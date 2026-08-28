import json
import logging
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

import api.task_mutations as task_mutations
import api.mutation_audit as mutation_audit
from api.main import app
from modules import database
from modules.config import SHEETS


client = TestClient(app)
HEADERS = {"X-Nexo-Token": "server-test", "X-Request-ID": "task-request-1"}
PAYLOAD = {
    "id": "0f3ac9b0-5779-40ce-834d-40a8657684af",
    "date": "2026-08-23",
    "title": "Revisar matemática",
    "category": "Estudo",
}
MALFORMED_JSON = b'{"id":'


def structured_mutation_events(caplog):
    return [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == mutation_audit.__name__
        and record.getMessage().startswith("{")
    ]


class FakeTaskWorksheet:
    def __init__(self, fail_after_first_append=False):
        self.rows = []
        self.append_attempts = 0
        self.value_input_options = []
        self.fail_after_first_append = fail_after_first_append

    def get(self, pad_values):
        assert pad_values is True
        return [list(SHEETS["Tarefas"]), *[list(row) for row in self.rows]]

    def append_row(self, values, value_input_option):
        assert value_input_option in {"RAW", "USER_ENTERED"}
        self.append_attempts += 1
        self.value_input_options.append(value_input_option)
        persisted = list(values)
        if value_input_option == "USER_ENTERED":
            persisted = [
                int(value)
                if isinstance(value, str) and value.isdigit()
                else value
                for value in persisted
            ]
        self.rows.append(persisted)
        if self.fail_after_first_append and self.append_attempts == 1:
            raise RuntimeError("a resposta do append foi perdida")


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
    cache_clears = []
    monkeypatch.setattr(
        task_mutations,
        "clear_dashboard_cache",
        lambda: cache_clears.append(True),
    )

    response = client.post(
        "/v1/tasks",
        json=PAYLOAD,
        headers={"X-Request-ID": "task-request-1"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "invalid_token",
            "message": "Token inválido.",
            "operationId": "task-request-1",
        }
    }
    assert "server-test" not in response.text
    assert cache_clears == []


