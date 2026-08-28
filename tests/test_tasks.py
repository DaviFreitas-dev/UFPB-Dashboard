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


def test_set_completed_changes_state_and_awards_xp_once(monkeypatch):
    rows = [{"id": "task-1", "status": "Pendente"}]
    updates, awards = [], []
    monkeypatch.setattr(tasks, "records", lambda _name: rows)
    monkeypatch.setattr(
        tasks,
        "update_record",
        lambda name, item_id, values: updates.append(values) or True,
    )
    monkeypatch.setattr(tasks, "award_xp_once", lambda *args: awards.append(args))

    record, changed = tasks.set_completed("task-1", True)

    assert changed is True
    assert record["status"] == "Concluída"
    assert updates == [{"status": "Concluída"}]
    assert awards == [("task:task-1", 15, "tarefa", "Tarefa concluída")]


def test_set_completed_replay_does_not_write_or_award(monkeypatch):
    monkeypatch.setattr(
        tasks,
        "records",
        lambda _name: [{"id": "task-1", "status": "Concluída"}],
    )
    monkeypatch.setattr(
        tasks,
        "update_record",
        lambda *_args: pytest.fail("must not write"),
    )
    monkeypatch.setattr(
        tasks,
        "award_xp_once",
        lambda *_args: pytest.fail("must not award"),
    )

    record, changed = tasks.set_completed("task-1", True)

    assert changed is False
    assert record["status"] == "Concluída"


def test_set_completed_reopens_without_awarding_xp(monkeypatch):
    updates = []
    monkeypatch.setattr(
        tasks,
        "records",
        lambda _name: [{"id": "task-1", "status": "Concluída"}],
    )
    monkeypatch.setattr(
        tasks,
        "update_record",
        lambda name, item_id, values: updates.append((name, item_id, values))
        or True,
    )
    monkeypatch.setattr(
        tasks,
        "award_xp_once",
        lambda *_args: pytest.fail("reopening must not award XP"),
    )

    record, changed = tasks.set_completed("task-1", False)

    assert changed is True
    assert record["status"] == "Pendente"
    assert updates == [("Tarefas", "task-1", {"status": "Pendente"})]


@pytest.mark.parametrize("item_id", ["task-1", "None", ""])
def test_set_completed_returns_absent_when_id_is_not_persisted(
    monkeypatch,
    item_id,
):
    monkeypatch.setattr(tasks, "records", lambda _name: [{"status": "Pendente"}])
    monkeypatch.setattr(
        tasks,
        "update_record",
        lambda *_args: pytest.fail("legacy rows without IDs are not mutable"),
    )

    assert tasks.set_completed(item_id, True) == (None, False)


@pytest.mark.parametrize("item_id", ["None", ""])
def test_remove_never_targets_a_legacy_row_without_id(monkeypatch, item_id):
    monkeypatch.setattr(tasks, "records", lambda _name: [{"status": "Pendente"}])
    monkeypatch.setattr(
        tasks,
        "delete_record",
        lambda *_args: pytest.fail("legacy rows without IDs are not mutable"),
    )

    assert tasks.remove(item_id) is False
