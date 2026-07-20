from fastapi import APIRouter

from app.schemas import TestCaseRequest
from app.utils import database

router = APIRouter()


@router.get("/test_cases")
async def get_test_cases():
    return await database.get_test_cases()


@router.post("/test_cases")
async def create_test_case(tc: TestCaseRequest):
    tc_id = await database.save_test_case(tc.name, tc.prompt, tc.expected_output)
    return {"status": "success", "id": tc_id}


@router.delete("/test_cases/{tc_id}")
async def delete_test_case(tc_id: str):
    await database.delete_test_case(tc_id)
    return {"status": "success"}