def test_task_creation_rejects_wrong_token_before_write_gate(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)
    forbid_domain_call(monkeypatch)
    cache_clears = []
    monkeypatch.setattr(
        task_mutations,
        "clear_dashboard_cache",
        lambda: cache_clears.append(True),
    )

    response = client.post(
        "/v1/tasks",
        json=PAYLOAD,
        headers={"X-Nexo-Token": "wrong", "X-Request-ID": "task-request-1"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"
    assert response.json()["error"]["operationId"] == "task-request-1"
    assert "server-test" not in response.text
    assert cache_clears == []


def test_task_creation_maps_missing_token_configuration(monkeypatch):
    monkeypatch.delenv("NEXO_API_TOKEN", raising=False)
    monkeypatch.setenv("NEXO_API_WRITES_ENABLED", "true")
    forbid_domain_call(monkeypatch)

    response = client.post(
        "/v1/tasks",
        json=PAYLOAD,
        headers={"X-Nexo-Token": "unused", "X-Request-ID": "task-request-1"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "authentication_unavailable"
    assert response.json()["error"]["operationId"] == "task-request-1"


def test_task_creation_is_blocked_by_default(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)
    forbid_domain_call(monkeypatch)
    cache_clears = []
    monkeypatch.setattr(
        task_mutations,
        "clear_dashboard_cache",
        lambda: cache_clears.append(True),
    )

    response = client.post("/v1/tasks", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "writes_disabled"
    assert response.json()["error"]["operationId"] == "task-request-1"
    assert cache_clears == []


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


def test_malformed_json_requires_token_before_decoding(monkeypatch):
    enable_mutations(monkeypatch)
    forbid_domain_call(monkeypatch)

    response = client.post(
        "/v1/tasks",
        content=MALFORMED_JSON,
        headers={
            "Content-Type": "application/json",
            "X-Request-ID": "task-request-1",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"
    assert response.json()["error"]["operationId"] == "task-request-1"


def test_malformed_json_rejects_wrong_token_before_decoding(monkeypatch):
    enable_mutations(monkeypatch)
    forbid_domain_call(monkeypatch)

    response = client.post(
        "/v1/tasks",
        content=MALFORMED_JSON,
        headers={
            "Content-Type": "application/json",
            "X-Nexo-Token": "wrong",
            "X-Request-ID": "task-request-1",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_malformed_json_checks_write_gate_before_decoding(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)
    forbid_domain_call(monkeypatch)

    response = client.post(
        "/v1/tasks",
        content=MALFORMED_JSON,
        headers={
            **HEADERS,
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "writes_disabled"


def test_malformed_json_is_invalid_after_guards_pass(monkeypatch):
    enable_mutations(monkeypatch)
    forbid_domain_call(monkeypatch)
    cache_clears = []
    monkeypatch.setattr(
        task_mutations,
        "clear_dashboard_cache",
        lambda: cache_clears.append(True),
    )

    response = client.post(
        "/v1/tasks",
        content=MALFORMED_JSON,
        headers={
            **HEADERS,
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert response.json()["error"]["operationId"] == "task-request-1"
    assert cache_clears == []


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


@pytest.mark.parametrize(
    ("created", "expected_outcome"),
    [(True, "create"), (False, "replay")],
)
def test_task_creation_logs_one_safe_structured_success_event(
    monkeypatch,
    caplog,
    created,
    expected_outcome,
):
    """Removing a required audit field or logging task content must fail."""
    enable_mutations(monkeypatch)
    caplog.set_level(logging.INFO, logger=mutation_audit.__name__)
    monkeypatch.setattr(
        task_mutations.tasks,
        "add",
        lambda title, category, target, item_id: ({
            "id": item_id,
            "data": str(target),
            "tarefa": title,
            "categoria": category,
            "status": "Pendente",
        }, created),
    )
    monkeypatch.setattr(task_mutations, "clear_dashboard_cache", lambda: None)

    response = client.post("/v1/tasks", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 200
    events = structured_mutation_events(caplog)
    assert len(events) == 1
    event = events[0]
    assert set(event) == {
        "duration_ms",
        "event",
        "operation_id",
        "outcome",
        "request_id",
        "route",
        "status",
        "resource_id",
        "timestamp",
        "worksheets",
    }
    assert event["event"] == "nexo.task.mutation"
    assert event["operation_id"] == "task-request-1"
    assert event["outcome"] == expected_outcome
    assert event["request_id"] == "task-request-1"
    assert event["route"] == "/v1/tasks"
    assert event["status"] == 200
    assert event["resource_id"] == PAYLOAD["id"]
    assert event["worksheets"] == ["Tarefas"]
    assert isinstance(event["duration_ms"], (int, float))
    assert event["duration_ms"] >= 0
    assert event["timestamp"].endswith("Z")
    serialized = json.dumps(event, ensure_ascii=False)
    assert PAYLOAD["title"] not in serialized
    assert PAYLOAD["category"] not in serialized
    assert HEADERS["X-Nexo-Token"] not in serialized


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

    def append_record(_name, values, value_input_option="USER_ENTERED"):
        assert value_input_option in {"RAW", "USER_ENTERED"}
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


def test_numeric_looking_title_is_persisted_raw_and_retries_identically(monkeypatch):
    enable_mutations(monkeypatch)
    worksheet = FakeTaskWorksheet()
    database.clear_records_cache("Tarefas")
    monkeypatch.setattr(database, "get_worksheet", lambda _name: worksheet)
    monkeypatch.setattr(task_mutations, "clear_dashboard_cache", lambda: None)

    try:
        first = client.post(
            "/v1/tasks",
            json={**PAYLOAD, "title": "001"},
            headers=HEADERS,
        )
        retry = client.post(
            "/v1/tasks",
            json={**PAYLOAD, "title": "001"},
            headers=HEADERS,
        )
    finally:
        database.clear_records_cache("Tarefas")

    assert first.status_code == 200
    assert first.json()["created"] is True
    assert retry.status_code == 200
    assert retry.json()["created"] is False
    assert retry.json()["task"]["title"] == "001"
    assert worksheet.rows[0][2] == "001"
    assert worksheet.append_attempts == 1
    assert worksheet.value_input_options == ["RAW"]


def test_retry_reloads_after_append_persists_but_response_is_lost(monkeypatch):
    enable_mutations(monkeypatch)
    worksheet = FakeTaskWorksheet(fail_after_first_append=True)
    dashboard_cache_clears = []
    database.clear_records_cache("Tarefas")
    monkeypatch.setattr(database, "get_worksheet", lambda _name: worksheet)
    monkeypatch.setattr(
        task_mutations,
        "clear_dashboard_cache",
        lambda: dashboard_cache_clears.append(True),
    )

    try:
        first = client.post("/v1/tasks", json=PAYLOAD, headers=HEADERS)
        retry = client.post("/v1/tasks", json=PAYLOAD, headers=HEADERS)
    finally:
        database.clear_records_cache("Tarefas")

    assert first.status_code == 503
    assert retry.status_code == 200
    assert retry.json()["created"] is False
    assert len(worksheet.rows) == 1
    assert worksheet.append_attempts == 1
    assert dashboard_cache_clears == [True]


def test_retry_after_dashboard_cache_failure_does_not_append_again(monkeypatch):
    enable_mutations(monkeypatch)
    worksheet = FakeTaskWorksheet()
    dashboard_cache_attempts = []
    database.clear_records_cache("Tarefas")
    monkeypatch.setattr(database, "get_worksheet", lambda _name: worksheet)

    def clear_dashboard_cache():
        dashboard_cache_attempts.append(True)
        if len(dashboard_cache_attempts) == 1:
            raise RuntimeError("falha temporária do cache")

    monkeypatch.setattr(task_mutations, "clear_dashboard_cache", clear_dashboard_cache)

    try:
        first = client.post("/v1/tasks", json=PAYLOAD, headers=HEADERS)
        retry = client.post("/v1/tasks", json=PAYLOAD, headers=HEADERS)
    finally:
        database.clear_records_cache("Tarefas")

    assert first.status_code == 503
    assert retry.status_code == 200
    assert retry.json()["created"] is False
    assert len(worksheet.rows) == 1
    assert worksheet.append_attempts == 1
    assert dashboard_cache_attempts == [True, True]


def test_task_creation_maps_id_conflict_without_leaking_content(
    monkeypatch,
    caplog,
):
    enable_mutations(monkeypatch)
    caplog.set_level(logging.INFO, logger=mutation_audit.__name__)
    cache_clears = []

    def conflict(*_args, **_kwargs):
        raise task_mutations.tasks.TaskIdConflict("conteúdo privado")

    monkeypatch.setattr(task_mutations.tasks, "add", conflict)
    monkeypatch.setattr(
        task_mutations,
        "clear_dashboard_cache",
        lambda: cache_clears.append(True),
    )
    response = client.post("/v1/tasks", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "idempotency_conflict"
    assert response.json()["error"]["operationId"] == "task-request-1"
    assert "conteúdo privado" not in response.text
    assert cache_clears == []
    events = structured_mutation_events(caplog)
    assert len(events) == 1
    assert events[0]["outcome"] == "conflict"
    assert events[0]["status"] == 409
    assert events[0]["resource_id"] == PAYLOAD["id"]
    serialized = json.dumps(events[0], ensure_ascii=False)
    assert PAYLOAD["title"] not in serialized
    assert PAYLOAD["category"] not in serialized
    assert HEADERS["X-Nexo-Token"] not in serialized
    assert "conteúdo privado" not in serialized


def test_task_creation_maps_internal_failure_without_leaking_details(
    monkeypatch,
    caplog,
):
    enable_mutations(monkeypatch)
    caplog.set_level(logging.ERROR, logger=mutation_audit.__name__)

    def fail(*_args, **_kwargs):
        raise RuntimeError("segredo interno da planilha")

    monkeypatch.setattr(task_mutations.tasks, "add", fail)
    response = client.post("/v1/tasks", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "write_failed"
    assert response.json()["error"]["operationId"] == "task-request-1"
    assert "segredo interno da planilha" not in response.text
    assert "segredo interno da planilha" not in caplog.text
    events = structured_mutation_events(caplog)
    assert len(events) == 1
    assert events[0]["outcome"] == "failure"
    assert events[0]["status"] == 503
    assert events[0]["resource_id"] == PAYLOAD["id"]
    serialized = json.dumps(events[0], ensure_ascii=False)
    assert PAYLOAD["title"] not in serialized
    assert PAYLOAD["category"] not in serialized
    assert HEADERS["X-Nexo-Token"] not in serialized
    assert "segredo interno da planilha" not in serialized


def test_openapi_declares_one_post_with_real_request_and_error_schemas():
    task_operations = app.openapi()["paths"]["/v1/tasks"]

    assert list(task_operations) == ["post"]
    operation = task_operations["post"]
    request_schema = operation["requestBody"]["content"]["application/json"][
        "schema"
    ]
    assert request_schema["type"] == "object"
    assert set(request_schema["required"]) == {"id", "date", "title", "category"}
    assert request_schema["properties"]["id"]["format"] == "uuid"
    assert request_schema["properties"]["date"]["format"] == "date"
    assert operation["responses"]["422"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/MutationErrorResponse"}
    token_headers = [
        parameter
        for parameter in operation["parameters"]
        if parameter["in"] == "header" and parameter["name"] == "X-Nexo-Token"
    ]
    assert len(token_headers) == 1
    assert token_headers[0]["required"] is True
    assert token_headers[0]["schema"] == {"type": "string"}
    assert "HTTPValidationError" not in str(operation)
