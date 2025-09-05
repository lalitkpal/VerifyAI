from app.utils.get_fluency_score import fluency_score_using_language_tool
from app.models.ollama_chat import get_gemma3n_response

def test_fluency(query, genai_output, expected_output):
    # Only genai_output is needed for fluency
    return fluency_score_using_language_tool(genai_output)

def test_fluency_using_gemma3n_002(query, genai_output, expected_output):
    return get_gemma3n_response(f"Check the fluency of the following text: {genai_output}, return Excellent, Good, Fair, Poor based on your judgement.") #for user query: {query}")