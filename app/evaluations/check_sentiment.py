from app.models.ollama_chat import get_gemma3n_response

def test_sentiment_using_gemma3n_002(query, test_model_output, expected_output):
    return get_gemma3n_response(f"Check if the emotion depicted in {test_model_output} matches with {expected_output} for user query: {query}")

def test_sentiment_using_stringcmp_002(query, test_model_output, expected_output):
    return test_model_output.strip().lower() == expected_output.strip().lower()