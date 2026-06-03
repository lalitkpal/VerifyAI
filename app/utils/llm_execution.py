import os
import httpx
from typing import Optional

async def execute_llm_prompt(
    provider: str,
    model_name: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    prompt: str = ""
) -> str:
    """
    Asynchronously queries the selected LLM provider.
    """
    provider = provider.lower().strip()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. OLLAMA LOCAL
        if provider == "ollama":
            url = f"{base_url or 'http://localhost:11434'}/api/chat"
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["message"]["content"].strip()
            except Exception as e:
                raise RuntimeError(f"Ollama execution failed: {str(e)}")

        # 2. OPENAI CLOUD
        elif provider == "openai":
            key = api_key or os.getenv("OPENAI_API_KEY")
            if not key:
                raise ValueError("OpenAI API Key is missing. Provide it in model config or set OPENAI_API_KEY environment variable.")
            url = f"{base_url or 'https://api.openai.com/v1'}/chat/completions"
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}]
            }
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                raise RuntimeError(f"OpenAI execution failed: {str(e)}")

        # 3. ANTHROPIC CLOUD
        elif provider == "anthropic":
            key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not key:
                raise ValueError("Anthropic API Key is missing. Provide it in model config or set ANTHROPIC_API_KEY environment variable.")
            url = f"{base_url or 'https://api.anthropic.com/v1'}/messages"
            headers = {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1500
            }
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["content"][0]["text"].strip()
            except Exception as e:
                raise RuntimeError(f"Anthropic execution failed: {str(e)}")

        # 4. GOOGLE GEMINI
        elif provider == "gemini":
            key = api_key or os.getenv("GEMINI_API_KEY")
            if not key:
                raise ValueError("Gemini API Key is missing. Provide it in model config or set GEMINI_API_KEY environment variable.")
            # Google AI Studio endpoint
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
            payload = {
                "contents": [
                    {
                        "parts": [{"text": prompt}]
                    }
                ]
            }
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as e:
                raise RuntimeError(f"Gemini execution failed: {str(e)}")

        # 5. OPENAI-COMPATIBLE (vLLM, LM Studio, llama.cpp, LocalAI, etc.)
        elif provider in ("openai-compatible", "local", "custom"):
            url = f"{base_url or 'http://localhost:8000/v1'}/chat/completions"
            headers = {"Content-Type": "application/json"}
            key = api_key or os.getenv("OPENAI_API_KEY")
            if key:
                headers["Authorization"] = f"Bearer {key}"
                
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}]
            }
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                raise RuntimeError(f"Custom OpenAI-compatible execution failed: {str(e)}")

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
