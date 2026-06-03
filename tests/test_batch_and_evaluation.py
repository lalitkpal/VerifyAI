import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json
import io

from app.main import app
from app.utils.file_parser import parse_csv_data, parse_excel_data
from app.utils import database

client = TestClient(app)

def test_csv_parser_success():
    csv_data = "prompt,message,expected_output\nWho won?,Google won,Google won\n"
    res = parse_csv_data(csv_data)
    assert len(res) == 1
    assert res[0]["prompt"] == "Who won?"
    assert res[0]["message"] == "Google won"
    assert res[0]["expected_output"] == "Google won"

def test_csv_parser_semantic_headers():
    csv_data = "question,response,target\nWho won?,Google won,Google won\n"
    res = parse_csv_data(csv_data)
    assert len(res) == 1
    assert res[0]["prompt"] == "Who won?"
    assert res[0]["message"] == "Google won"
    assert res[0]["expected_output"] == "Google won"

def test_excel_parser_mock():
    # Since openpyxl loads workbook from bytes, we can mock load_workbook
    # to avoid binary file complexity in unit tests.
    with patch("openpyxl.load_workbook") as mock_load:
        mock_wb = mock_load.return_value
        mock_sheet = mock_wb.active
        
        # Mock sheet dimensions and row returns
        mock_sheet.max_row = 2
        mock_sheet.max_column = 3
        
        # Row 1 headers
        class MockCell:
            def __init__(self, value):
                self.value = value
        
        mock_sheet.__getitem__.side_effect = lambda key: [MockCell("prompt"), MockCell("message"), MockCell("expected_output")]
        
        # Row 2 values
        # mock_sheet.cell(row=2, column=c).value
        def cell_mock(row, column):
            if row == 2:
                if column == 1: return MockCell("What color?")
                if column == 2: return MockCell("Blue")
                if column == 3: return MockCell("Blue")
            return MockCell(None)
            
        mock_sheet.cell = cell_mock
        
        res = parse_excel_data(b"dummy")
        assert len(res) == 1
        assert res[0]["prompt"] == "What color?"
        assert res[0]["message"] == "Blue"
        assert res[0]["expected_output"] == "Blue"

@pytest.mark.asyncio
async def test_database_crud_operations():
    # Clean/init database first
    await database.init_db()
    
    # Test cases CRUD
    tc_id = await database.save_test_case(
        name="Unit Test Case",
        prompt="Explain quantum mechanics.",
        expected_output="Quantum mechanics explains..."
    )
    assert tc_id is not None
    
    cases = await database.get_test_cases()
    assert any(c["id"] == tc_id for c in cases)
    
    # Model endpoints CRUD
    model_id = await database.save_model_endpoint(
        name="Test Model Endpoint",
        provider="openai",
        model_name="gpt-4",
        api_key="mock_key",
        base_url="https://api.openai.com/v1"
    )
    assert model_id is not None
    
    models = await database.get_model_endpoints()
    assert any(m["id"] == model_id for m in models)
    
    # Cleanup
    await database.delete_test_case(tc_id)
    await database.delete_model_endpoint(model_id)
    
    cases_post = await database.get_test_cases()
    assert not any(c["id"] == tc_id for c in cases_post)

def test_api_verify_batch():
    payload = {
        "model_description": "Batch API Tester",
        "items": [
            {
                "prompt": "Hello",
                "message": "Hello there",
                "expected_output": "Hello there"
            }
        ],
        "checks": ["safety_check", "structure_check"]
    }
    response = client.post("/api/verify/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total_runs"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["status"] == "passed"

def test_api_verify_upload_csv():
    csv_content = "prompt,message\nWhat is 2+2?,4\n"
    file_payload = {"file": ("test_cases.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    form_data = {
        "model_description": "Uploaded CSV model",
        "checks": json.dumps(["safety_check"])
    }
    response = client.post("/api/verify/upload", files=file_payload, data=form_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total_runs"] == 1
    assert data["results"][0]["status"] == "passed"

@pytest.mark.asyncio
async def test_api_evaluations_run():
    # Initialize DB
    await database.init_db()
    
    # Create test case and model endpoint
    tc_id = await database.save_test_case("Eval TC", "Evaluate 1+1", "2")
    m_id = await database.save_model_endpoint("Eval Model", "openai", "gpt-3.5-turbo", "test_key", "test_url")
    
    # Mock LLM execution call
    with patch("app.main.execute_llm_prompt", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = "The answer is 2"
        
        payload = {
            "test_case_ids": [tc_id],
            "model_ids": [m_id],
            "checks": ["safety_check"]
        }
        
        response = client.post("/api/evaluations/run", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["results"]) == 1
        assert data["results"][0]["model_id"] == m_id
        assert data["results"][0]["test_case_id"] == tc_id
        assert data["results"][0]["status"] == "passed"
        assert data["results"][0]["error"] is None
        
    # Cleanup
    await database.delete_test_case(tc_id)
    await database.delete_model_endpoint(m_id)
