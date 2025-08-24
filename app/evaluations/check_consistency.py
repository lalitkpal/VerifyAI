from app.models.ollama_chat import get_gemma3n_response
from app.utils.get_cosine_similarity_score import cosine_similarity_score

def test_consistency_using_gemma3n_002(query, test_model_output, expected_output):
    return get_gemma3n_response(f"Check if the {test_model_output} is consistent with {expected_output} for user query: {query}")
    

def test_consistency_using_cosine_similarity_002(query, test_model_output, expected_output):
    return cosine_similarity_score([test_model_output, expected_output])