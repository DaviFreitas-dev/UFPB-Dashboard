import pytest

from modules import reading


def test_add_persists_raw_and_replays_identical_content(monkeypatch):
    stored = []
    writes = []
    monkeypatch.setattr(reading, "records", lambda _name: stored)

    def append_record(name, values, value_input_option="USER_ENTERED"):
        writes.append((name, values, value_input_option))
        stored.append(dict(zip(
            ("id", "titulo", "autor", "pagina_atual", "total_paginas", "meta_diaria", "status"),
            values,
        )))

    monkeypatch.setattr(reading, "append_record", append_record)

    created, first_changed = reading.add("001", "  Autor  ", 120, 15, item_id="book-1")
    replay, second_changed = reading.add("001", "Autor", 120, 15, item_id="book-1")

    assert first_changed is True
    assert second_changed is False
    assert replay == created
    assert writes == [(
        "Leitura",
        ["book-1", "001", "Autor", 0, 120, 15, "Lendo"],
        "RAW",
    )]


def test_add_rejects_conflicting_id(monkeypatch):
    monkeypatch.setattr(reading, "records", lambda _name: [{
        "id": "book-1", "titulo": "Outro", "autor": "Autor",
        "pagina_atual": 0, "total_paginas": 120, "meta_diaria": 15,
        "status": "Lendo",
    }])

    with pytest.raises(reading.ReadingIdConflict):
        reading.add("Livro", "Autor", 120, 15, item_id="book-1")


@pytest.mark.parametrize(
    ("title", "total", "goal"),
    [("   ", 100, 10), ("Livro", 0, 10), ("Livro", -1, 10), ("Livro", 100, 0), ("Livro", 100, -1)],
)
def test_add_rejects_invalid_creation_values(monkeypatch, title, total, goal):
    monkeypatch.setattr(reading, "records", lambda _name: [])
    monkeypatch.setattr(reading, "append_record", lambda *_args, **_kwargs: pytest.fail("must not write"))

    with pytest.raises(ValueError):
        reading.add(title, "Autor", total, goal, item_id="book-1")


def test_progress_reaching_last_page_marks_book_complete(monkeypatch):
    stored = {"id": "book-1", "pagina_atual": "20", "total_paginas": "100", "status": "Lendo"}
    updates = []
    monkeypatch.setattr(reading, "records", lambda _name: [stored])
    monkeypatch.setattr(reading, "update_record", lambda _name, _id, values: updates.append(values) or True)

    record, changed = reading.set_progress("book-1", current_page=100)

    assert changed is True
    assert record["pagina_atual"] == 100
    assert record["status"] == "Concluído"
    assert updates == [{"pagina_atual": 100, "status": "Concluído"}]


@pytest.mark.parametrize("page", [-1, 101])
def test_progress_rejects_page_outside_book(monkeypatch, page):
    monkeypatch.setattr(reading, "records", lambda _name: [{
        "id": "book-1", "pagina_atual": "20", "total_paginas": "100", "status": "Lendo",
    }])

    with pytest.raises(ValueError):
        reading.set_progress("book-1", current_page=page)


def test_explicit_complete_sets_page_to_total_and_reopen_preserves_page(monkeypatch):
    stored = {"id": "  legacy/book  ", "pagina_atual": "bad", "total_paginas": "100", "status": ""}
    updates = []
    monkeypatch.setattr(reading, "records", lambda _name: [stored])

    def update_record(_name, raw_id, values):
        updates.append((raw_id, values))
        stored.update(values)
        return True

    monkeypatch.setattr(reading, "update_record", update_record)

    completed, changed = reading.set_progress("legacy/book", status="Concluído")
    reopened, reopened_changed = reading.set_progress("legacy/book", status="Lendo")

    assert changed is True
    assert reopened_changed is True
    assert completed["pagina_atual"] == 100
    assert reopened["pagina_atual"] == 100
    assert updates == [
        ("  legacy/book  ", {"pagina_atual": 100, "status": "Concluído"}),
        ("  legacy/book  ", {"status": "Lendo"}),
    ]


def test_legacy_incomplete_row_and_replay_are_safe(monkeypatch):
    stored = {"id": "book-1", "total_paginas": "invalid"}
    monkeypatch.setattr(reading, "records", lambda _name: [stored])
    monkeypatch.setattr(reading, "update_record", lambda *_args: pytest.fail("must not write"))

    record, changed = reading.set_progress("book-1", current_page=0, status="Lendo")

    assert changed is False
    assert record["pagina_atual"] == 0
    assert record["total_paginas"] == 1
    assert record["status"] == "Lendo"


def test_missing_book_and_repeated_delete_are_noops(monkeypatch):
    monkeypatch.setattr(reading, "records", lambda _name: [])
    monkeypatch.setattr(reading, "delete_record", lambda *_args: pytest.fail("must not delete"))

    assert reading.set_progress("missing", current_page=1) == (None, False)
    assert reading.remove("missing") is False


def test_remove_uses_exact_raw_persisted_id(monkeypatch):
    stored = {"id": "  legacy/book  "}
    deleted = []
    monkeypatch.setattr(reading, "records", lambda _name: [stored])
    monkeypatch.setattr(reading, "delete_record", lambda name, raw_id: deleted.append((name, raw_id)) or True)

    assert reading.remove("legacy/book") is True
    assert deleted == [("Leitura", "  legacy/book  ")]


def test_streamlit_update_wrapper_preserves_legacy_contract(monkeypatch):
    calls = []
    monkeypatch.setattr(reading, "set_progress", lambda item_id, **changes: calls.append((item_id, changes)) or ({}, True))

    assert reading.update("book-1", "12", "Lendo") is None
    assert calls == [("book-1", {"current_page": "12", "status": "Lendo"})]


@pytest.mark.parametrize("value", [True, 1.5, "1.5", float("inf")])
def test_creation_rejects_non_integer_pages_without_writing(monkeypatch, value):
    monkeypatch.setattr(reading, "records", lambda _name: [])
    monkeypatch.setattr(reading, "append_record", lambda *_args, **_kwargs: pytest.fail("must not write"))
    with pytest.raises(ValueError):
        reading.add("Livro", "", value, 10)
    with pytest.raises(ValueError):
        reading.add("Livro", "", 100, value)


def test_streamlit_displays_incomplete_books_without_writable_synthetic_ids(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(reading, "records", lambda _name: [
        {"titulo": "Antigo", "pagina_atual": "", "total_paginas": "inválido"},
        {"titulo": "Outro antigo", "pagina_atual": "-10"},
        {"id": "real-id", "titulo": "Atual", "pagina_atual": "12.0", "total_paginas": "100"},
    ])
    app = AppTest.from_string("from views.reading import render\nrender()").run()
    assert not app.exception
    assert [item.value for item in app.subheader] == ["Antigo", "Outro antigo", "Atual"]
    assert [item.key for item in app.number_input if item.label == "Página atual"] == ["page_real-id"]
