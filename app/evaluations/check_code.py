import re
import ast

def extract_code_blocks(text: str):
    """
    Extracts code blocks from markdown.
    Returns a list of dicts with 'language' and 'code'.
    """
    pattern = r"```(\w*)\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    
    blocks = []
    for lang, code in matches:
        blocks.append({
            "language": lang.strip().lower() if lang else "text",
            "code": code
        })
    return blocks

def verify_code_syntax(code: str, language: str) -> dict:
    """
    Verifies the syntax of a code block.
    """
    if not code.strip():
        return {"status": "passed", "message": "Code block is empty"}
        
    if language in ("python", "py"):
        try:
            ast.parse(code)
            return {"status": "passed", "message": "Python code is syntactically valid."}
        except SyntaxError as e:
            return {
                "status": "failed", 
                "message": f"Python Syntax Error on line {e.lineno}: {e.msg}\nCode snippet: {e.text}"
            }
    elif language in ("json",):
        import json
        try:
            json.loads(code)
            return {"status": "passed", "message": "JSON is valid."}
        except ValueError as e:
            return {"status": "failed", "message": f"Invalid JSON structure: {str(e)}"}
    
    # Generic brace matching and basic syntax check for other languages (C++, Java, JS, etc.)
    stack = []
    pairs = {')': '(', '}': '{', ']': '['}
    for char in code:
        if char in pairs.values():
            stack.append(char)
        elif char in pairs.keys():
            if not stack or stack[-1] != pairs[char]:
                # We won't strictly fail on brace mismatch for non-python because comment structures or strings 
                # can throw off simple regex without full tokenizers. We will issue a warning instead.
                return {"status": "warning", "message": f"Potential unbalanced bracket/brace '{char}' found."}
            stack.pop()
            
    return {"status": "passed", "message": f"Basic structure check passed for language: {language or 'unspecified'}."}

def verify_code_security(code: str) -> dict:
    """
    Checks for dangerous operations and hardcoded secrets.
    """
    issues = []
    
    # Check for hardcoded secrets
    # AWS keys
    aws_key_pattern = r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}"
    aws_secret_pattern = r"\"[A-Za-z0-9/+=]{40}\"|\'[A-Za-z0-9/+=]{40}\'"
    # General API Key patterns
    api_key_patterns = [
        r"(?i)(api_key|apikey|secret|password|token)\s*=\s*['\"][a-zA-Z0-9_\-\.\+=]{16,}['\"]",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
    ]
    
    if re.search(aws_key_pattern, code):
        issues.append("Potential AWS Access Key ID detected.")
    if re.search(aws_secret_pattern, code):
        issues.append("Potential AWS Secret Access Key detected.")
        
    for pat in api_key_patterns:
        if re.search(pat, code):
            issues.append("Potential hardcoded credential or API secret key detected.")

    # Dangerous functions (Python/JS)
    dangerous_patterns = [
        (r"\beval\s*\(", "Use of 'eval()' is extremely dangerous and can lead to remote code execution (RCE)."),
        (r"\bexec\s*\(", "Use of 'exec()' can lead to arbitrary code execution."),
        (r"\bos\.system\s*\(", "Use of 'os.system()' is unsafe. Prefer subprocess module with arguments listed as a list."),
        (r"\bsubprocess\.Popen\s*\([^)]*shell\s*=\s*True", "subprocess with shell=True is vulnerable to shell injection."),
        (r"\bchild_process\.exec\s*\(", "Use of child_process.exec in JS is vulnerable to command injection.")
    ]
    
    for pat, desc in dangerous_patterns:
        if re.search(pat, code):
            issues.append(desc)
            
    if issues:
        return {"status": "failed", "message": " | ".join(issues)}
    return {"status": "passed", "message": "No obvious security vulnerabilities or hardcoded secrets found."}

