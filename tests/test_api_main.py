from datetime import date

from fastapi.testclient import TestClient

import api.main as api_main
from api.dashboard import build_today_dashboard
from api.sheets import DASHBOARD_SHEETS


client = TestClient(api_main.app)


def sample_dashboard():
    tables = {name: [] for name in DASHBOARD_SHEETS}
    return build_today_dashboard(tables, date(2026, 8, 22))


def test_health_does_not_require_credentials():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"service": "nexo-api", "status": "ok"}


def test_dashboard_requires_server_token(monkeypatch):
    monkeypatch.delenv("NEXO_API_TOKEN", raising=False)

    response = client.get("/v1/dashboard/today")

    assert response.status_code == 503


def test_dashboard_rejects_wrong_token(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "segredo-de-teste")

    response = client.get(
        "/v1/dashboard/today",
        headers={"X-Nexo-Token": "incorreto"},
    )

    assert response.status_code == 401


def test_dashboard_returns_camel_case_contract(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "segredo-de-teste")
    monkeypatch.setattr(api_main, "load_today_dashboard", sample_dashboard)

    response = client.get(
        "/v1/dashboard/today",
        headers={"X-Nexo-Token": "segredo-de-teste"},
    )

    assert response.status_code == 200
    assert response.json()["date"] == "2026-08-22"
    assert response.json()["weeklyQuestions"]["target"] == 200
    assert response.json()["user"]["xpToNextLevel"] == 1000


def test_dashboard_hides_internal_failures(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "segredo-de-teste")

    def fail():
        raise RuntimeError("detalhe interno")

    monkeypatch.setattr(api_main, "load_today_dashboard", fail)
    response = client.get(
        "/v1/dashboard/today",
        headers={"X-Nexo-Token": "segredo-de-teste"},
    )

    assert response.status_code == 503
    assert "detalhe interno" not in response.text
