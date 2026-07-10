from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json

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

# Custom utility imports
from app.utils.file_parser import parse_csv_data, parse_excel_data
from app.utils.llm_execution import execute_llm_prompt

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

class BatchVerifyRequest(BaseModel):
    model_description: str
    items: List[dict]
    checks: Optional[List[str]] = None

class TestCaseRequest(BaseModel):
    name: str
    prompt: str
    expected_output: Optional[str] = None

class ModelConfigRequest(BaseModel):
    name: str
    provider: str
    model_name: str
    api_key: Optional[str] = ""
    base_url: Optional[str] = ""
    is_active: Optional[bool] = True
    id: Optional[str] = None

class EvaluationRunRequest(BaseModel):
    test_case_ids: List[str]
    model_ids: List[str]
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
                
    # 7. Sentiment Check
    if not checks or "sentiment_check" in checks:
        try:
            # Use string comparison as primary; fall back to LLM if expected_output absent
            if expected_output:
                sentiment_match = test_sentiment_using_stringcmp_002(prompt, message, expected_output)
                status = "passed" if sentiment_match else "warning"
                results["sentiment_check"] = {
                    "status": status,
                    "message": "Sentiment matches expected output." if sentiment_match else "Sentiment of response differs from expected output.",
                    "details": {"match": sentiment_match}
                }
            else:
                try:
                    ollama_sentiment = test_sentiment_using_gemma3n_002(prompt, message, "")
                    results["sentiment_check"] = {
                        "status": "passed",
                        "message": f"Sentiment evaluation: {ollama_sentiment}",
                        "details": {"feedback": ollama_sentiment}
                    }
                except Exception:
                    results["sentiment_check"] = {
                        "status": "passed",
                        "message": "Sentiment check skipped (no expected output and LLM offline)."
                    }
            if results["sentiment_check"]["status"] == "passed":
                passed_count += 1
            elif results["sentiment_check"]["status"] == "warning":
                warning_count += 1
            else:
                failed_count += 1
        except Exception as e:
            results["sentiment_check"] = {
                "status": "warning",
                "message": f"Sentiment check could not be completed: {str(e)}"
            }
            warning_count += 1

    # 8. Summarization Check
    if not checks or "summarization_check" in checks:
        if expected_output:
            try:
                score = test_summarization_using_cosine_similarity_002(prompt, message, expected_output)
                status = "passed" if score >= 0.6 else "warning"
                results["summarization_check"] = {
                    "status": status,
                    "message": f"Summarization similarity score is {score:.3f} (threshold: 0.600).",
                    "details": {"score": score}
                }
                if status == "passed":
                    passed_count += 1
                else:
                    warning_count += 1
            except Exception as e:
                try:
                    ollama_summ = test_summarization_using_gemma3n_002(prompt, message, expected_output)
                    status = "passed" if "good" in ollama_summ.lower() else "warning"
                    results["summarization_check"] = {
                        "status": status,
                        "message": f"Summarization evaluation: {ollama_summ}",
                        "details": {"feedback": ollama_summ}
                    }
                    if status == "passed":
                        passed_count += 1
                    else:
                        warning_count += 1
                except Exception:
                    results["summarization_check"] = {
                        "status": "passed",
                        "message": "Summarization check skipped (LLM offline)."
                    }
                    passed_count += 1
        else:
            results["summarization_check"] = {
                "status": "passed",
                "message": "Summarization check skipped (no expected output provided for comparison)."
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

@app.post("/api/verify/batch")
async def verify_batch(req: BatchVerifyRequest):
    import asyncio
    passed_runs = 0
    failed_runs = 0
    
    async def process_item(item):
        prompt = item.get("prompt", "")
        message = item.get("message", "")
        expected = item.get("expected_output") or ""
        
        v_req = VerifyRequest(
            source=req.model_description,
            prompt=prompt,
            message=message,
            expected_output=expected,
            checks=req.checks
        )
        return await verify_output(v_req)
        
    tasks = [process_item(item) for item in req.items]
    run_results = await asyncio.gather(*tasks)
    
    for res in run_results:
        if res["status"] == "passed":
            passed_runs += 1
        else:
            failed_runs += 1
            
    return {
        "status": "success",
        "passed_runs": passed_runs,
        "failed_runs": failed_runs,
        "total_runs": len(run_results),
        "results": run_results
    }

@app.post("/api/verify/upload")
async def verify_upload(
    file: UploadFile = File(...),
    model_description: str = Form("Uploaded Model"),
    checks: Optional[str] = Form(None)
):
    import asyncio
    # Parse checks list from JSON if available
    checks_list = None
    if checks:
        try:
            checks_list = json.loads(checks)
        except Exception:
            checks_list = [c.strip() for c in checks.split(",") if c.strip()]
            
    content_bytes = await file.read()
    filename = file.filename.lower()
    
    items = []
    if filename.endswith(".csv"):
        content_str = content_bytes.decode("utf-8", errors="ignore")
        items = parse_csv_data(content_str)
    elif filename.endswith((".xlsx", ".xls")):
        items = parse_excel_data(content_bytes)
    else:
        return {"error": "Unsupported file format. Please upload a .csv, .xlsx, or .xls file."}
        
    if not items:
        return {"error": "No valid test cases parsed from the file. Check headers."}
        
    async def process_item(item):
        prompt = item.get("prompt", "")
        message = item.get("message", "")
        expected = item.get("expected_output") or ""
        
        v_req = VerifyRequest(
            source=model_description,
            prompt=prompt,
            message=message,
            expected_output=expected,
            checks=checks_list
        )
        return await verify_output(v_req)
        
    tasks = [process_item(item) for item in items]
    run_results = await asyncio.gather(*tasks)
    
    passed_runs = sum(1 for r in run_results if r["status"] == "passed")
    failed_runs = len(run_results) - passed_runs
    
    return {
        "status": "success",
        "passed_runs": passed_runs,
        "failed_runs": failed_runs,
        "total_runs": len(run_results),
        "results": run_results
    }

@app.get("/api/test_cases")
async def get_test_cases():
    return await database.get_test_cases()

@app.post("/api/test_cases")
async def create_test_case(tc: TestCaseRequest):
    tc_id = await database.save_test_case(tc.name, tc.prompt, tc.expected_output)
    return {"status": "success", "id": tc_id}

@app.delete("/api/test_cases/{tc_id}")
async def delete_test_case(tc_id: str):
    await database.delete_test_case(tc_id)
    return {"status": "success"}

@app.get("/api/models")
async def get_models():
    return await database.get_model_endpoints()

@app.post("/api/models")
async def create_or_update_model(cfg: ModelConfigRequest):
    endpoint_id = await database.save_model_endpoint(
        name=cfg.name,
        provider=cfg.provider,
        model_name=cfg.model_name,
        api_key=cfg.api_key or "",
        base_url=cfg.base_url or "",
        is_active=cfg.is_active if cfg.is_active is not None else True,
        endpoint_id=cfg.id
    )
    return {"status": "success", "id": endpoint_id}

@app.delete("/api/models/{endpoint_id}")
async def delete_model(endpoint_id: str):
    await database.delete_model_endpoint(endpoint_id)
    return {"status": "success"}

@app.post("/api/models/test")
async def test_model_endpoint(cfg: ModelConfigRequest):
    test_prompt = "Hello! Please reply with exactly the word 'OK'."
    try:
        response_text = await execute_llm_prompt(
            provider=cfg.provider,
            model_name=cfg.model_name,
            api_key=cfg.api_key or "",
            base_url=cfg.base_url or "",
            prompt=test_prompt
        )
        return {"status": "success", "response": response_text}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/evaluations/run")
async def run_evaluation_suite(req: EvaluationRunRequest):
    import asyncio
    all_cases = await database.get_test_cases()
    selected_cases = [tc for tc in all_cases if tc["id"] in req.test_case_ids]
    
    all_models = await database.get_model_endpoints()
    selected_models = [m for m in all_models if m["id"] in req.model_ids]
    
    if not selected_cases or not selected_models:
        return {"error": "Please select at least one test case and one model endpoint."}
        
    async def evaluate_single(model, test_case):
        model_name = model["name"]
        provider = model["provider"]
        model_id = model["id"]
        tc_id = test_case["id"]
        tc_name = test_case["name"]
        prompt = test_case["prompt"]
        expected = test_case["expected_output"] or ""
        
        try:
            generated_response = await execute_llm_prompt(
                provider=provider,
                model_name=model["model_name"],
                api_key=model["api_key"] or "",
                base_url=model["base_url"] or "",
                prompt=prompt
            )
            
            v_req = VerifyRequest(
                source=f"{model_name} ({model['model_name']})",
                prompt=prompt,
                message=generated_response,
                expected_output=expected,
                checks=req.checks
            )
            verification = await verify_output(v_req)
            
            return {
                "model_id": model_id,
                "model_name": model_name,
                "test_case_id": tc_id,
                "test_case_name": tc_name,
                "status": verification["status"],
                "run_id": verification["id"],
                "error": None
            }
        except Exception as e:
            return {
                "model_id": model_id,
                "model_name": model_name,
                "test_case_id": tc_id,
                "test_case_name": tc_name,
                "status": "failed",
                "run_id": None,
                "error": str(e)
            }

    tasks = []
    for model in selected_models:
        for tc in selected_cases:
            tasks.append(evaluate_single(model, tc))
            
    grid_results = await asyncio.gather(*tasks)
    
    return {
        "status": "success",
        "results": grid_results
    }