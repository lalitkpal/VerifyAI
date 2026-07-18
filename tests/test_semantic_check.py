"""
Integration tests for the semantic_check path in POST /api/verify.

Correctness properties:
  P1. High-similarity pair (score >= 0.7) → semantic_check status "passed"
  P2. Low-similarity pair (score < 0.7) → semantic_check status "failed"
  P3. No expected_output → semantic_check key absent from results
  P4. Response always contains id, status, summary, results keys
  P5. score field is present and in [0, 1] when check runs
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

SIMILAR_PAIR = {
    "source": "ChatGPT",
    "prompt": "What is the capital of France?",
    "message": "The capital of France is Paris.",
    "expected_output": "Paris is the capital city of France.",
    "checks": ["semantic_check"]
}

DISSIMILAR_PAIR = {
    "source": "ChatGPT",
    "prompt": "What is the capital of France?",
    "message": "Bananas are a great source of potassium and are yellow in colour.",
    "expected_output": "Paris is the capital city of France.",
    "checks": ["semantic_check"]
}

NO_EXPECTED = {
    "source": "ChatGPT",
    "prompt": "Tell me a joke.",
    "message": "Why did the chicken cross the road? To get to the other side!",
    "checks": ["semantic_check"]
}


# P1 — high-similarity passes
def test_high_similarity_passes():
    res = client.post("/api/verify", json=SIMILAR_PAIR)
    assert res.status_code == 200
    data = res.json()
    assert "semantic_check" in data["results"]
    assert data["results"]["semantic_check"]["status"] == "passed"


# P2 — low-similarity fails
def test_low_similarity_fails():
    res = client.post("/api/verify", json=DISSIMILAR_PAIR)
    assert res.status_code == 200
    data = res.json()
    assert "semantic_check" in data["results"]
    assert data["results"]["semantic_check"]["status"] == "failed"


# P3 — no expected_output skips semantic check
def test_no_expected_output_skips_semantic_check():
    res = client.post("/api/verify", json=NO_EXPECTED)
    assert res.status_code == 200
    data = res.json()
    assert "semantic_check" not in data["results"]


# P4 — response structure is always correct
@pytest.mark.parametrize("payload", [SIMILAR_PAIR, DISSIMILAR_PAIR, NO_EXPECTED])
def test_response_has_required_keys(payload):
    res = client.post("/api/verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    for key in ("id", "status", "summary", "results"):
        assert key in data, f"Missing key '{key}' in response"


# P5 — score field present and in [0, 1]
def test_score_field_present_and_valid():
    res = client.post("/api/verify", json=SIMILAR_PAIR)
    assert res.status_code == 200
    data = res.json()
    check = data["results"].get("semantic_check", {})
    assert "score" in check, "score field missing from semantic_check result"
    assert 0.0 <= check["score"] <= 1.0, f"score {check['score']} out of [0, 1]"
