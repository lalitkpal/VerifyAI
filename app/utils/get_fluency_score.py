import language_tool_python

def fluency_score_using_language_tool(genai_output):
    """
    Returns the number of grammar mistakes and a qualitative label.
    """
    tool = language_tool_python.LanguageTool('en-US')
    matches = tool.check(genai_output)
    num_errors = len(matches)
    return num_errors
    