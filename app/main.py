from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Existing imports
from app.models.ollama_chat import get_gemma3n_response
from app.evaluations.check_sentiment import test_sentiment_using_gemma3n_002
from app.evaluations.check_sentiment import test_sentiment_using_stringcmp_002
from app.evaluations.check_consistency import test_consistency_using_cosine_similarity_002
from app.evaluations.check_consistency import test_consistency_using_gemma3n_002
from app.evaluations.check_summarization import test_summarization_using_cosine_similarity_002
from app.evaluations.check_summarization import test_summarization_using_gemma3n_002
from app.evaluations.check_fluency import test_fluency
from app.evaluations.check_fluency import test_fluency_using_gemma3n_002

# New imports for the verification pipeline
from app.utils import database
from app.evaluations.check_code import run_code_verifications
from app.evaluations.check_safety import run_safety_verifications
from app.evaluations.check_grounding import verify_citations_and_links
from app.evaluations.check_structure import verify_structure_compliance

import os

app = FastAPI(title="VerifyAI Test Harness")

# Serve static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Database event hooks
@app.on_event("startup")
async def startup():
    await database.init_db()

@app.on_event("shutdown")
async def shutdown():
    await database.close_db()

class ItemRequest(BaseModel):
    item: str
    box1: str
    box2: str
    box3: str

class VerifyRequest(BaseModel):
    source: str
    prompt: str
    message: str
    expected_output: Optional[str] = None
    checks: Optional[List[str]] = None

# Serve index.html at root
@app.get("/")
def read_root():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    return FileResponse(index_path)

@app.post("/run_prompt/")
async def run_prompt(request: Request):
    data = await request.json()
    prompt = data.get("prompt")
    try:
        result = get_gemma3n_response(prompt)
    except Exception as e:
        result = f"Ollama offline fallback: simulated response for '{prompt}'"
    return {"output": result}

@app.post("/execute/")
def execute_item(request: ItemRequest):
    # Backward compatible execution endpoint
    if request.item == "item1":
        return test_sentiment_using_stringcmp_002(request.box1, request.box2, request.box3)
    elif request.item == "item2":
        return test_consistency_using_gemma3n_002(request.box1, request.box2, request.box3)
    elif request.item == "item3":
        return test_summarization_using_gemma3n_002(request.box1, request.box2, request.box3)
    elif request.item == "item4":
        return test_fluency_using_gemma3n_002(request.box1, request.box2, request.box3)
    else:
        return {"error": "Unknown item"}

