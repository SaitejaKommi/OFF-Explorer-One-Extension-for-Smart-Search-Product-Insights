"""
tests/test_api.py
-----------------
Integration tests for FastAPI endpoints using TestClient + empty-stub DuckDB.
Tests verify endpoint structure and correctness, not data results.
"""
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "slm_enabled" in data


def test_search_returns_200():
    resp = client.post("/search", json={"query": "low sugar vegan snacks", "limit": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert "parsed_intent" in data
    assert "session_id" in data


def test_search_parsed_intent_fields():
    resp = client.post("/search", json={"query": "low sugar vegan snacks under 200 calories"})
    assert resp.status_code == 200
    intent = resp.json()["parsed_intent"]
    assert "categories" in intent
    assert "dietary_tags" in intent
    assert "nutrient_constraints" in intent


def test_search_french_query():
    resp = client.post(
        "/search",
        json={"query": "collations véganes faible sucre moins de 200 calories", "language": "fr"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["parsed_intent"]["language"] == "fr"


def test_search_session_id_returned():
    resp = client.post("/search", json={"query": "high protein cereal"})
    data = resp.json()
    assert "session_id" in data
    assert len(data["session_id"]) > 0


def test_refine_without_session_returns_404():
    resp = client.post(
        "/refine",
        json={"refinement": "now only gluten-free", "session_id": "nonexistent-session"},
    )
    assert resp.status_code == 404


def test_refine_after_search():
    # First search to create session
    search_resp = client.post("/search", json={"query": "vegan snacks"})
    assert search_resp.status_code == 200
    session_id = search_resp.json()["session_id"]

    # Refine
    refine_resp = client.post(
        "/refine",
        json={"refinement": "now only gluten-free", "session_id": session_id},
    )
    assert refine_resp.status_code == 200
    data = refine_resp.json()
    assert "en:gluten-free" in data["parsed_intent"]["dietary_tags"]


def test_product_insights_not_found():
    resp = client.post(
        "/product-insights",
        json={"barcode": "0000000000000", "language": "en"},
    )
    assert resp.status_code == 404


def test_search_limit_validation():
    resp = client.post("/search", json={"query": "bread", "limit": 0})
    assert resp.status_code == 422  # pydantic validation error


def test_search_empty_query_validation():
    resp = client.post("/search", json={"query": ""})
    assert resp.status_code == 422
