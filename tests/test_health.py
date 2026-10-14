"""
tests/test_health.py

Tests for:
  GET /api/health  — health check endpoint
"""

import json


def test_health_returns_200(client):
    """The health endpoint must return HTTP 200 when the database is reachable."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_returns_json(client):
    """The health endpoint must return a JSON body."""
    response = client.get("/api/health")
    data = response.get_json()
    assert data is not None, "Response body is not valid JSON"


def test_health_status_ok(client):
    """The health response must contain status='ok' and database='reachable'."""
    response = client.get("/api/health")
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["database"] == "reachable"


def test_health_db_failure(app):
    """
    When the database is unreachable the health endpoint must return HTTP 503.

    Strategy: use a named in-memory URI that we deliberately do NOT
    initialise (no tables created), then mock health_check to return False
    — simulating an unreachable database.
    """
    import unittest.mock as mock

    with mock.patch("url_shortener.routes.health_check", return_value=False):
        with app.test_client() as bad_client:
            response = bad_client.get("/api/health")

    assert response.status_code == 503
    data = response.get_json()
    assert data["status"] == "degraded"
    assert data["database"] == "unreachable"
