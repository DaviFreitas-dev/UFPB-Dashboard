import json
import logging
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

import api.mutation_audit as mutation_audit
import api.mutations as mutations
import api.sheets as sheets
from api.main import app
from modules import reading


client = TestClient(app)
HEADERS = {"X-Nexo-Token": "server-test", "X-Request-ID": "reading-request-1"}
PAYLOAD = {
    "id": "0f3ac9b0-5779-40ce-834d-40a8657684af",
    "title": "O Hobbit",
    "author": "J. R. R. Tolkien",
    "totalPages": 320,
    "dailyGoal": 20,
}


def enable_mutations(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.setenv("NEXO_API_WRITES_ENABLED", "true")


def test_books_require_token_before_gate_or_domain(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)
    monkeypatch.setattr(reading, "add", lambda *_args, **_kwargs: pytest.fail("must not write"))

    response = client.post("/v1/books", json=PAYLOAD, headers={"X-Request-ID": "reading-request-1"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"
    assert "server-test" not in response.text


def test_books_are_blocked_by_default_before_validation(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)
    monkeypatch.setattr(reading, "add", lambda *_args, **_kwargs: pytest.fail("must not write"))

    response = client.post("/v1/books", json={**PAYLOAD, "title": "   "}, headers=HEADERS)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "writes_disabled"


@pytest.mark.parametrize(
    "changes",
    [{}, {"currentPage": -1}, {"currentPage": 1.5}, {"status": "Pausado"}],
)
def test_patch_rejects_empty_or_invalid_state_before_domain(monkeypatch, changes):
    enable_mutations(monkeypatch)
    monkeypatch.setattr(reading, "set_progress", lambda *_args, **_kwargs: pytest.fail("must not write"), raising=False)

    response = client.patch("/v1/books/book-1", json=changes, headers=HEADERS)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


@pytest.mark.parametrize("field", ["title", "totalPages", "dailyGoal"])
def test_create_validates_required_positive_fields(monkeypatch, field):
    enable_mutations(monkeypatch)
    monkeypatch.setattr(reading, "add", lambda *_args, **_kwargs: pytest.fail("must not write"))
    payload = {**PAYLOAD, field: "   " if field == "title" else 0}

    response = client.post("/v1/books", json=payload, headers=HEADERS)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_create_normalizes_locks_clears_cache_and_returns_contract(monkeypatch):
    enable_mutations(monkeypatch)
    events = []

    @contextmanager
    def tracked_lock():
        events.append("lock-enter")
        try:
            yield
        finally:
            events.append("lock-exit")

    def add(title, author, total, goal, item_id):
        events.append(("add", title, author, total, goal, item_id))
        return ({
            "id": item_id, "titulo": title, "autor": author, "pagina_atual": 0,
            "total_paginas": total, "meta_diaria": goal, "status": "Lendo",
        }, True)

    monkeypatch.setattr(mutations, "mutation_lock", tracked_lock)
    monkeypatch.setattr(reading, "add", add)
    monkeypatch.setattr(sheets, "clear_dashboard_cache", lambda: events.append("cache-clear"))

    response = client.post("/v1/books", json={**PAYLOAD, "title": "  O Hobbit  ", "author": " Tolkien "}, headers=HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "operationId": "reading-request-1", "created": True,
        "book": {"id": PAYLOAD["id"], "title": "O Hobbit", "author": "Tolkien", "currentPage": 0,
                 "totalPages": 320, "dailyGoal": 20, "status": "Lendo"},
    }
    assert events == ["lock-enter", ("add", "O Hobbit", "Tolkien", 320, 20, PAYLOAD["id"]), "lock-exit", "cache-clear"]


def test_create_maps_conflict_and_never_leaks_content(monkeypatch, caplog):
    enable_mutations(monkeypatch)
    caplog.set_level(logging.INFO, logger=mutation_audit.__name__)
    monkeypatch.setattr(reading, "add", lambda *_args, **_kwargs: (_ for _ in ()).throw(reading.ReadingIdConflict("conteúdo privado")), raising=False)

    response = client.post("/v1/books", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "idempotency_conflict"
    assert "conteúdo privado" not in response.text
    assert PAYLOAD["title"] not in caplog.text
    events = [json.loads(record.getMessage()) for record in caplog.records if record.name == mutation_audit.__name__ and record.getMessage().startswith("{")]
    assert len(events) == 1
    assert events[0]["event"] == "nexo.reading.mutation"
    assert events[0]["outcome"] == "conflict"


def test_patch_confirms_complete_and_reopen_preserves_page(monkeypatch):
    enable_mutations(monkeypatch)
    calls = []
    rows = [
        {"id": "book-1", "titulo": "Livro", "autor": "Autor", "pagina_atual": 40, "total_paginas": 100, "meta_diaria": 10, "status": "Lendo"},
    ]

    def set_progress(item_id, **changes):
        calls.append((item_id, changes))
        row = rows[0]
        if changes.get("status") == "Concluído":
            row.update(pagina_atual=100, status="Concluído")
        elif changes.get("status") == "Lendo":
            row.update(status="Lendo")
        return row.copy(), True

    monkeypatch.setattr(reading, "set_progress", set_progress, raising=False)
    monkeypatch.setattr(sheets, "clear_dashboard_cache", lambda: None)

    complete = client.patch("/v1/books/book-1", json={"status": "Concluído"}, headers=HEADERS)
    reopen = client.patch("/v1/books/book-1", json={"status": "Lendo"}, headers=HEADERS)

    assert complete.status_code == reopen.status_code == 200
    assert complete.json()["book"]["currentPage"] == 100
    assert reopen.json()["book"]["currentPage"] == 100
    assert calls == [("book-1", {"current_page": None, "status": "Concluído"}), ("book-1", {"current_page": None, "status": "Lendo"})]


def test_patch_maps_missing_and_domain_bounds(monkeypatch):
    enable_mutations(monkeypatch)
    monkeypatch.setattr(reading, "set_progress", lambda *_args, **_kwargs: (None, False), raising=False)
    missing = client.patch("/v1/books/book-1", json={"currentPage": 10}, headers=HEADERS)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "record_not_found"

    monkeypatch.setattr(reading, "set_progress", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("fora do livro")), raising=False)
    invalid = client.patch("/v1/books/book-1", json={"currentPage": 10}, headers=HEADERS)
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_request"
    assert "fora do livro" not in invalid.text


def test_delete_is_idempotent_and_uses_safe_opaque_id(monkeypatch):
    enable_mutations(monkeypatch)
    received = []
    monkeypatch.setattr(reading, "remove", lambda item_id: received.append(item_id) or False)
    monkeypatch.setattr(sheets, "clear_dashboard_cache", lambda: None)

    response = client.delete("/v1/books/legacy/folder.item", headers=HEADERS)

    assert response.status_code == 200
    assert response.json() == {"operationId": "reading-request-1", "id": "legacy/folder.item", "deleted": False}
    assert received == ["legacy/folder.item"]


@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
def test_lifecycle_rejects_unsafe_or_oversized_ids(monkeypatch, method):
    enable_mutations(monkeypatch)
    monkeypatch.setattr(reading, "set_progress", lambda *_args, **_kwargs: pytest.fail("must not write"), raising=False)
    monkeypatch.setattr(reading, "remove", lambda *_args: pytest.fail("must not write"))

    response = client.request(method, f"/v1/books/{'x' * 513}", json={"status": "Lendo"} if method == "PATCH" else None, headers=HEADERS)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
