from app.models.ollama_chat import get_gemma3n_response

def test_sentiment_using_gemma3n_002(input, output):
    return get_gemma3n_response(f"Classify this as 'positive', 'negative', 'neutral', or 'mixed': {input} Just return the emotion") == output
    
