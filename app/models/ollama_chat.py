from ollama import chat
from ollama import ChatResponse

def get_gemma3n_response(input: str) -> str:
    response: ChatResponse = chat(model='gemma3n:e2b', messages=[{
        'role': 'user',
        'content': input,
      },
    ])

    return response['message']['content'].strip().lower()

def get_gptoss20b_response(input: str) -> str:
    response: ChatResponse = chat(model='gpt-oss:20b', messages=[{
        'role': 'user',
        'content': input,
      },
    ])

    return response['message']['content'].strip().lower()
