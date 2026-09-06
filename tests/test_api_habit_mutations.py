import importlib
from contextlib import contextmanager
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter, ValidationError

from api.main import app
from modules import habits


client = TestClient(app)
HEADERS = {
    "X-Nexo-Token": "server-test",
    "X-Request-ID": "habit-request-1",
}
CONFIG_ID = "398615a3-c08d-4f42-a9f4-b5d5c5c94515"
LOG_ID = "5a70642d-874d-52fb-9653-5a49ff00882b"


def habit_api():
    return importlib.import_module("api.habit_mutations")


def enable_mutations(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.setenv("NEXO_API_WRITES_ENABLED", "true")


def test_create_returns_conflict_for_reused_id(monkeypatch):
    enable_mutations(monkeypatch)
    monkeypatch.setattr(habits, "records", lambda _name: [
        {"id": CONFIG_ID, "nome": "Ler", "ativo": "Sim"},
    ])
    monkeypatch.setattr(habits, "append_record", lambda *a, **kw: pytest.fail("must not duplicate"))
    response = client.post("/v1/habits", json={"id": CONFIG_ID, "name": "Caminhar"}, headers=HEADERS)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "idempotency_conflict"


def forbid_domain_calls(monkeypatch):
    monkeypatch.setattr(
        habits,
        "add",
        lambda *_args, **_kwargs: pytest.fail("request must not create"),
    )
    monkeypatch.setattr(
        habits,
        "set_active",
        lambda *_args, **_kwargs: pytest.fail("request must not archive"),
        raising=False,
    )
    monkeypatch.setattr(
        habits,
        "set_completed",
        lambda *_args, **_kwargs: pytest.fail("request must not check in"),
        raising=False,
    )


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", "/v1/habits", {"id": CONFIG_ID, "name": "Ler"}),
        ("PATCH", f"/v1/habits/{CONFIG_ID}", {"active": False}),
        (
            "PUT",
            f"/v1/habit-checkins/{CONFIG_ID}/2026-08-25",
            {"completed": True},
        ),
    ],
)
def test_habit_mutations_require_token_before_write_gate(
    monkeypatch, method, path, body
):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)
    forbid_domain_calls(monkeypatch)

    response = client.request(method, path, json=body)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_create_checks_gate_before_body_validation(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)
    forbid_domain_calls(monkeypatch)

    response = client.post(
        "/v1/habits",
        content=b"{",
        headers={**HEADERS, "Content-Type": "application/json"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "writes_disabled"


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"id": "not-a-uuid", "name": "Ler"}, "id"),
        ({"id": CONFIG_ID, "name": "   "}, "name"),
        ({"id": CONFIG_ID, "name": "x" * 81}, "name"),
    ],
)
def test_create_rejects_invalid_payload_before_domain(monkeypatch, payload, field):
    enable_mutations(monkeypatch)
    forbid_domain_calls(monkeypatch)

    response = client.post("/v1/habits", json=payload, headers=HEADERS)

    assert response.status_code == 422, field
    assert response.json()["error"]["code"] == "invalid_request"


