from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.readability import MAX_TEXT_LENGTH

client = TestClient(app)


def test_readability_success_response_shape():
    response = client.post(
        "/readability",
        json={"text": "The cat sat on the mat."},
    )
    assert response.status_code == 200
    body = response.json()

    expected_keys = {
        "word_count",
        "sentence_count",
        "character_count",
        "average_words_per_sentence",
        "average_syllables_per_word",
        "flesch_reading_ease",
        "flesch_kincaid_grade",
        "reading_level",
    }
    assert expected_keys.issubset(body.keys())

    assert body["word_count"] == 6
    assert body["sentence_count"] == 1
    assert body["reading_level"] == "Very Easy"
    assert body["flesch_reading_ease"] == 116.15
    assert body["flesch_kincaid_grade"] == -1.45


def test_readability_success_with_paragraph():
    text = (
        "The quick brown fox jumps over the lazy dog. "
        "It was a bright, cold morning in the forest."
    )
    response = client.post("/readability", json={"text": text})
    assert response.status_code == 200
    body = response.json()
    assert body["sentence_count"] == 2
    assert body["word_count"] > 0


def test_readability_whitespace_only_text_is_accepted_and_undetermined():
    # A single space passes min_length=1 at the schema layer; the service
    # then handles it gracefully rather than raising.
    response = client.post("/readability", json={"text": " "})
    assert response.status_code == 200
    body = response.json()
    assert body["word_count"] == 0
    assert body["reading_level"] == "Undetermined"


def test_readability_rejects_empty_text():
    response = client.post("/readability", json={"text": ""})
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "ValidationError"


def test_readability_rejects_missing_text_field():
    response = client.post("/readability", json={})
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "ValidationError"


def test_readability_rejects_wrong_type():
    response = client.post("/readability", json={"text": 12345})
    assert response.status_code == 422


def test_readability_enforces_max_length_limit():
    too_long_text = "a " * (MAX_TEXT_LENGTH)  # comfortably over the limit
    response = client.post("/readability", json={"text": too_long_text})
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "ValidationError"


def test_readability_accepts_text_at_max_length_boundary():
    exactly_max_text = "a" * MAX_TEXT_LENGTH
    response = client.post("/readability", json={"text": exactly_max_text})
    assert response.status_code == 200


def test_readability_repeated_requests_are_deterministic():
    payload = {"text": "Determinism matters a great deal in production systems."}
    first = client.post("/readability", json=payload).json()
    second = client.post("/readability", json=payload).json()
    assert first == second
