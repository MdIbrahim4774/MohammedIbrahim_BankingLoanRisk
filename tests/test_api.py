import pytest
from fastapi.testclient import TestClient
from src.api.main import app

from tests.conftest import requires_mysql

client = TestClient(app)

def test_health_and_root():
    res = client.get("/")
    assert res.status_code == 200
    assert "project" in res.json()

    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

def test_auth_login():
    res = client.post("/api/v1/auth/login", data={"username": "analyst", "password": "analyst123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "analyst"

    # Test me
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    res_me = client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["username"] == "analyst"

@requires_mysql
def test_customers_list_and_filter():
    # Login
    auth_res = client.post("/api/v1/auth/login", data={"username": "analyst", "password": "analyst123"})
    token = auth_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # List
    res = client.get("/api/v1/customers?page=1&page_size=10", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) <= 10
    assert data["total"] > 0

    # Filter by risk band
    res_filtered = client.get("/api/v1/customers?risk_band=High&page_size=5", headers=headers)
    assert res_filtered.status_code == 200
    for item in res_filtered.json()["items"]:
        if item.get("credit_profile"):
            assert item["credit_profile"]["risk_band"] == "High"

def test_risk_evaluate_endpoint():
    payload = {
        "limit_bal": 150000.0,
        "age": 32,
        "education": 1,
        "marriage": 2,
        "sex": 1,
        "pay_statuses": [0, 0, 0, 0, 0, 0],
        "bill_amounts": [30000.0, 30000.0, 30000.0, 30000.0, 30000.0, 30000.0],
        "pay_amounts": [30000.0, 30000.0, 30000.0, 30000.0, 30000.0, 30000.0]
    }
    res = client.post("/api/v1/risk/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["risk_band"] == "Low"
    assert "risk_score" in data

@requires_mysql
def test_analytics_kpis():
    auth_res = client.post("/api/v1/auth/login", data={"username": "analyst", "password": "analyst123"})
    token = auth_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/analytics/kpis", headers=headers)
    assert res.status_code == 200
    kpis = res.json()
    assert "total_customers" in kpis
    assert kpis["total_customers"] > 0
    assert "total_credit_exposure" in kpis

