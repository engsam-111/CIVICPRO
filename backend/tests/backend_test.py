"""Regression checks for Clerk configuration and unauthenticated API protection."""
import os
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


def test_clerk_config_enabled():
    response = requests.get(f"{BASE_URL}/api/clerk/config", timeout=15)
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert isinstance(data["publishable_key"], str) and data["publishable_key"]


def test_protected_endpoints_reject_missing_bearer():
    for path in ("/api/me", "/api/projects", "/api/reports", "/api/issues"):
        response = requests.get(f"{BASE_URL}{path}", timeout=15)
        assert response.status_code == 401, (path, response.status_code, response.text)
