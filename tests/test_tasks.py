from datetime import date

import pytest

from modules import tasks


def test_add_uses_stable_id_and_returns_created_record(monkeypatch):
    appended = []
    monkeypatch.setattr(tasks, "records", lambda _name: [])
    monkeypatch.setattr(
        tasks,
        "append_record",
        lambda name, values, value_input_option="USER_ENTERED": appended.append(
            (name, values, value_input_option)
        ),
    )

    record, created = tasks.add(
        "Revisar matemática",
        "Estudo",
        date(2026, 8, 23),
        item_id="task-stable-id",
    )

    assert created is True
    assert record["id"] == "task-stable-id"
    assert appended == [
        (
            "Tarefas",
            ["task-stable-id", "2026-08-23", "Revisar matemática", "Estudo", "Pendente"],
            "RAW",
        )
    ]


def test_add_returns_existing_record_for_identical_retry(monkeypatch):
    existing = {
        "id": "task-stable-id",
        "data": "2026-08-23",
        "tarefa": "Revisar matemática",
        "categoria": "Estudo",
        "status": "Concluída",
    }
    monkeypatch.setattr(tasks, "records", lambda _name: [existing])
    monkeypatch.setattr(
        tasks,
        "append_record",
        lambda _name, _values: pytest.fail("retry must not append"),
    )

    assert tasks.add(
        "Revisar matemática",
        "Estudo",
        date(2026, 8, 23),
        item_id="task-stable-id",
    ) == (existing, False)


def test_add_rejects_same_id_with_different_content(monkeypatch):
    monkeypatch.setattr(
        tasks,
        "records",
        lambda _name: [{
            "id": "task-stable-id",
            "data": "2026-08-23",
            "tarefa": "Conteúdo anterior",
            "categoria": "Estudo",
            "status": "Pendente",
        }],
    )

    with pytest.raises(tasks.TaskIdConflict):
        tasks.add(
            "Novo conteúdo",
            "Estudo",
            date(2026, 8, 23),
            item_id="task-stable-id",
        )
