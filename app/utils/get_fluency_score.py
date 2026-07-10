import language_tool_python

# LanguageTool starts a Java subprocess; initialising it once and reusing
# it across calls avoids a 2-5 second JVM startup on every fluency check.
_tool: language_tool_python.LanguageTool | None = None

def _get_tool() -> language_tool_python.LanguageTool:
    global _tool
    if _tool is None:
        _tool = language_tool_python.LanguageTool('en-US')
    return _tool


def fluency_score_using_language_tool(genai_output: str) -> int:
    """
    Returns the number of grammar/style issues found in *genai_output*.
    Lower is better; 0 means no issues detected.
    """
    tool = _get_tool()
    matches = tool.check(genai_output)
    return len(matches)
