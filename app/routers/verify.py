import asyncio
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, File, Form, UploadFile

from app.schemas import BatchVerifyRequest, VerifyRequest
from app.utils import database
from app.utils.file_parser import parse_csv_data, parse_excel_data
from app.pipeline.checks import (
    run_code_check,
    run_fluency_check,
    run_grounding_check,
    run_safety_check,
    run_semantic_check,
    run_sentiment_check,
    run_structure_check,
    run_summarization_check,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _tally(result: dict, passed: int, failed: int, warning: int):
    """Return updated (passed, failed, warning) counts based on result status."""
    s = result["status"]
    if s == "passed":
        return passed + 1, failed, warning
    if s == "warning":
        return passed, failed, warning + 1
    return passed, failed + 1, warning


def _overall_status(failed: int, warning: int) -> str:
    if failed > 0:
        return "failed"
    if warning > 0:
        return "warning"
    return "passed"


async def _run_pipeline(req: VerifyRequest) -> dict:
    """Execute all selected checks and return a complete result payload."""
    source = req.source
    prompt = req.prompt
    message = req.message
    expected = req.expected_output or ""
    checks = req.checks  # None means run all

    results: dict = {}
    passed = failed = warning = 0

    def _active(key: str) -> bool:
        return not checks or key in checks

    # 1. Code
    if _active("code_check"):
        res = run_code_check(source, message)
        if res is not None:
            results["code_check"] = res
            passed, failed, warning = _tally(res, passed, failed, warning)

    # 2. Safety
    if _active("safety_check"):
        res = run_safety_check(prompt, message)
        results["safety_check"] = res
        passed, failed, warning = _tally(res, passed, failed, warning)

    # 3. Grounding
    if _active("grounding_check"):
        res = await run_grounding_check(source, message)
        if res is not None:
            results["grounding_check"] = res
            passed, failed, warning = _tally(res, passed, failed, warning)

    # 4. Structure
    if _active("structure_check"):
        res = run_structure_check(prompt, message)
        results["structure_check"] = res
        passed, failed, warning = _tally(res, passed, failed, warning)

    # 5. Semantic
    if expected and _active("semantic_check"):
        res = run_semantic_check(prompt, message, expected)
        results["semantic_check"] = res
        passed, failed, warning = _tally(res, passed, failed, warning)

    # 6. Fluency
    if _active("fluency_check"):
        res = run_fluency_check(prompt, message, expected)
        results["fluency_check"] = res
        passed, failed, warning = _tally(res, passed, failed, warning)

    # 7. Sentiment
    if _active("sentiment_check"):
        res = run_sentiment_check(prompt, message, expected)
        results["sentiment_check"] = res
        passed, failed, warning = _tally(res, passed, failed, warning)

    # 8. Summarization
    if _active("summarization_check"):
        res = run_summarization_check(prompt, message, expected)
        results["summarization_check"] = res
        passed, failed, warning = _tally(res, passed, failed, warning)

    overall = _overall_status(failed, warning)

    run_id = await database.save_verification_run(
        source=source,
        prompt=prompt,
        message=message,
        expected_output=expected,
        status=overall,
        results=results,
        passed_count=passed,
        failed_count=failed,
    )

    return {
        "id": run_id,
        "timestamp": datetime.utcnow().isoformat(),
        "source": source,
        "status": overall,
        "summary": {"passed": passed, "failed": failed, "warning": warning},
        "results": results,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/verify")
async def verify_output(req: VerifyRequest):
    return await _run_pipeline(req)


@router.post("/verify/batch")
async def verify_batch(req: BatchVerifyRequest):
    async def process(item: dict):
        return await _run_pipeline(VerifyRequest(
            source=req.model_description,
            prompt=item.get("prompt", ""),
            message=item.get("message", ""),
            expected_output=item.get("expected_output") or "",
            checks=req.checks,
        ))

    run_results = await asyncio.gather(*[process(i) for i in req.items])
    passed_runs = sum(1 for r in run_results if r["status"] == "passed")

    return {
        "status": "success",
        "passed_runs": passed_runs,
        "failed_runs": len(run_results) - passed_runs,
        "total_runs": len(run_results),
        "results": list(run_results),
    }


@router.post("/verify/upload")
async def verify_upload(
    file: UploadFile = File(...),
    model_description: str = Form("Uploaded Model"),
    checks: Optional[str] = Form(None),
):
    checks_list: Optional[List[str]] = None
    if checks:
        try:
            checks_list = json.loads(checks)
        except Exception:
            checks_list = [c.strip() for c in checks.split(",") if c.strip()]

    content = await file.read()
    name = (file.filename or "").lower()

    if name.endswith(".csv"):
        items = parse_csv_data(content.decode("utf-8", errors="ignore"))
    elif name.endswith((".xlsx", ".xls")):
        items = parse_excel_data(content)
    else:
        return {"error": "Unsupported file format. Please upload .csv, .xlsx, or .xls."}

    if not items:
        return {"error": "No valid test cases parsed from the file. Check column headers."}

    async def process(item: dict):
        return await _run_pipeline(VerifyRequest(
            source=model_description,
            prompt=item.get("prompt", ""),
            message=item.get("message", ""),
            expected_output=item.get("expected_output") or "",
            checks=checks_list,
        ))

    run_results = await asyncio.gather(*[process(i) for i in items])
    passed_runs = sum(1 for r in run_results if r["status"] == "passed")

    return {
        "status": "success",
        "passed_runs": passed_runs,
        "failed_runs": len(run_results) - passed_runs,
        "total_runs": len(run_results),
        "results": list(run_results),
    }