@pytest.mark.parametrize(("path", "field"), [("habits", "active"), ("habit-checkins", "completed")])
@pytest.mark.parametrize("value", ["true", "false", 1, 0, None])
def test_state_endpoints_require_strict_json_booleans(monkeypatch, path, field, value):
    enable_mutations(monkeypatch)
    forbid_domain_calls(monkeypatch)
    target = (
        f"/v1/habits/{CONFIG_ID}"
        if path == "habits"
        else f"/v1/habit-checkins/{CONFIG_ID}/2026-08-25"
    )

    response = client.request(
        "PATCH" if path == "habits" else "PUT",
        target,
        json={field: value},
        headers=HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_create_locks_normalized_call_and_invalidates_all_habit_caches(monkeypatch):
    enable_mutations(monkeypatch)
    api = habit_api()
    events = []

    @contextmanager
    def tracked_lock():
        events.append("lock-enter")
        try:
            yield
        finally:
            events.append("lock-exit")

    def add(name, item_id=None):
        assert events == ["lock-enter"]
        events.append(("add", name, item_id))
        return {"id": item_id, "nome": name, "ativo": "Sim"}, True, False

    monkeypatch.setattr(api.mutations, "mutation_lock", tracked_lock)
    monkeypatch.setattr(habits, "add", add)
    monkeypatch.setattr(
        api,
        "clear_records_cache",
        lambda name: events.append(("records-cache", name)),
    )
    monkeypatch.setattr(
        api.sheets,
        "clear_dashboard_cache",
        lambda: events.append("dashboard-cache"),
    )

    response = client.post(
        "/v1/habits",
        json={"id": CONFIG_ID, "name": "  Ler   vinte páginas  "},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "operationId": "habit-request-1",
        "created": True,
        "reactivated": False,
        "habit": {
            "configId": CONFIG_ID,
            "title": "Ler vinte páginas",
            "active": True,
        },
    }
    assert events == [
        "lock-enter",
        ("add", "Ler vinte páginas", CONFIG_ID),
        "lock-exit",
        ("records-cache", "HabitosConfig"),
        ("records-cache", "Habitos"),
        "dashboard-cache",
    ]


def test_create_reports_reactivation_without_claiming_creation(monkeypatch):
    enable_mutations(monkeypatch)
    api = habit_api()
    monkeypatch.setattr(
        habits,
        "add",
        lambda name, item_id=None: (
            {"id": "legacy-config", "nome": "Ler", "ativo": "Sim"},
            False,
            True,
        ),
    )
    monkeypatch.setattr(api, "clear_records_cache", lambda _name: None)
    monkeypatch.setattr(api.sheets, "clear_dashboard_cache", lambda: None)

    response = client.post(
        "/v1/habits",
        json={"id": CONFIG_ID, "name": "Ler"},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["created"] is False
    assert response.json()["reactivated"] is True
    assert response.json()["habit"]["configId"] == "legacy-config"


def test_archive_uses_desired_state_under_the_lock(monkeypatch):
    enable_mutations(monkeypatch)
    api = habit_api()
    events = []

    @contextmanager
    def tracked_lock():
        events.append("lock-enter")
        try:
            yield
        finally:
            events.append("lock-exit")

    def set_active(config_id, active):
        assert events == ["lock-enter"]
        events.append(("set-active", config_id, active))
        return {"id": config_id, "nome": "Ler", "ativo": "Não"}, True

    monkeypatch.setattr(api.mutations, "mutation_lock", tracked_lock)
    monkeypatch.setattr(habits, "set_active", set_active, raising=False)
    monkeypatch.setattr(api, "clear_records_cache", lambda name: events.append(("cache", name)))
    monkeypatch.setattr(api.sheets, "clear_dashboard_cache", lambda: events.append("dashboard"))

    response = client.patch(
        f"/v1/habits/{CONFIG_ID}",
        json={"active": False},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["changed"] is True
    assert response.json()["habit"]["active"] is False
    assert events[:3] == ["lock-enter", ("set-active", CONFIG_ID, False), "lock-exit"]


def test_checkin_accepts_a_missing_log_id_and_confirms_the_requested_state(monkeypatch):
    enable_mutations(monkeypatch)
    api = habit_api()
    monkeypatch.setattr(
        habits,
        "set_completed",
        lambda config_id, target, completed: (
            {
                "id": None,
                "config_id": config_id,
                "data": str(target),
                "habito": "Ler",
                "feito": "Não",
            },
            False,
        ),
        raising=False,
    )
    monkeypatch.setattr(api, "clear_records_cache", lambda _name: None)
    monkeypatch.setattr(api.sheets, "clear_dashboard_cache", lambda: None)

    response = client.put(
        f"/v1/habit-checkins/{CONFIG_ID}/2026-08-25",
        json={"completed": False},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "operationId": "habit-request-1",
        "changed": False,
        "checkin": {
            "configId": CONFIG_ID,
            "logId": None,
            "date": "2026-08-25",
            "title": "Ler",
            "completed": False,
        },
    }


def test_checkin_preserves_an_opaque_config_id_with_encoded_slashes(monkeypatch):
    enable_mutations(monkeypatch)
    api = habit_api()
    opaque_id = "legacy/folder/habit"
    received = []

    def set_completed(config_id, target, completed):
        received.append((config_id, str(target), completed))
        return {
            "id": "legacy-log",
            "config_id": config_id,
            "data": str(target),
            "habito": "Ler",
            "feito": "Sim",
        }, True

    monkeypatch.setattr(habits, "set_completed", set_completed)
    monkeypatch.setattr(api, "clear_records_cache", lambda _name: None)
    monkeypatch.setattr(api.sheets, "clear_dashboard_cache", lambda: None)

    response = client.put(
        f"/v1/habit-checkins/{quote(opaque_id, safe='')}/2026-08-25",
        json={"completed": True},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["checkin"]["configId"] == opaque_id
    assert received == [(opaque_id, "2026-08-25", True)]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("PATCH", f"/v1/habits/{CONFIG_ID}", {"active": False}),
        (
            "PUT",
            f"/v1/habit-checkins/{CONFIG_ID}/2026-08-25",
            {"completed": True},
        ),
    ],
)
def test_state_endpoints_report_missing_config_without_cache_clear(
    monkeypatch, method, path, body
):
    enable_mutations(monkeypatch)
    api = habit_api()
    monkeypatch.setattr(habits, "set_active", lambda *_args: (None, False), raising=False)
    monkeypatch.setattr(habits, "set_completed", lambda *_args: (None, False), raising=False)
    monkeypatch.setattr(
        api,
        "clear_records_cache",
        lambda _name: pytest.fail("missing config must not clear cache"),
    )
    monkeypatch.setattr(
        api.sheets,
        "clear_dashboard_cache",
        lambda: pytest.fail("missing config must not clear cache"),
    )

    response = client.request(method, path, json=body, headers=HEADERS)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "record_not_found"


@pytest.mark.parametrize("config_id", ["%20%20", "i" * 513])
def test_state_routes_reject_unsafe_persistent_config_ids(monkeypatch, config_id):
    enable_mutations(monkeypatch)
    forbid_domain_calls(monkeypatch)

    response = client.patch(
        f"/v1/habits/{config_id}",
        json={"active": False},
        headers=HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


@pytest.mark.parametrize("config_id", [".", ".."])
def test_persistent_config_contract_rejects_dot_segments(config_id):
    with pytest.raises(ValidationError):
        TypeAdapter(habit_api().HabitConfigPathId).validate_python(config_id)
