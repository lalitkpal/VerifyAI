"""
Tests for the cosine similarity utility.

Correctness properties:
  P1. Singleton: a list of one string scores 1.0
  P2. Identical outputs: all-same list scores 1.0
  P3. Ordering invariance: score([a, b]) == score([b, a])
  P4. Range: score is always in [0.0, 1.0]
  P5. Similar texts score higher than dissimilar texts
  P6. Empty-string guard: does not raise ZeroDivisionError
"""
import pytest
from app.utils.get_cosine_similarity_score import cosine_similarity_score


# P1 — singleton
def test_single_string_scores_one():
    score = cosine_similarity_score(["The quick brown fox"])
    assert abs(score - 1.0) < 1e-4, f"Expected ~1.0, got {score}"


# P2 — identical list
def test_two_identical_strings_score_one():
    text = "Machine learning is transforming the world."
    score = cosine_similarity_score([text, text])
    assert abs(score - 1.0) < 1e-4, f"Expected ~1.0, got {score}"


def test_all_identical_outputs():
    outputs = ["hello world"] * 5
    score = cosine_similarity_score(outputs)
    assert abs(score - 1.0) < 1e-4


# P3 — ordering invariance
def test_ordering_invariance():
    a = "The cat sat on the mat."
    b = "A dog ran across the field."
    assert abs(cosine_similarity_score([a, b]) - cosine_similarity_score([b, a])) < 1e-6


# P4 — range
@pytest.mark.parametrize("outputs", [
    ["hello"],
    ["hello", "world"],
    ["The sky is blue.", "The ocean is deep.", "Mountains are tall."],
    ["foo bar baz", "qux quux corge"],
])
def test_score_in_valid_range(outputs):
    score = cosine_similarity_score(outputs)
    assert 0.0 <= score <= 1.0 + 1e-6, f"Score {score} out of [0, 1] for {outputs}"


# P5 — similar scores higher than dissimilar
def test_similar_scores_higher_than_dissimilar():
    similar = [
        "Python is a popular programming language.",
        "Python is widely used in software development."
    ]
    dissimilar = [
        "Python is a popular programming language.",
        "The Eiffel Tower is located in Paris, France."
    ]
    assert cosine_similarity_score(similar) > cosine_similarity_score(dissimilar)


# P6 — empty-string guard
def test_empty_string_does_not_raise():
    try:
        score = cosine_similarity_score(["", "hello world"])
        assert 0.0 <= score <= 1.0 + 1e-6
    except ZeroDivisionError:
        pytest.fail("cosine_similarity_score raised ZeroDivisionError on empty string")