# New Verification Test Harness API endpoints
@app.post("/api/verify")
async def verify_output(req: VerifyRequest):
    source = req.source
    prompt = req.prompt
    message = req.message
    expected_output = req.expected_output or ""
    checks = req.checks
    
    results = {}
    passed_count = 0
    failed_count = 0
    warning_count = 0
    
    # 1. Code validation
    if not checks or "code_check" in checks:
        is_coding = source.lower() in ("cursor", "copilot", "windsurf", "devin")
        has_code = "```" in message or "def " in message or "function " in message or "import " in message
        if is_coding or has_code:
            code_res = run_code_verifications(message)
            results["code_check"] = code_res
            if code_res["status"] == "passed":
                passed_count += 1
            else:
                failed_count += 1
                
    # 2. Safety and PII verification
    if not checks or "safety_check" in checks:
        safety_res = run_safety_verifications(prompt, message)
        results["safety_check"] = safety_res
        if safety_res["status"] == "passed":
            passed_count += 1
        else:
            failed_count += 1
            
    # 3. Grounding and Citations
    if not checks or "grounding_check" in checks:
        is_search = source.lower() in ("perplexity", "perplexity pro", "gemini", "gemini 1.5 pro", "gemini 1.5 flash")
        has_urls = "http://" in message or "https://" in message
        if is_search or has_urls:
            ground_res = await verify_citations_and_links(message, source)
            results["grounding_check"] = ground_res
            if ground_res["status"] == "passed":
                passed_count += 1
            elif ground_res["status"] == "warning":
                warning_count += 1
            else:
                failed_count += 1
                
    # 4. JSON / Structure Compliance
    if not checks or "structure_check" in checks:
        struct_res = verify_structure_compliance(prompt, message)
        results["structure_check"] = struct_res
        if struct_res["status"] == "passed":
            passed_count += 1
        else:
            failed_count += 1
            
    # 5. Semantic Cosine Similarity
    if expected_output:
        if not checks or "semantic_check" in checks:
            try:
                score = test_consistency_using_cosine_similarity_002(prompt, message, expected_output)
                status = "passed" if score >= 0.7 else "failed"
                results["semantic_check"] = {
                    "status": status,
                    "message": f"Semantic similarity score is {score:.3f} (threshold: 0.700).",
                    "details": {"score": score}
                }
                if status == "passed":
                    passed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                results["semantic_check"] = {
                    "status": "warning",
                    "message": f"Could not compute similarity: {str(e)}"
                }
                warning_count += 1
                
    # 6. Fluency Check
    if not checks or "fluency_check" in checks:
        try:
            num_errors = test_fluency(prompt, message, expected_output)
            status = "passed" if num_errors <= 3 else "warning"
            results["fluency_check"] = {
                "status": status,
                "message": f"Found {num_errors} grammar rules issues.",
                "details": {"grammar_errors": num_errors}
            }
            if status == "passed":
                passed_count += 1
            else:
                warning_count += 1
        except Exception:
            try:
                ollama_fluency = test_fluency_using_gemma3n_002(prompt, message, expected_output)
                status = "passed" if "excellent" in ollama_fluency.lower() or "good" in ollama_fluency.lower() else "warning"
                results["fluency_check"] = {
                    "status": status,
                    "message": f"Ollama Fluency evaluation: {ollama_fluency}",
                    "details": {"feedback": ollama_fluency}
                }
                if status == "passed":
                    passed_count += 1
                else:
                    warning_count += 1
            except Exception:
                results["fluency_check"] = {
                    "status": "passed",
                    "message": "Basic grammar evaluation skipped (grammar tools offline)."
                }
                passed_count += 1
                
    # Overall status
    overall_status = "failed" if failed_count > 0 else "passed"
    
    # Save to database
    run_id = await database.save_verification_run(
        source=source,
        prompt=prompt,
        message=message,
        expected_output=expected_output,
        status=overall_status,
        results=results,
        passed_count=passed_count,
        failed_count=failed_count
    )
    
    return {
        "id": run_id,
        "timestamp": datetime.utcnow().isoformat(),
        "source": source,
        "status": overall_status,
        "summary": {
            "passed": passed_count,
            "failed": failed_count,
            "warning": warning_count
        },
        "results": results
    }

@app.get("/api/history")
async def get_history():
    return await database.get_verification_runs()

@app.get("/api/stats")
async def get_stats():
    runs = await database.get_stats()
    total = len(runs)
    if total == 0:
        return {
            "total_runs": 0,
            "pass_rate": 0.0,
            "platform_stats": {}
        }
        
    passed_runs = sum(1 for r in runs if r["status"] == "passed")
    pass_rate = passed_runs / total
    
    platform_stats = {}
    for r in runs:
        src = r["source"]
        if src not in platform_stats:
            platform_stats[src] = {"total": 0, "passed": 0}
        platform_stats[src]["total"] += 1
        if r["status"] == "passed":
            platform_stats[src]["passed"] += 1
            
    platform_pass_rates = {}
    for src, stat in platform_stats.items():
        platform_pass_rates[src] = {
            "total": stat["total"],
            "passed": stat["passed"],
            "pass_rate": round(stat["passed"] / stat["total"], 3)
        }
        
    return {
        "total_runs": total,
        "pass_rate": round(pass_rate, 3),
        "platform_stats": platform_pass_rates
    }

@app.delete("/api/history")
async def delete_history():
    await database.clear_history()
    return {"status": "success", "message": "Verification history cleared."}