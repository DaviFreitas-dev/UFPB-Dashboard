import logging
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

import api.task_mutations as task_mutations
from api.main import app


client = TestClient(app)
HEADERS = {"X-Nexo-Token": "server-test", "X-Request-ID": "task-request-1"}
PAYLOAD = {
    "id": "0f3ac9b0-5779-40ce-834d-40a8657684af",
    "date": "2026-08-23",
    "title": "Revisar matemática",
    "category": "Estudo",
}


def enable_mutations(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.setenv("NEXO_API_WRITES_ENABLED", "true")


def forbid_domain_call(monkeypatch):
    monkeypatch.setattr(
        task_mutations.tasks,
        "add",
        lambda *_args, **_kwargs: pytest.fail("request must not reach the domain"),
    )


def test_task_creation_requires_token_before_write_gate(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)
    forbid_domain_call(monkeypatch)

    response = client.post("/v1/tasks", json=PAYLOAD)

    assert response.status_code == 401
    assert "server-test" not in response.text


def test_task_creation_rejects_wrong_token_before_write_gate(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)
    forbid_domain_call(monkeypatch)

    response = client.post(
        "/v1/tasks",
        json=PAYLOAD,
        headers={"X-Nexo-Token": "wrong"},
    )

    assert response.status_code == 401
    assert "server-test" not in response.text


def test_task_creation_is_blocked_by_default(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)
    forbid_domain_call(monkeypatch)

    response = client.post("/v1/tasks", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "writes_disabled"


def test_write_gate_runs_before_payload_validation(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)
    forbid_domain_call(monkeypatch)

    response = client.post(
        "/v1/tasks",
        json={**PAYLOAD, "title": "   "},
        headers=HEADERS,
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "writes_disabled"


def test_task_creation_normalizes_then_locks_domain_and_clears_cache(monkeypatch):
    enable_mutations(monkeypatch)
    events = []

    @contextmanager
    def tracked_lock():
        events.append("lock-enter")
        try:
            yield
        finally:
            events.append("lock-exit")

    def add(title, category, target, item_id):
        events.append(("add", title, category, str(target), item_id))
        assert events[0] == "lock-enter"
        return ({
            "id": item_id,
            "data": str(target),
            "tarefa": title,
            "categoria": category,
            "status": "Pendente",
        }, True)

    monkeypatch.setattr(task_mutations, "mutation_lock", tracked_lock)
    monkeypatch.setattr(task_mutations.tasks, "add", add)
    monkeypatch.setattr(
        task_mutations,
        "clear_dashboard_cache",
        lambda: events.append("cache-clear"),
    )

    response = client.post(
        "/v1/tasks",
        json={
            **PAYLOAD,
            "title": "  Revisar matemática  ",
            "category": "  Estudo  ",
        },
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "operationId": "task-request-1",
        "created": True,
        "task": {
            "id": PAYLOAD["id"],
            "date": PAYLOAD["date"],
            "title": PAYLOAD["title"],
            "category": PAYLOAD["category"],
            "completed": False,
        },
    }
    assert events == [
        "lock-enter",
        (
            "add",
            PAYLOAD["title"],
            PAYLOAD["category"],
            PAYLOAD["date"],
            PAYLOAD["id"],
        ),
        "lock-exit",
        "cache-clear",
    ]


def test_task_creation_rejects_empty_title_before_domain(monkeypatch):
    enable_mutations(monkeypatch)
    forbid_domain_call(monkeypatch)

    response = client.post(
        "/v1/tasks",
        json={**PAYLOAD, "title": "   "},
        headers=HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert response.json()["error"]["operationId"] == "task-request-1"


def test_task_creation_requires_stable_uuid_before_domain(monkeypatch):
    enable_mutations(monkeypatch)
    forbid_domain_call(monkeypatch)

    response = client.post(
        "/v1/tasks",
        json={key: value for key, value in PAYLOAD.items() if key != "id"},
        headers=HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_task_creation_reports_identical_retry_without_second_append(monkeypatch):
    enable_mutations(monkeypatch)
    stored = []
    cache_clears = []

    monkeypatch.setattr(task_mutations.tasks, "records", lambda _name: stored)

    def append_record(_name, values):
        stored.append(dict(zip(
            ("id", "data", "tarefa", "categoria", "status"),
            values,
        )))

    monkeypatch.setattr(task_mutations.tasks, "append_record", append_record)
    monkeypatch.setattr(
        task_mutations,
        "clear_dashboard_cache",
        lambda: cache_clears.append(True),
    )

    first = client.post("/v1/tasks", json=PAYLOAD, headers=HEADERS)
    retry = client.post("/v1/tasks", json=PAYLOAD, headers=HEADERS)

    assert first.status_code == 200
    assert first.json()["created"] is True
    assert retry.status_code == 200
    assert retry.json()["created"] is False
    assert retry.json()["task"] == first.json()["task"]
    assert len(stored) == 1
    assert cache_clears == [True, True]


def test_task_creation_maps_id_conflict_without_leaking_content(monkeypatch):
    enable_mutations(monkeypatch)

    def conflict(*_args, **_kwargs):
        raise task_mutations.tasks.TaskIdConflict("conteúdo privado")

    monkeypatch.setattr(task_mutations.tasks, "add", conflict)
    response = client.post("/v1/tasks", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "idempotency_conflict"
    assert response.json()["error"]["operationId"] == "task-request-1"
    assert "conteúdo privado" not in response.text


def test_task_creation_maps_internal_failure_without_leaking_details(
    monkeypatch,
    caplog,
):
    enable_mutations(monkeypatch)
    caplog.set_level(logging.ERROR, logger=task_mutations.__name__)

    def fail(*_args, **_kwargs):
        raise RuntimeError("segredo interno da planilha")

    monkeypatch.setattr(task_mutations.tasks, "add", fail)
    response = client.post("/v1/tasks", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "write_failed"
    assert response.json()["error"]["operationId"] == "task-request-1"
    assert "segredo interno da planilha" not in response.text
    assert "segredo interno da planilha" not in caplog.text
