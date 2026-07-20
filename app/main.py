import os

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.models.ollama_chat import get_gemma3n_response
from app.schemas import ItemRequest
from app.utils import database
from app.evaluations.check_sentiment import test_sentiment_using_stringcmp_002
from app.evaluations.check_consistency import test_consistency_using_gemma3n_002
from app.evaluations.check_summarization import test_summarization_using_gemma3n_002
from app.evaluations.check_fluency import test_fluency_using_gemma3n_002

from app.routers import evaluation, history, models, test_cases, verify

app = FastAPI(title="VerifyAI Test Harness")

# ---------------------------------------------------------------------------
# Static files & lifecycle
# ---------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
async def startup():
    await database.init_db()


@app.on_event("shutdown")
async def shutdown():
    await database.close_db()


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(verify.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(test_cases.router, prefix="/api")
app.include_router(evaluation.router, prefix="/api")


# ---------------------------------------------------------------------------
# UI root
# ---------------------------------------------------------------------------

@app.get("/")
def read_root():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


# ---------------------------------------------------------------------------
# Legacy endpoints (kept for backward compatibility)
# ---------------------------------------------------------------------------

@app.post("/run_prompt/")
async def run_prompt(request: Request):
    data = await request.json()
    prompt = data.get("prompt")
    try:
        result = get_gemma3n_response(prompt)
    except Exception:
        result = f"Ollama offline fallback: simulated response for '{prompt}'"
    return {"output": result}


@app.post("/execute/")
def execute_item(request: ItemRequest):
    if request.item == "item1":
        return test_sentiment_using_stringcmp_002(request.box1, request.box2, request.box3)
    if request.item == "item2":
        return test_consistency_using_gemma3n_002(request.box1, request.box2, request.box3)
    if request.item == "item3":
        return test_summarization_using_gemma3n_002(request.box1, request.box2, request.box3)
    if request.item == "item4":
        return test_fluency_using_gemma3n_002(request.box1, request.box2, request.box3)
    return {"error": "Unknown item"}
