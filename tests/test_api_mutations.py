from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from api.mutations import (
    NexoMutationError,
    install_mutation_support,
    mutation_lock,
    require_api_writes,
)
from api.security import require_api_token
from modules.gamification import xp_write_lock


def build_probe_app():
    probe = FastAPI()
    install_mutation_support(probe)

    @probe.post("/probe")
    def write_probe(_=Depends(require_api_writes)):
        return {"ok": True}

    @probe.get("/token")
    def token_probe(_=Depends(require_api_token)):
        return {"ok": True}

    @probe.get("/error")
    def error_probe():
        raise NexoMutationError(409, "conflict", "A operação conflitou.")

    return probe


def test_write_gate_is_closed_when_environment_is_missing(monkeypatch):
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)

    response = TestClient(build_probe_app()).post("/probe")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "writes_disabled"
    assert response.json()["error"]["operationId"]
    assert response.headers["X-Request-ID"]


def test_write_gate_accepts_only_explicit_true(monkeypatch):
    monkeypatch.setenv("NEXO_API_WRITES_ENABLED", "true")

    response = TestClient(build_probe_app()).post(
        "/probe",
        headers={"X-Request-ID": "request-test-1"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "request-test-1"


def test_mutation_error_has_stable_contract_and_safe_operation_id():
    response = TestClient(build_probe_app()).get(
        "/error",
        headers={"X-Request-ID": "not valid because of spaces"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "conflict",
            "message": "A operação conflitou.",
            "operationId": response.headers["X-Request-ID"],
        }
    }
    assert response.headers["X-Request-ID"] != "not valid because of spaces"


def test_api_token_dependency_accepts_only_configured_server_token(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test-token")

    response = TestClient(build_probe_app()).get(
        "/token",
        headers={"X-Nexo-Token": "invalid-token"},
    )

    assert response.status_code == 401
    assert "server-test-token" not in response.text


def test_api_token_dependency_reports_missing_configuration_without_secret(monkeypatch):
    monkeypatch.delenv("NEXO_API_TOKEN", raising=False)

    response = TestClient(build_probe_app()).get("/token")

    assert response.status_code == 503
    assert "NEXO_API_TOKEN" not in response.text


def test_mutation_lock_reuses_the_reentrant_xp_lock():
    lock = mutation_lock()

    assert lock is xp_write_lock()
    with lock:
        with mutation_lock():
            pass
