"""Integration tests for FastAPI REST endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check_endpoint():
    """Verify that /health returns online status and healthy database."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["database"]["status"] == "healthy"


def test_schema_endpoint():
    """Verify that /api/v1/schema returns approved tables, relationships, and business metrics."""
    response = client.get("/api/v1/schema")
    assert response.status_code == 200
    data = response.json()
    assert "customers" in data["tables"]
    assert "orders" in data["tables"]
    assert "order_items" in data["tables"]
    assert "products" in data["tables"]
    assert len(data["relationships"]) > 0
    assert "Net Sales / Revenue" in data["metrics"]


def test_ask_endpoint_valid_question():
    """Verify that POST /api/v1/ask processes a business question successfully."""
    payload = {
        "question": "What is the breakdown of net sales by customer segment?",
        "provider": "mock"
    }
    response = client.post("/api/v1/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("success", "ready")
    assert len(data["answer"]) > 0
    assert data["sql"] is not None
    assert len(data["columns"]) > 0
    assert data["row_count"] > 0
    assert data["chart"] is not None


def test_ask_endpoint_ambiguous_question():
    """Verify that an ambiguous question returns clarification_required via the API."""
    payload = {
        "question": "Which product is best?",
        "provider": "mock"
    }
    response = client.post("/api/v1/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "clarification_required"
    assert data["clarification_question"] is not None


def test_evaluations_summary_endpoint():
    """Verify that /api/v1/evaluations/summary returns reference query statistics."""
    response = client.get("/api/v1/evaluations/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["reference_suite"]["total_queries"] == 20
    assert data["reference_suite"]["accuracy_pct"] == 100.0
