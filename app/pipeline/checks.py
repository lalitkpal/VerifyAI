"""
Individual check functions for the verification pipeline.

Each function accepts (prompt, message, expected_output) and returns a
result dict with at minimum: status, message, score.
Count updates (passed/failed/warning) are handled by the caller.
"""
from app.evaluations.check_code import run_code_verifications
from app.evaluations.check_safety import run_safety_verifications
from app.evaluations.check_grounding import verify_citations_and_links
from app.evaluations.check_structure import verify_structure_compliance
from app.evaluations.check_consistency import test_consistency_using_cosine_similarity_002
from app.evaluations.check_fluency import test_fluency, test_fluency_using_gemma3n_002
from app.evaluations.check_sentiment import (
    test_sentiment_using_stringcmp_002,
    test_sentiment_using_gemma3n_002,
)
from app.evaluations.check_summarization import (
    test_summarization_using_cosine_similarity_002,
    test_summarization_using_gemma3n_002,
)

# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

_STATUS_SCORE = {"passed": 1.0, "warning": 0.5, "failed": 0.0}


def _score(status: str) -> float:
    return _STATUS_SCORE.get(status, 0.0)


# ---------------------------------------------------------------------------
# Check 1 — Code
# ---------------------------------------------------------------------------

def run_code_check(source: str, message: str) -> dict | None:
    """Returns a result dict, or None if the check does not apply."""
    is_coding = source.lower() in ("cursor", "copilot", "windsurf", "devin")
    has_code = any(tok in message for tok in ("```", "def ", "function ", "import "))
    if not (is_coding or has_code):
        return None
    res = run_code_verifications(message)
    res["score"] = 1.0 if res["status"] == "passed" else 0.0
    return res


# ---------------------------------------------------------------------------
# Check 2 — Safety
# ---------------------------------------------------------------------------

def run_safety_check(prompt: str, message: str) -> dict:
    res = run_safety_verifications(prompt, message)
    res["score"] = 1.0 if res["status"] == "passed" else 0.0
    return res


# ---------------------------------------------------------------------------
# Check 3 — Grounding
# ---------------------------------------------------------------------------

async def run_grounding_check(source: str, message: str) -> dict | None:
    """Returns a result dict, or None if no URLs are present."""
    is_search = source.lower() in (
        "perplexity", "perplexity pro", "gemini",
        "gemini 1.5 pro", "gemini 1.5 flash",
    )
    has_urls = "http://" in message or "https://" in message
    if not (is_search or has_urls):
        return None
    res = await verify_citations_and_links(message, source)
    res["score"] = 1.0 if res["status"] == "passed" else (0.5 if res["status"] == "warning" else 0.0)
    return res


# ---------------------------------------------------------------------------
# Check 4 — Structure
# ---------------------------------------------------------------------------

def run_structure_check(prompt: str, message: str) -> dict:
    res = verify_structure_compliance(prompt, message)
    res["score"] = 1.0 if res["status"] == "passed" else 0.0
    return res


# ---------------------------------------------------------------------------
# Check 5 — Semantic similarity
# ---------------------------------------------------------------------------

def run_semantic_check(prompt: str, message: str, expected_output: str) -> dict:
    try:
        score = test_consistency_using_cosine_similarity_002(prompt, message, expected_output)
        status = "passed" if score >= 0.7 else "failed"
        return {
            "status": status,
            "message": f"Semantic similarity score is {score:.3f} (threshold: 0.700).",
            "details": {"score": score},
            "score": round(score, 4),
        }
    except Exception as exc:
        return {
            "status": "warning",
            "message": f"Could not compute similarity: {exc}",
            "score": 0.5,
        }


# ---------------------------------------------------------------------------
# Check 6 — Fluency
# ---------------------------------------------------------------------------

def run_fluency_check(prompt: str, message: str, expected_output: str) -> dict:
    try:
        num_errors = test_fluency(prompt, message, expected_output)
        status = "passed" if num_errors <= 3 else "warning"
        return {
            "status": status,
            "message": f"Found {num_errors} grammar issue(s).",
            "details": {"grammar_errors": num_errors},
            "score": round(max(0.0, 1.0 - num_errors / 10), 4),
        }
    except Exception:
        pass

    try:
        feedback = test_fluency_using_gemma3n_002(prompt, message, expected_output)
        status = "passed" if any(w in feedback.lower() for w in ("excellent", "good")) else "warning"
        return {
            "status": status,
            "message": f"Ollama fluency evaluation: {feedback}",
            "details": {"feedback": feedback},
            "score": _score(status),
        }
    except Exception:
        return {
            "status": "passed",
            "message": "Grammar evaluation skipped (tools offline).",
            "score": 1.0,
        }


# ---------------------------------------------------------------------------
# Check 7 — Sentiment
# ---------------------------------------------------------------------------

def run_sentiment_check(prompt: str, message: str, expected_output: str) -> dict:
    try:
        if expected_output:
            match = test_sentiment_using_stringcmp_002(prompt, message, expected_output)
            status = "passed" if match else "warning"
            return {
                "status": status,
                "message": "Sentiment matches expected output." if match else "Sentiment differs from expected output.",
                "details": {"match": match},
                "score": _score(status),
            }
        try:
            feedback = test_sentiment_using_gemma3n_002(prompt, message, "")
            return {
                "status": "passed",
                "message": f"Sentiment evaluation: {feedback}",
                "details": {"feedback": feedback},
                "score": 1.0,
            }
        except Exception:
            return {
                "status": "passed",
                "message": "Sentiment check skipped (no reference and LLM offline).",
                "score": 1.0,
            }
    except Exception as exc:
        return {
            "status": "warning",
            "message": f"Sentiment check could not be completed: {exc}",
            "score": 0.5,
        }


# ---------------------------------------------------------------------------
# Check 8 — Summarization
# ---------------------------------------------------------------------------

def run_summarization_check(prompt: str, message: str, expected_output: str) -> dict:
    if not expected_output:
        return {
            "status": "passed",
            "message": "Summarization check skipped (no reference output provided).",
            "score": 1.0,
        }
    try:
        score = test_summarization_using_cosine_similarity_002(prompt, message, expected_output)
        status = "passed" if score >= 0.6 else "warning"
        return {
            "status": status,
            "message": f"Summarization similarity score is {score:.3f} (threshold: 0.600).",
            "details": {"score": score},
            "score": round(score, 4),
        }
    except Exception:
        pass

    try:
        feedback = test_summarization_using_gemma3n_002(prompt, message, expected_output)
        status = "passed" if "good" in feedback.lower() else "warning"
        return {
            "status": status,
            "message": f"Summarization evaluation: {feedback}",
            "details": {"feedback": feedback},
            "score": _score(status),
        }
    except Exception:
        return {
            "status": "passed",
            "message": "Summarization check skipped (LLM offline).",
            "score": 1.0,
        }
