import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "VerifyAI" in response.text

def test_legacy_execute_sentiment():
    # Box1: query, Box2: output, Box3: expected
    payload = {
        "item": "item1",
        "box1": "User prompt",
        "box2": "Happy",
        "box3": "Happy"
    }
    response = client.post("/execute/", json=payload)
    assert response.status_code == 200
    assert response.json() is True  # Sentiment comparison returned True

def test_legacy_unknown_item():
    payload = {
        "item": "non_existent_item",
        "box1": "",
        "box2": "",
        "box3": ""
    }
    response = client.post("/execute/", json=payload)
    assert response.status_code == 200
    assert "error" in response.json()