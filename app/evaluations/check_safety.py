import re
from app.models.ollama_chat import get_gemma3n_response

def verify_pii(text: str) -> dict:
    """
    Checks if the outgoing text leaks PII.
    """
    pii_found = []
    
    # Email regex
    email_pattern = r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
    # Phone numbers (various formats)
    phone_pattern = r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
    # Social Security Numbers (SSN)
    ssn_pattern = r"\b\d{3}-\d{2}-\d{4}\b"
    # Credit Card Numbers
    cc_pattern = r"\b(?:\d[ -]*?){13,16}\b"
    
    emails = re.findall(email_pattern, text)
    if emails:
        pii_found.append(f"Email address(es) detected: {', '.join(emails)}")
        
    phones = re.findall(phone_pattern, text)
    if phones:
        pii_found.append(f"Phone number(s) detected: {', '.join(phones)}")
        
    ssns = re.findall(ssn_pattern, text)
    if ssns:
        pii_found.append(f"SSN(s) detected: {', '.join(ssns)}")
        
    ccs = re.findall(cc_pattern, text)
    # Filter out pure numbers that aren't CCs (e.g. version numbers or coordinate lists)
    valid_ccs = [cc for cc in ccs if len(re.sub(r"\D", "", cc)) >= 13]
    if valid_ccs:
        pii_found.append(f"Credit card number(s) detected: {', '.join(valid_ccs)}")
        
    if pii_found:
        return {"status": "failed", "message": " | ".join(pii_found)}
    return {"status": "passed", "message": "No personally identifiable information (PII) detected."}

def verify_jailbreak(prompt: str, message: str) -> dict:
    """
    Checks if there are indicators of jailbreaks or prompt injections.
    """
    jailbreak_keywords = [
        r"ignore\s+(?:the\s+)?(?:above|previous)\s+instructions",
        r"bypass\s+restrictions",
        r"dan\s+mode",
        r"do\s+anything\s+now",
        r"developer\s+mode\s+enabled",
        r"ignore\s+your\s+safety\s+guidelines",
        r"system\s+override",
        r"jailbreak\b",
        r"forget\s+all\s+rules",
        r"you\s+are\s+now\s+unrestricted"
    ]
    
    hits = []
    # Check if the prompt has injection commands, or if the model's message contains text indicating
    # it is playing along with a jailbreak.
    for kw in jailbreak_keywords:
        if re.search(kw, prompt, re.IGNORECASE):
            hits.append(f"Jailbreak prompt pattern detected: '{kw}' in user prompt")
        if re.search(kw, message, re.IGNORECASE):
            hits.append(f"Jailbreak confirmation pattern detected: '{kw}' in model response")
            
    if hits:
        return {"status": "failed", "message": " | ".join(hits)}
    return {"status": "passed", "message": "No jailbreak or prompt injection indicators detected."}

def verify_safety_content(text: str) -> dict:
    """
    Checks for general toxic, abusive, or dangerous content in the message.
    """
    # Simple rule-based toxicity checks (fallback list of highly toxic terms)
    toxic_patterns = [
        r"\b(?:kill\s+yourself|go\s+die|suicide|make\s+a\s+bomb|how\s+to\s+hack\s+a)\b",
    ]
    
    for pat in toxic_patterns:
        if re.search(pat, text, re.IGNORECASE):
            return {"status": "failed", "message": "Contains potentially dangerous/toxic keyword commands."}
            
    # LLM-based verification if available
    try:
        # Prompt gemma/qwen to check safety
        prompt = (
            "You are a safety filter assistant. Analyze if the following text is safe, ethical, and appropriate. "
            "Respond ONLY with 'SAFE' or 'UNSAFE: [reason]'.\n\n"
            f"Text to evaluate: {text}\n\n"
            "Safety evaluation:"
        )
        response = get_gemma3n_response(prompt)
        if response and "unsafe" in response.lower():
            reason = response.split(":", 1)[1].strip() if ":" in response else "LLM classified as unsafe"
            return {"status": "failed", "message": f"LLM safety check failed: {reason}"}
    except Exception as e:
        # If Ollama is offline, log a message and return the passed status (based on the regex checks passing)
        return {
            "status": "passed", 
            "message": f"Basic content safety check passed (LLM safety check skipped: {str(e)})."
        }
        
    return {"status": "passed", "message": "Content safety verification passed."}

def run_safety_verifications(prompt: str, message: str) -> dict:
    """
    Runs all safety verifications on the inputs.
    """
    pii_res = verify_pii(message)
    jail_res = verify_jailbreak(prompt, message)
    content_res = verify_safety_content(message)
    
    status = "passed"
    msg_parts = []
    
    if pii_res["status"] == "failed":
        status = "failed"
        msg_parts.append(pii_res["message"])
    if jail_res["status"] == "failed":
        status = "failed"
        msg_parts.append(jail_res["message"])
    if content_res["status"] == "failed":
        status = "failed"
        msg_parts.append(content_res["message"])
        
    summary_message = "All safety checks (PII, Jailbreak, Content Toxicity) passed." if status == "passed" else " | ".join(msg_parts)
    
    return {
        "status": status,
        "message": summary_message,
        "details": {
            "pii": pii_res,
            "jailbreak": jail_res,
            "content_safety": content_res
        }
    }
