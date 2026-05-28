import ollama
from ollama import chat

def get_available_model() -> str:
    """
    Scans local Ollama instance for installed models.
    Prefers gemma4:latest, qwen3.6:latest, gemma3n:e2b, or any other installed model.
    """
    try:
        models_response = ollama.list()
        
        # Determine model names depending on the client library response format
        models = []
        if isinstance(models_response, dict) and "models" in models_response:
            models = [m["name"] for m in models_response["models"]]
        elif hasattr(models_response, "models"):
            models = [m.name for m in models_response.models]
        elif isinstance(models_response, list):
            models = [m.get("name") if isinstance(m, dict) else getattr(m, "name", str(m)) for m in models_response]
            
        if not models:
            return None
            
        # Choose preference order
        preferences = ["gemma4:latest", "qwen3.6:latest", "gemma3n:e2b", "gemma", "qwen", "llama", "mistral"]
        for pref in preferences:
            for model in models:
                if pref in model.lower():
                    return model
        return models[0]
    except Exception:
        return None

def get_gemma3n_response(input_text: str) -> str:
    """
    Invokes the selected local Ollama model to generate a response.
    """
    selected_model = get_available_model()
    if not selected_model:
        raise ConnectionError("Ollama is offline or no local models are installed.")
        
    try:
        response = chat(model=selected_model, messages=[{
            'role': 'user',
            'content': input_text,
        }])
        
        # Check structure of return message
        if isinstance(response, dict) and 'message' in response:
            return response['message']['content'].strip()
        elif hasattr(response, 'message'):
            return response.message.content.strip()
        elif hasattr(response, 'choices'):
            return response.choices[0].message.content.strip()
        return str(response).strip()
    except Exception as e:
        raise RuntimeError(f"Ollama inference error with model {selected_model}: {str(e)}")

def get_gptoss20b_response(input_text: str) -> str:
    """
    Fallback interface matching existing references.
    """
    return get_gemma3n_response(input_text)
