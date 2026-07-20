from fastapi import APIRouter

from app.schemas import ModelConfigRequest
from app.utils import database
from app.utils.llm_execution import execute_llm_prompt

router = APIRouter()

_TEST_PROMPT = "Hello! Please reply with exactly the word 'OK'."


@router.get("/models")
async def get_models():
    return await database.get_model_endpoints()


@router.post("/models")
async def create_or_update_model(cfg: ModelConfigRequest):
    endpoint_id = await database.save_model_endpoint(
        name=cfg.name,
        provider=cfg.provider,
        model_name=cfg.model_name,
        api_key=cfg.api_key or "",
        base_url=cfg.base_url or "",
        is_active=cfg.is_active if cfg.is_active is not None else True,
        endpoint_id=cfg.id,
    )
    return {"status": "success", "id": endpoint_id}


@router.delete("/models/{endpoint_id}")
async def delete_model(endpoint_id: str):
    await database.delete_model_endpoint(endpoint_id)
    return {"status": "success"}


@router.post("/models/test")
async def test_model_endpoint(cfg: ModelConfigRequest):
    try:
        response_text = await execute_llm_prompt(
            provider=cfg.provider,
            model_name=cfg.model_name,
            api_key=cfg.api_key or "",
            base_url=cfg.base_url or "",
            prompt=_TEST_PROMPT,
        )
        return {"status": "success", "response": response_text}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
