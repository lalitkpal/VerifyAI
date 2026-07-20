from pydantic import BaseModel
from typing import List, Optional


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


class ItemRequest(BaseModel):
    """Legacy request model for the /execute/ backward-compat endpoint."""
    item: str
    box1: str
    box2: str
    box3: str
