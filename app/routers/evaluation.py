import asyncio

from fastapi import APIRouter

from app.schemas import EvaluationRunRequest, VerifyRequest
from app.utils import database
from app.utils.llm_execution import execute_llm_prompt

router = APIRouter()


@router.post("/evaluations/run")
async def run_evaluation_suite(req: EvaluationRunRequest):
    # Import here to avoid a circular dependency at module load time
    from app.routers.verify import _run_pipeline

    all_cases = await database.get_test_cases()
    selected_cases = [tc for tc in all_cases if tc["id"] in req.test_case_ids]

    all_models = await database.get_model_endpoints()
    selected_models = [m for m in all_models if m["id"] in req.model_ids]

    if not selected_cases or not selected_models:
        return {"error": "Please select at least one test case and one model endpoint."}

    async def evaluate_single(model: dict, test_case: dict) -> dict:
        model_id = model["id"]
        model_name = model["name"]
        tc_id = test_case["id"]
        tc_name = test_case["name"]
        prompt = test_case["prompt"]
        expected = test_case["expected_output"] or ""

        try:
            generated = await execute_llm_prompt(
                provider=model["provider"],
                model_name=model["model_name"],
                api_key=model["api_key"] or "",
                base_url=model["base_url"] or "",
                prompt=prompt,
            )
            verification = await _run_pipeline(VerifyRequest(
                source=f"{model_name} ({model['model_name']})",
                prompt=prompt,
                message=generated,
                expected_output=expected,
                checks=req.checks,
            ))
            return {
                "model_id": model_id,
                "model_name": model_name,
                "test_case_id": tc_id,
                "test_case_name": tc_name,
                "status": verification["status"],
                "run_id": verification["id"],
                "error": None,
            }
        except Exception as exc:
            return {
                "model_id": model_id,
                "model_name": model_name,
                "test_case_id": tc_id,
                "test_case_name": tc_name,
                "status": "failed",
                "run_id": None,
                "error": str(exc),
            }

    tasks = [
        evaluate_single(model, tc)
        for model in selected_models
        for tc in selected_cases
    ]
    grid_results = await asyncio.gather(*tasks)

    return {"status": "success", "results": list(grid_results)}
