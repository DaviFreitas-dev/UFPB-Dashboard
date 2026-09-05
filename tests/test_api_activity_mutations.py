from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from api import mutations, sheets
from api.main import app
from modules import activity


client = TestClient(app)
HEADERS = {
    "X-Nexo-Token": "server-test",
    "X-Request-ID": "activity-request-1",
}
PAYLOAD = {
    "id": "0f3ac9b0-5779-40ce-834d-40a8657684af",
    "date": "2026-08-25",
    "type": "Corrida",
}


def enable_mutations(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.setenv("NEXO_API_WRITES_ENABLED", "true")


def forbid_domain(monkeypatch):
    monkeypatch.setattr(
        activity,
        "add",
        lambda *_args, **_kwargs: pytest.fail("must not reach domain"),
    )


def test_activity_creation_requires_token_before_write_gate(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)
    forbid_domain(monkeypatch)

    response = client.post(
        "/v1/activities",
        json=PAYLOAD,
        headers={"X-Request-ID": "activity-request-1"},
    )

    assert response.status_code == 401
    assert response.json()["error"] == {
        "code": "invalid_token",
        "message": "Token inválido.",
        "operationId": "activity-request-1",
    }


def test_activity_creation_checks_write_gate_before_body(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)
    forbid_domain(monkeypatch)
    body = b'{"id":'

    response = client.post(
        "/v1/activities",
        content=body,
        headers={**HEADERS, "Content-Type": "application/json"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "writes_disabled"


@pytest.mark.parametrize(
    "changes",
    [
        {"date": "25/08/2026"},
        {"type": "Natação"},
        {"type": "   "},
        {"id": "not-a-uuid"},
    ],
)
def test_activity_creation_validates_contract_before_domain(monkeypatch, changes):
    enable_mutations(monkeypatch)
    forbid_domain(monkeypatch)

    response = client.post(
        "/v1/activities",
        json={**PAYLOAD, **changes},
        headers=HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_activity_creation_normalizes_locks_confirms_and_clears_cache(monkeypatch):
    enable_mutations(monkeypatch)
    events = []

    @contextmanager
    def tracked_lock():
        events.append("lock-enter")
        try:
            yield
        finally:
            events.append("lock-exit")

    def add(activity_type, target_date, item_id):
        assert events == ["lock-enter"]
        events.append(("add", activity_type, str(target_date), item_id))
        return (
            {
                "id": item_id,
                "data": str(target_date),
                "tipo": activity_type,
                "feito": "Sim",
            },
            True,
            True,
        )

    monkeypatch.setattr(mutations, "mutation_lock", tracked_lock)
    monkeypatch.setattr(activity, "add", add)
    monkeypatch.setattr(
        sheets,
        "clear_dashboard_cache",
        lambda: events.append("cache-clear"),
    )

    response = client.post(
        "/v1/activities",
        json={**PAYLOAD, "type": "  Outro  "},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "operationId": "activity-request-1",
        "created": True,
        "changed": True,
        "activity": {
            "id": PAYLOAD["id"],
            "date": "2026-08-25",
            "type": "Outro",
            "completed": True,
        },
    }
    assert events == [
        "lock-enter",
        ("add", "Outro", "2026-08-25", PAYLOAD["id"]),
        "lock-exit",
        "cache-clear",
    ]


def test_activity_creation_confirms_semantic_replay_with_existing_id(monkeypatch):
    enable_mutations(monkeypatch)
    monkeypatch.setattr(
        activity,
        "add",
        lambda *_args, **_kwargs: (
            {
                "id": "legacy-id",
                "data": "2026-08-25",
                "tipo": "corrida",
                "feito": "Sim",
            },
            False,
            False,
        ),
    )
    monkeypatch.setattr(sheets, "clear_dashboard_cache", lambda: None)

    response = client.post("/v1/activities", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 200
    assert response.json()["activity"]["id"] == "legacy-id"
    assert response.json()["created"] is False
    assert response.json()["changed"] is False


def test_completed_idless_legacy_replay_does_not_invent_persisted_id(
    monkeypatch,
):
    enable_mutations(monkeypatch)
    monkeypatch.setattr(
        activity,
        "add",
        lambda *_args, **_kwargs: (
            {
                "data": "2026-08-25",
                "tipo": "Corrida",
                "feito": "Sim",
            },
            False,
            False,
        ),
    )
    monkeypatch.setattr(sheets, "clear_dashboard_cache", lambda: None)

    response = client.post("/v1/activities", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 200
    assert response.json()["activity"]["id"] is None


def test_activity_id_conflict_is_safe_and_does_not_clear_cache(monkeypatch):
    enable_mutations(monkeypatch)
    monkeypatch.setattr(
        activity,
        "add",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            activity.ActivityIdConflict("private row content")
        ),
    )
    monkeypatch.setattr(
        sheets,
        "clear_dashboard_cache",
        lambda: pytest.fail("conflict must not clear API cache"),
    )

    response = client.post("/v1/activities", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "idempotency_conflict"
    assert "private row content" not in response.text


def test_activity_failure_after_domain_is_not_reported_as_success(monkeypatch):
    enable_mutations(monkeypatch)
    monkeypatch.setattr(
        activity,
        "add",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("private spreadsheet detail")
        ),
    )
    monkeypatch.setattr(
        sheets,
        "clear_dashboard_cache",
        lambda: pytest.fail("failure must not clear API cache"),
    )

    response = client.post("/v1/activities", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "write_failed"
    assert "private spreadsheet detail" not in response.text


def test_openapi_declares_activity_post_contract():
    operation = app.openapi()["paths"]["/v1/activities"]["post"]
    schema = operation["requestBody"]["content"]["application/json"]["schema"]

    assert set(schema["required"]) == {"id", "date", "type"}
    assert schema["properties"]["id"]["format"] == "uuid"
    assert schema["properties"]["date"]["format"] == "date"
    assert operation["responses"]["422"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/MutationErrorResponse"}