def verify_code_completeness(code: str) -> dict:
    """
    Checks for placeholders like TODOs and ellipses that represent unfinished code.
    """
    placeholders = [
        (r"//\s*TODO", "Contains '// TODO' comment indicating unfinished implementation."),
        (r"#\s*TODO", "Contains '# TODO' comment indicating unfinished implementation."),
        (r"/\*\s*TODO", "Contains '/* TODO */' comment indicating unfinished implementation."),
        (r"//\s*implement\b", "Contains '// implement' indicating placeholder logic."),
        (r"#\s*implement\b", "Contains '# implement' indicating placeholder logic."),
        (r"\.\.\.\s*#\s*placeholder", "Contains placeholder markers."),
        (r"//\s*write\s+your\s+code\b", "Contains placeholder instruction comments.")
    ]
    
    # We should exclude the standard python ellipsis '...' when used alone in function signature if followed by implementation
    # but check if it's the ONLY thing in the function body or matches common lazy patterns
    lazy_patterns = [
        (r"def\s+\w+\([^)]*\):\s*\n\s*\.\.\.\s*(\n|$)", "Python function body is left as an ellipsis placeholder ('...')."),
        (r"\{\s*\.\.\.\s*\}", "Braces contain only ellipsis placeholder.")
    ]
    
    found = []
    for pat, desc in placeholders + lazy_patterns:
        if re.search(pat, code, re.IGNORECASE):
            found.append(desc)
            
    if found:
        return {"status": "failed", "message": " | ".join(found)}
    return {"status": "passed", "message": "Code appears to be complete with no lazy placeholders."}

def run_code_verifications(text: str) -> dict:
    """
    Runs all code checks on all code blocks found in text.
    """
    blocks = extract_code_blocks(text)
    if not blocks:
        # If the text does not contain markdown code blocks, check if the text itself might be raw code.
        # This is common in simple code-only responses.
        if "def " in text or "import " in text or "function " in text or "const " in text:
            blocks = [{"language": "python" if "def " in text else "javascript", "code": text}]
        else:
            return {
                "summary": {"status": "passed", "message": "No code blocks detected for verification."},
                "details": {}
            }
            
    syntax_results = []
    security_results = []
    completeness_results = []
    
    for idx, block in enumerate(blocks):
        lang = block["language"]
        code = block["code"]
        block_name = f"block_{idx+1}_{lang}"
        
        syntax = verify_code_syntax(code, lang)
        security = verify_code_security(code)
        completeness = verify_code_completeness(code)
        
        syntax_results.append(syntax)
        security_results.append(security)
        completeness_results.append(completeness)
        
    # Summarize results
    failed_syntax = [r for r in syntax_results if r["status"] == "failed"]
    failed_sec = [r for r in security_results if r["status"] == "failed"]
    failed_comp = [r for r in completeness_results if r["status"] == "failed"]
    
    status = "passed"
    msg_parts = []
    
    if failed_syntax:
        status = "failed"
        msg_parts.append(f"Syntax errors in {len(failed_syntax)} block(s): " + "; ".join(r["message"] for r in failed_syntax))
    if failed_sec:
        status = "failed"
        msg_parts.append(f"Security issues: " + "; ".join(r["message"] for r in failed_sec))
    if failed_comp:
        # We can make completeness a warning or failure. Let's make it a failure since outgoing messages
        # shouldn't be lazy, but give it a clear description.
        status = "failed"
        msg_parts.append(f"Incomplete code: " + "; ".join(r["message"] for r in failed_comp))
        
    summary_message = "All code blocks passed syntax, security, and completeness validations." if status == "passed" else " | ".join(msg_parts)
    
    return {
        "status": status,
        "message": summary_message,
        "details": {
            "syntax": {"status": "failed" if failed_syntax else "passed", "results": syntax_results},
            "security": {"status": "failed" if failed_sec else "passed", "results": security_results},
            "completeness": {"status": "failed" if failed_comp else "passed", "results": completeness_results}
        }
    }
