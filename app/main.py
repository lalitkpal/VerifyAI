from fastapi import FastAPI
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.models.ollama_chat import get_gemma3n_response
from app.evaluations.check_sentiment import test_sentiment_using_gemma3n_002
from app.evaluations.check_sentiment import test_sentiment_using_stringcmp_002
from app.evaluations.check_consistency import test_consistency_using_cosine_similarity_002
from app.evaluations.check_consistency import test_consistency_using_gemma3n_002
from app.evaluations.check_summarization import test_summarization_using_cosine_similarity_002
from app.evaluations.check_summarization import test_summarization_using_gemma3n_002
from app.evaluations.check_fluency import test_fluency
from app.evaluations.check_fluency import test_fluency_using_gemma3n_002

import os

app = FastAPI()

class ItemRequest(BaseModel):
    item: str
    box1: str
    box2: str
    box3: str

# Serve static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Serve index.html at root
@app.get("/")
def read_root():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    return FileResponse(index_path)

@app.post("/run_prompt/")
async def run_prompt(request: Request):
    data = await request.json()
    prompt = data.get("prompt")
    result = get_gemma3n_response(prompt)
    # result = f"GenAI output for: {prompt}"  # Placeholder
    return {"output": result}

def item1_function(box1, box2, box3):
    return {"equal": (box1 + box2) == box3}

def item1_function_sentiment(box1, box2, box3):
    #return test_sentiment_using_gemma3n_002(box1, box2, box3)
    return test_sentiment_using_stringcmp_002(box1, box2, box3)

def item2_function(box1, box2, box3):
    return {"equal": (box1 + box2) == box3}

def item2_function_consistency_001(box1, box2, box3):
    score =  test_consistency_using_cosine_similarity_002(box1, box2, box3)
    if score > 0.85:
        description = "Highly consistent"
    elif score > 0.7:
        description = "Consistent"
    elif score > 0.5:
        description = "Somewhat consistent"
    else:
        description = "Not consistent"

    return {
        "Cosine similarity score": round(score, 3),
        "Consistency": description
    }

def item2_function_consistency_002(box1, box2, box3):
    return test_consistency_using_gemma3n_002(box1, box2, box3)

def item3_function_summarization_001(box1, box2, box3):
    score =  test_summarization_using_cosine_similarity_002(box1, box2, box3)
    if score > 0.85:
        description = "Excellent summary"
    elif score > 0.7:
        description = "Good summary"
    elif score > 0.5:
        description = "Fair summary"
    else:
        description = "Poor summary"

    return {
        "Cosine similarity score": round(score, 3),
        "Consistency": description
    }

def item3_function_summarization_002(box1, box2, box3):
    return test_summarization_using_gemma3n_002(box1, box2, box3)
    
def item4_function_fluency_001(box1, box2, box3):

    num_errors = test_fluency(box1, box2, box3)
    if num_errors == 0:
        label = "Excellent fluency"
    elif num_errors <= 2:
        label = "Good fluency"
    elif num_errors <= 5:
        label = "Fair fluency"
    else:
        label = "Poor fluency"

    return label

def item4_function_fluency_002(box1, box2, box3):
    return test_fluency_using_gemma3n_002(box1, box2, box3)


@app.post("/execute/")
def execute_item(request: ItemRequest):
    if request.item == "item1":
        return item1_function_sentiment(request.box1, request.box2, request.box3)
    elif request.item == "item2":
        return item2_function_consistency_002(request.box1, request.box2, request.box3)
    elif request.item == "item3":
        return item3_function_summarization_002(request.box1, request.box2, request.box3)
    elif request.item == "item4":
        return item4_function_fluency_002(request.box1, request.box2, request.box3)
    else:
        return {"error": "Unknown item"}