"""Smoke test for the health check endpoint."""

import pytest


@pytest.mark.django_db
def test_health_check_returns_ok(api_client):
    """Health endpoint returns 200 with simple status."""
    response = api_client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_health_check_no_sensitive_data(api_client):
    """Health endpoint must not expose version, settings, or error details."""
    response = api_client.get("/api/v1/health/")
    data = response.json()
    assert "version" not in data
    assert "settings" not in data
    assert "error" not in data
    assert "debug" not in data
    assert list(data.keys()) == ["status"]
