import re
import json

def detect_json_request(prompt: str) -> bool:
    """
    Checks if the user prompt is explicitly requesting a JSON format.
    """
    keywords = [
        r"\bjson\b",
        r"\bvalid\s+json\b",
        r"\bformat\s+as\s+json\b",
        r"\bjson\s+schema\b",
        r"\bstructured\s+data\b"
    ]
    for kw in keywords:
        if re.search(kw, prompt, re.IGNORECASE):
            return True
    return False

def extract_json_content(text: str) -> str:
    """
    Attempts to extract JSON string from markdown code blocks or brackets.
    """
    # Try finding markdown code block of type json
    pattern = r"```(?:json)?\n(.*?)\n```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
        
    # Find matching outermost braces
    brace_pattern = r"(\{.*\})"
    match = re.search(brace_pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
        
    return text.strip()

def verify_structure_compliance(prompt: str, message: str) -> dict:
    """
    Validates structure correctness when requested in prompt.
    """
    if not detect_json_request(prompt):
        return {"status": "passed", "message": "No structured JSON compliance was explicitly requested in user prompt."}
        
    json_candidate = extract_json_content(message)
    try:
        parsed = json.loads(json_candidate)
        return {
            "status": "passed",
            "message": "Valid JSON structure detected and parsed successfully.",
            "details": {
                "keys_found": list(parsed.keys()) if isinstance(parsed, dict) else []
            }
        }
    except json.JSONDecodeError as e:
        return {
            "status": "failed",
            "message": f"Structured JSON output was requested, but output could not be parsed: {str(e)}",
            "details": {
                "error": str(e),
                "attempted_payload": json_candidate[:200] + "..." if len(json_candidate) > 200 else json_candidate
            }
        }
