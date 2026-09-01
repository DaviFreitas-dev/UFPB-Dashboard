from datetime import date

import pytest

from modules import routine


def test_add_uses_stable_id_normalizes_fields_and_persists_raw(monkeypatch):
    appended = []
    monkeypatch.setattr(routine, "records", lambda _name: [])
    monkeypatch.setattr(
        routine,
        "append_record",
        lambda name, values, value_input_option="USER_ENTERED": appended.append(
            (name, values, value_input_option)
        ),
    )

    record, created = routine.add(
        "  001  ",
        "08:30",
        date(2026, 8, 25),
        item_id="routine-1",
    )

    assert created is True
    assert record == {
        "id": "routine-1",
        "data": "2026-08-25",
        "hora": "08:30",
        "atividade": "001",
        "status": "Pendente",
    }
    assert appended == [
        (
            "Rotina",
            ["routine-1", "2026-08-25", "08:30", "001", "Pendente"],
            "RAW",
        )
    ]


def test_add_replays_same_uuid_without_second_append(monkeypatch):
    existing = {
        "id": "routine-1",
        "data": "2026-08-25",
        "hora": "08:30",
        "atividade": "Dentista",
        "status": "Concluída",
    }
    monkeypatch.setattr(routine, "records", lambda _name: [existing])
    monkeypatch.setattr(
        routine,
        "append_record",
        lambda *_args, **_kwargs: pytest.fail("must not append"),
    )

    assert routine.add(
        "Dentista",
        "08:30",
        date(2026, 8, 25),
        item_id="routine-1",
    ) == (existing, False)


@pytest.mark.parametrize(
    ("activity", "time_text", "target_date"),
    [
        ("", "08:30", date(2026, 8, 25)),
        ("x" * 161, "08:30", date(2026, 8, 25)),
        ("Dentista", "8:30", date(2026, 8, 25)),
        ("Dentista", "24:00", date(2026, 8, 25)),
        ("Dentista", "08:60", date(2026, 8, 25)),
    ],
)
def test_add_rejects_invalid_immutable_fields_before_read(
    monkeypatch,
    activity,
    time_text,
    target_date,
):
    monkeypatch.setattr(
        routine,
        "records",
        lambda _name: pytest.fail("invalid input must not read storage"),
    )

    with pytest.raises(ValueError):
        routine.add(activity, time_text, target_date, item_id="routine-1")


def test_add_rejects_reused_id_with_different_immutable_content(monkeypatch):
    monkeypatch.setattr(
        routine,
        "records",
        lambda _name: [
            {
                "id": "routine-1",
                "data": "2026-08-25",
                "hora": "08:30",
                "atividade": "Dentista",
                "status": "Pendente",
            }
        ],
    )

    with pytest.raises(routine.RoutineIdConflict):
        routine.add(
            "Mercado",
            "08:30",
            date(2026, 8, 25),
            item_id="routine-1",
        )


def test_set_completed_changes_state_and_awards_xp_once(monkeypatch):
    updates, awards = [], []
    monkeypatch.setattr(
        routine,
        "records",
        lambda _name: [{"id": "routine-1", "status": "Pendente"}],
    )
    monkeypatch.setattr(
        routine,
        "update_record",
        lambda name, item_id, values: updates.append((name, item_id, values))
        or True,
    )
    monkeypatch.setattr(
        routine,
        "award_xp_once",
        lambda *args: awards.append(args),
    )

    record, changed = routine.set_completed("routine-1", True)

    assert changed is True
    assert record["status"] == "Concluída"
    assert updates == [
        ("Rotina", "routine-1", {"status": "Concluída"})
    ]
    assert awards == [
        (
            "routine:routine-1",
            10,
            "rotina",
            "Compromisso do dia concluído",
        )
    ]


@pytest.mark.parametrize(
    ("current_status", "completed", "expected_status"),
    [
        ("Pendente", False, "Pendente"),
    ],
)
def test_set_completed_replay_does_not_write_or_award(
    monkeypatch,
    current_status,
    completed,
    expected_status,
):
    monkeypatch.setattr(
        routine,
        "records",
        lambda _name: [{"id": "routine-1", "status": current_status}],
    )
    monkeypatch.setattr(
        routine,
        "update_record",
        lambda *_args: pytest.fail("replay must not write"),
    )
    monkeypatch.setattr(
        routine,
        "award_xp_once",
        lambda *_args: pytest.fail("replay must not award XP"),
    )

    record, changed = routine.set_completed("routine-1", completed)

    assert changed is False
    assert record["status"] == expected_status


