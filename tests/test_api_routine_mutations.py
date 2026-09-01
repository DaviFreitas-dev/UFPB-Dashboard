import json
import logging
from contextlib import contextmanager
from datetime import date

import pytest
from fastapi.testclient import TestClient

from api import mutation_audit, mutations, sheets
from api.main import app
from api.routine import build_routine_dashboard
from api.sheets import DASHBOARD_SHEETS
from modules import routine


client = TestClient(app)
HEADERS = {
    "X-Nexo-Token": "server-test",
    "X-Request-ID": "routine-request-1",
}
PAYLOAD = {
    "id": "0f3ac9b0-5779-40ce-834d-40a8657684af",
    "date": "2026-08-25",
    "time": "08:30",
    "title": "  Dentista  ",
}


def enable_mutations(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.setenv("NEXO_API_WRITES_ENABLED", "true")


def routine_record(status="Pendente"):
    return {
        "id": PAYLOAD["id"],
        "data": PAYLOAD["date"],
        "hora": PAYLOAD["time"],
        "atividade": "Dentista",
        "status": status,
    }


def empty_tables():
    return {name: [] for name in DASHBOARD_SHEETS}


def forbid_domain_calls(monkeypatch):
    monkeypatch.setattr(
        routine,
        "add",
        lambda *_args, **_kwargs: pytest.fail("request must not create"),
    )
    monkeypatch.setattr(
        routine,
        "set_completed",
        lambda *_args, **_kwargs: pytest.fail("request must not update"),
        raising=False,
    )
    monkeypatch.setattr(
        routine,
        "remove",
        lambda *_args, **_kwargs: pytest.fail("request must not delete"),
    )


def structured_mutation_events(caplog):
    return [
        json.loads(record.message)
        for record in caplog.records
        if record.name == mutation_audit.__name__
        and record.message.startswith("{")
    ]


@pytest.mark.parametrize("method", ["post", "patch", "delete"])
def test_routine_mutations_require_token_before_write_gate(monkeypatch, method):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)
    forbid_domain_calls(monkeypatch)
    path = (
        "/v1/routine-items"
        if method == "post"
        else f"/v1/routine-items/{PAYLOAD['id']}"
    )
    body = PAYLOAD if method == "post" else {"completed": True}

    response = client.request(
        method.upper(),
        path,
        json=body if method != "delete" else None,
        headers={"X-Request-ID": "routine-request-1"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_routine_creation_checks_gate_before_body_validation(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)
    forbid_domain_calls(monkeypatch)

    response = client.post(
        "/v1/routine-items",
        content=b"{",
        headers={**HEADERS, "Content-Type": "application/json"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "writes_disabled"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("time", "8:30"),
        ("time", "24:00"),
        ("time", "08:60"),
        ("date", "25/08/2026"),
        ("title", "   "),
        ("title", "x" * 161),
        ("id", "not-a-uuid"),
    ],
)
def test_routine_creation_rejects_invalid_payload_before_domain(
    monkeypatch,
    field,
    value,
):
    enable_mutations(monkeypatch)
    forbid_domain_calls(monkeypatch)

    response = client.post(
        "/v1/routine-items",
        json={**PAYLOAD, field: value},
        headers=HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_routine_creation_locks_normalized_domain_call_and_clears_cache(
    monkeypatch,
):
    enable_mutations(monkeypatch)
    events = []

    @contextmanager
    def tracked_lock():
        events.append("lock-enter")
        try:
            yield
        finally:
            events.append("lock-exit")

    def add(title, time_text, target_date, item_id=None):
        assert events == ["lock-enter"]
        events.append(("add", title, time_text, str(target_date), item_id))
        return routine_record(), True

    monkeypatch.setattr(mutations, "mutation_lock", tracked_lock)
    monkeypatch.setattr(routine, "add", add)
    monkeypatch.setattr(
        sheets,
        "clear_dashboard_cache",
        lambda: events.append("cache-clear"),
    )

    response = client.post("/v1/routine-items", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "operationId": "routine-request-1",
        "created": True,
        "item": {
            "id": PAYLOAD["id"],
            "date": "2026-08-25",
            "time": "08:30",
            "title": "Dentista",
            "completed": False,
        },
    }
    assert events == [
        "lock-enter",
        ("add", "Dentista", "08:30", "2026-08-25", PAYLOAD["id"]),
        "lock-exit",
        "cache-clear",
    ]


def test_routine_creation_trims_before_enforcing_title_limit(monkeypatch):
    enable_mutations(monkeypatch)
    captured = []
    title = "x" * 160

    def add(activity, time_text, target_date, item_id=None):
        captured.append((activity, time_text, str(target_date), item_id))
        return {**routine_record(), "atividade": title}, True

    monkeypatch.setattr(routine, "add", add)
    monkeypatch.setattr(sheets, "clear_dashboard_cache", lambda: None)

    response = client.post(
        "/v1/routine-items",
        json={**PAYLOAD, "title": f"  {title}  "},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["item"]["title"] == title
    assert captured == [(title, "08:30", "2026-08-25", PAYLOAD["id"])]


def test_routine_creation_replays_legacy_record_without_status(monkeypatch):
    enable_mutations(monkeypatch)
    existing = {
        "id": PAYLOAD["id"],
        "data": PAYLOAD["date"],
        "hora": PAYLOAD["time"],
        "atividade": "Dentista",
    }
    cache_clears = []
    monkeypatch.setattr(routine, "records", lambda _name: [existing])
    monkeypatch.setattr(
        routine,
        "append_record",
        lambda *_args, **_kwargs: pytest.fail("replay must not append"),
    )
    monkeypatch.setattr(
        sheets,
        "clear_dashboard_cache",
        lambda: cache_clears.append(True),
    )

    response = client.post("/v1/routine-items", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "operationId": "routine-request-1",
        "created": False,
        "item": {
            "id": PAYLOAD["id"],
            "date": PAYLOAD["date"],
            "time": PAYLOAD["time"],
            "title": "Dentista",
            "completed": False,
        },
    }
    assert cache_clears == [True]


def test_routine_creation_maps_id_conflict_without_cache_clear(monkeypatch):
    enable_mutations(monkeypatch)
    monkeypatch.setattr(
        routine,
        "add",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            routine.RoutineIdConflict("private content")
        ),
    )
    monkeypatch.setattr(
        sheets,
        "clear_dashboard_cache",
        lambda: pytest.fail("conflict must not clear cache"),
    )

    response = client.post("/v1/routine-items", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "idempotency_conflict"
    assert "private content" not in response.text


@pytest.mark.parametrize("completed", ["true", "false", 1, 0, None])
def test_routine_patch_requires_strict_json_boolean(monkeypatch, completed):
    enable_mutations(monkeypatch)
    forbid_domain_calls(monkeypatch)

    response = client.patch(
        f"/v1/routine-items/{PAYLOAD['id']}",
        json={"completed": completed},
        headers=HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_routine_patch_uses_desired_state_lock_and_cache(monkeypatch):
    enable_mutations(monkeypatch)
    events = []

    @contextmanager
    def tracked_lock():
        events.append("lock-enter")
        try:
            yield
        finally:
            events.append("lock-exit")

    def set_completed(item_id, completed):
        assert events == ["lock-enter"]
        events.append(("set-completed", item_id, completed))
        return routine_record("Concluída"), True

    monkeypatch.setattr(mutations, "mutation_lock", tracked_lock)
    monkeypatch.setattr(routine, "set_completed", set_completed, raising=False)
    monkeypatch.setattr(
        sheets,
        "clear_dashboard_cache",
        lambda: events.append("cache-clear"),
    )

    response = client.patch(
        f"/v1/routine-items/{PAYLOAD['id']}",
        json={"completed": True},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["changed"] is True
    assert response.json()["item"]["completed"] is True
    assert events == [
        "lock-enter",
        ("set-completed", PAYLOAD["id"], True),
        "lock-exit",
        "cache-clear",
    ]


def test_persistent_legacy_item_without_time_or_status_mutates_safely_once(
    monkeypatch,
):
    enable_mutations(monkeypatch)
    legacy = {
        "id": "routine-legacy-1",
        "data": "2026-08-25",
        "atividade": "Consulta legada",
    }
    tables = empty_tables()
    tables["Rotina"] = [legacy.copy()]
    read_item = build_routine_dashboard(
        tables,
        date(2026, 8, 25),
    ).items[0]
    assert read_item.source_id == "routine-legacy-1"
    assert read_item.time == "--:--"
    assert read_item.completed is False
    assert read_item.mutable is True

    updates, awards, cache_clears = [], [], []
    monkeypatch.setattr(routine, "records", lambda _name: [legacy])

    def update_record(name, item_id, values):
        updates.append((name, item_id, values))
        legacy.update(values)
        return True

    monkeypatch.setattr(routine, "update_record", update_record)
    monkeypatch.setattr(
        routine,
        "award_xp_once",
        lambda *args: awards.append(args),
    )
    monkeypatch.setattr(
        sheets,
        "clear_dashboard_cache",
        lambda: cache_clears.append(True),
    )

    first = client.patch(
        "/v1/routine-items/routine-legacy-1",
        json={"completed": True},
        headers=HEADERS,
    )
    replay = client.patch(
        "/v1/routine-items/routine-legacy-1",
        json={"completed": True},
        headers=HEADERS,
    )

    assert first.status_code == 200
    assert first.json()["changed"] is True
    assert first.json()["item"] == {
        "id": "routine-legacy-1",
        "date": "2026-08-25",
        "time": "--:--",
        "title": "Consulta legada",
        "completed": True,
    }
    assert replay.status_code == 200
    assert replay.json()["changed"] is False
    assert replay.json()["item"] == first.json()["item"]
    assert updates == [
        (
            "Rotina",
            "routine-legacy-1",
            {"status": "Concluída"},
        )
    ]
    assert awards == [
        (
            "routine:routine-legacy-1",
            10,
            "rotina",
            "Compromisso do dia concluído",
        ),
        (
            "routine:routine-legacy-1",
            10,
            "rotina",
            "Compromisso do dia concluído",
        )
    ]
    assert cache_clears == [True, True]


def test_routine_patch_returns_not_found_without_cache_clear(monkeypatch):
    enable_mutations(monkeypatch)
    monkeypatch.setattr(
        routine,
        "set_completed",
        lambda *_args: (None, False),
        raising=False,
    )
    monkeypatch.setattr(
        sheets,
        "clear_dashboard_cache",
        lambda: pytest.fail("missing row must not clear cache"),
    )

    response = client.patch(
        f"/v1/routine-items/{PAYLOAD['id']}",
        json={"completed": True},
        headers=HEADERS,
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "record_not_found"


def test_routine_delete_is_repeatable_and_clears_cache_each_time(monkeypatch):
    enable_mutations(monkeypatch)
    results = iter([True, False])
    clears = []
    monkeypatch.setattr(routine, "remove", lambda _item_id: next(results))
    monkeypatch.setattr(
        sheets,
        "clear_dashboard_cache",
        lambda: clears.append(True),
    )

    first = client.delete(
        f"/v1/routine-items/{PAYLOAD['id']}",
        headers=HEADERS,
    )
    replay = client.delete(
        f"/v1/routine-items/{PAYLOAD['id']}",
        headers=HEADERS,
    )

    assert first.status_code == 200
    assert first.json()["deleted"] is True
    assert replay.status_code == 200
    assert replay.json()["deleted"] is False
    assert first.json()["id"] == replay.json()["id"] == PAYLOAD["id"]
    assert clears == [True, True]


def test_routine_mutations_log_safe_fields_only(monkeypatch, caplog):
    enable_mutations(monkeypatch)
    caplog.set_level(logging.INFO, logger=mutation_audit.__name__)
    monkeypatch.setattr(routine, "add", lambda *_args, **_kwargs: (routine_record(), False))
    monkeypatch.setattr(sheets, "clear_dashboard_cache", lambda: None)

    response = client.post("/v1/routine-items", json=PAYLOAD, headers=HEADERS)

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
        "resource_id",
        "route",
        "status",
        "timestamp",
        "worksheets",
    }
    assert event["event"] == "nexo.routine.mutation"
    assert event["outcome"] == "replay"
    assert event["route"] == "/v1/routine-items"
    assert event["worksheets"] == ["Rotina"]
    serialized = json.dumps(event, ensure_ascii=False)
    assert "Dentista" not in serialized
    assert HEADERS["X-Nexo-Token"] not in serialized


def test_routine_mutation_hides_internal_storage_failure(monkeypatch, caplog):
    enable_mutations(monkeypatch)
    caplog.set_level(logging.ERROR, logger=mutation_audit.__name__)
    monkeypatch.setattr(
        routine,
        "add",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("secret sheet detail")
        ),
    )

    response = client.post("/v1/routine-items", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "write_failed"
    assert "secret sheet detail" not in response.text
    assert "secret sheet detail" not in caplog.text


def test_openapi_declares_routine_mutation_contracts():
    paths = app.openapi()["paths"]
    assert list(paths["/v1/routine-items"]) == ["post"]
    assert set(paths["/v1/routine-items/{item_id}"]) == {"patch", "delete"}
    request_schema = paths["/v1/routine-items"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]
    assert set(request_schema["required"]) == {"id", "date", "time", "title"}
    assert request_schema["properties"]["id"]["format"] == "uuid"
    assert request_schema["properties"]["date"]["format"] == "date"
