from datetime import date

from fastapi.testclient import TestClient

import api.main as api_main
from api.dashboard import build_today_dashboard
from api.planning import build_planning_dashboard
from api.routine import build_routine_dashboard
from api.sheets import DASHBOARD_SHEETS


client = TestClient(api_main.app)


def sample_dashboard():
    tables = {name: [] for name in DASHBOARD_SHEETS}
    return build_today_dashboard(tables, date(2026, 8, 22))


def sample_planning():
    tables = {name: [] for name in DASHBOARD_SHEETS}
    return build_planning_dashboard(tables, date(2026, 8, 22))


def sample_routine(reference=None):
    tables = {name: [] for name in DASHBOARD_SHEETS}
    return build_routine_dashboard(tables, reference or date(2026, 8, 22))


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


def test_planning_returns_camel_case_contract(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "segredo-de-teste")
    monkeypatch.setattr(api_main, "load_planning_dashboard", sample_planning)

    response = client.get(
        "/v1/planning",
        headers={"X-Nexo-Token": "segredo-de-teste"},
    )

    assert response.status_code == 200
    assert response.json()["date"] == "2026-08-22"
    assert response.json()["summary"]["studyHours"] == 0
    assert response.json()["week"][5]["isToday"] is True


def test_planning_uses_the_same_token_guard(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "segredo-de-teste")

    response = client.get(
        "/v1/planning",
        headers={"X-Nexo-Token": "incorreto"},
    )

    assert response.status_code == 401


def test_routine_accepts_a_selected_date(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "segredo-de-teste")
    monkeypatch.setattr(api_main, "load_routine_dashboard", sample_routine)

    response = client.get(
        "/v1/routine?date=2026-08-24",
        headers={"X-Nexo-Token": "segredo-de-teste"},
    )

    assert response.status_code == 200
    assert response.json()["date"] == "2026-08-24"
    assert response.json()["fixedCount"] == 0


def test_routine_rejects_an_invalid_date(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "segredo-de-teste")

    response = client.get(
        "/v1/routine?date=ontem",
        headers={"X-Nexo-Token": "segredo-de-teste"},
    )

    assert response.status_code == 422