def test_completed_replay_retries_idempotent_xp_without_rewriting(monkeypatch):
    awards = []
    monkeypatch.setattr(
        routine,
        "records",
        lambda _name: [{"id": "routine-1", "status": "Concluída"}],
    )
    monkeypatch.setattr(
        routine,
        "update_record",
        lambda *_args: pytest.fail("completed replay must not rewrite status"),
    )
    monkeypatch.setattr(
        routine,
        "award_xp_once",
        lambda *args: awards.append(args),
    )

    record, changed = routine.set_completed("routine-1", True)

    assert changed is False
    assert record["status"] == "Concluída"
    assert awards == [
        (
            "routine:routine-1",
            10,
            "rotina",
            "Compromisso do dia concluído",
        )
    ]


def test_completed_retry_recovers_xp_after_first_award_failure(monkeypatch):
    row = {"id": "routine-1", "status": "Pendente"}
    updates, awards = [], []
    monkeypatch.setattr(routine, "records", lambda _name: [row])

    def update_record(name, item_id, values):
        updates.append((name, item_id, values))
        row.update(values)
        return True

    def award_xp_once(*args):
        awards.append(args)
        if len(awards) == 1:
            raise RuntimeError("xp temporarily unavailable")

    monkeypatch.setattr(routine, "update_record", update_record)
    monkeypatch.setattr(routine, "award_xp_once", award_xp_once)

    with pytest.raises(RuntimeError, match="temporarily unavailable"):
        routine.set_completed("routine-1", True)

    record, changed = routine.set_completed("routine-1", True)

    assert changed is False
    assert record["status"] == "Concluída"
    assert updates == [
        ("Rotina", "routine-1", {"status": "Concluída"})
    ]
    assert awards == [
        (
            "routine:routine-1",
            10,
            "rotina",
            "Compromisso do dia concluído",
        ),
        (
            "routine:routine-1",
            10,
            "rotina",
            "Compromisso do dia concluído",
        ),
    ]


def test_set_completed_reopens_without_awarding_xp(monkeypatch):
    updates = []
    monkeypatch.setattr(
        routine,
        "records",
        lambda _name: [{"id": "routine-1", "status": "Concluída"}],
    )
    monkeypatch.setattr(
        routine,
        "update_record",
        lambda name, item_id, values: updates.append((name, item_id, values))
        or True,
    )
    monkeypatch.setattr(
        routine,
        "award_xp_once",
        lambda *_args: pytest.fail("reopening must not award XP"),
    )

    record, changed = routine.set_completed("routine-1", False)

    assert changed is True
    assert record["status"] == "Pendente"
    assert updates == [("Rotina", "routine-1", {"status": "Pendente"})]


def test_set_completed_treats_legacy_completed_spelling_as_xp_replay(
    monkeypatch,
):
    awards = []
    monkeypatch.setattr(
        routine,
        "records",
        lambda _name: [{"id": "routine-1", "status": "Concluida"}],
    )
    monkeypatch.setattr(
        routine,
        "update_record",
        lambda *_args: pytest.fail("a completed legacy row must not be rewritten"),
    )
    monkeypatch.setattr(
        routine,
        "award_xp_once",
        lambda *args: awards.append(args),
    )

    record, changed = routine.set_completed("routine-1", True)

    assert changed is False
    assert record["status"] == "Concluída"
    assert awards == [
        (
            "routine:routine-1",
            10,
            "rotina",
            "Compromisso do dia concluído",
        )
    ]


@pytest.mark.parametrize("item_id", ["routine-1", "None", ""])
def test_set_completed_never_targets_legacy_rows_without_id(monkeypatch, item_id):
    monkeypatch.setattr(
        routine,
        "records",
        lambda _name: [{"status": "Pendente"}],
    )
    monkeypatch.setattr(
        routine,
        "update_record",
        lambda *_args: pytest.fail("legacy rows are not mutable"),
    )

    assert routine.set_completed(item_id, True) == (None, False)


def test_remove_is_idempotent_and_never_targets_legacy_rows(monkeypatch):
    rows = [{"id": "routine-1", "status": "Pendente"}]
    deletes = []
    monkeypatch.setattr(routine, "records", lambda _name: list(rows))

    def delete_record(name, item_id):
        deletes.append((name, item_id))
        rows.clear()
        return True

    monkeypatch.setattr(routine, "delete_record", delete_record)

    assert routine.remove("routine-1") is True
    assert routine.remove("routine-1") is False
    assert routine.remove("") is False
    assert deletes == [("Rotina", "routine-1")]
