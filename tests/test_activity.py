from contextlib import contextmanager
from datetime import date

import pytest

from modules import activity


TARGET = date(2026, 8, 25)


def _unlocked():
    @contextmanager
    def lock():
        yield

    return lock


def test_completed_semantic_replay_recognizes_original_case_legacy_xp_key(
    monkeypatch,
):
    existing = {
        "id": "old-id",
        "data": "2026-08-25",
        "tipo": "Corrida",
        "feito": "Sim",
    }

    def records(name):
        if name == "Atividade":
            return [existing]
        assert name == "XPEventos"
        return [{"event_key": "activity:2026-08-25:Corrida"}]

    monkeypatch.setattr(activity, "records", records)
    monkeypatch.setattr(activity, "xp_write_lock", _unlocked(), raising=False)
    monkeypatch.setattr(
        activity,
        "append_record",
        lambda *_args, **_kwargs: pytest.fail("must not append"),
    )
    monkeypatch.setattr(
        activity,
        "award_xp_once",
        lambda *_args: pytest.fail("legacy XP must be recognized"),
    )

    record, created, changed = activity.add(
        "  corrida  ",
        TARGET,
        item_id="new-id",
    )

    assert record == existing
    assert (created, changed) == (False, False)


def test_completed_semantic_replay_recovers_missing_xp(monkeypatch):
    existing = {
        "id": "old-id",
        "data": "2026-08-25",
        "tipo": "Corrida",
        "feito": "Sim",
    }
    awards = []
    monkeypatch.setattr(
        activity,
        "records",
        lambda name: [existing] if name == "Atividade" else [],
    )
    monkeypatch.setattr(activity, "xp_write_lock", _unlocked(), raising=False)
    monkeypatch.setattr(activity, "award_xp_once", lambda *args: awards.append(args))

    record, created, changed = activity.add(
        "CORRIDA",
        TARGET,
        item_id="new-id",
    )

    assert record == existing
    assert (created, changed) == (False, False)
    assert awards == [
        (
            "activity:2026-08-25:corrida",
            20,
            "atividade",
            "Atividade física registrada",
        )
    ]


def test_pending_semantic_record_is_completed_without_duplicate(monkeypatch):
    existing = {
        "id": "  legacy-id  ",
        "data": "2026-08-25",
        "tipo": "Treino",
        "feito": "Não",
    }
    updates = []
    awards = []
    monkeypatch.setattr(
        activity,
        "records",
        lambda name: [existing] if name == "Atividade" else [],
    )
    monkeypatch.setattr(activity, "xp_write_lock", _unlocked(), raising=False)
    monkeypatch.setattr(
        activity,
        "update_record",
        lambda *args: updates.append(args) or True,
    )
    monkeypatch.setattr(
        activity,
        "append_record",
        lambda *_args, **_kwargs: pytest.fail("must not append"),
    )
    monkeypatch.setattr(activity, "award_xp_once", lambda *args: awards.append(args))

    record, created, changed = activity.add(
        " treino ",
        TARGET,
        item_id="new-id",
    )

    assert record == {**existing, "feito": "Sim"}
    assert (created, changed) == (False, True)
    assert updates == [("Atividade", "  legacy-id  ", {"feito": "Sim"})]
    assert awards[0][0] == "activity:2026-08-25:treino"


def test_pending_semantic_record_without_id_fails_without_positional_write(
    monkeypatch,
):
    monkeypatch.setattr(
        activity,
        "records",
        lambda _name: [
            {
                "data": "2026-08-25",
                "tipo": "Treino",
                "feito": "Não",
            }
        ],
    )
    monkeypatch.setattr(
        activity,
        "update_record",
        lambda *_args: pytest.fail("id-less rows are not mutable"),
    )
    monkeypatch.setattr(
        activity,
        "append_record",
        lambda *_args, **_kwargs: pytest.fail("must not duplicate"),
    )
    monkeypatch.setattr(
        activity,
        "award_xp_once",
        lambda *_args: pytest.fail("incomplete activity must not award XP"),
    )

    with pytest.raises(activity.ActivityIdConflict):
        activity.add("Treino", TARGET, item_id="new-id")


def test_reused_stable_id_with_different_content_conflicts(monkeypatch):
    monkeypatch.setattr(
        activity,
        "records",
        lambda _name: [
            {
                "id": "same-id",
                "data": "2026-08-24",
                "tipo": "Corrida",
                "feito": "Sim",
            }
        ],
    )

    with pytest.raises(activity.ActivityIdConflict):
        activity.add("Corrida", TARGET, item_id="same-id")


def test_create_trims_allowed_type_uses_raw_and_holds_xp_lock(monkeypatch):
    events = []
    locked = False

    @contextmanager
    def tracked_lock():
        nonlocal locked
        locked = True
        events.append("lock-enter")
        try:
            yield
        finally:
            events.append("lock-exit")
            locked = False

    def records(name):
        if name == "Atividade":
            return []
        assert name == "XPEventos"
        assert locked
        events.append("xp-lookup")
        return []

    monkeypatch.setattr(activity, "records", records)
    monkeypatch.setattr(activity, "xp_write_lock", tracked_lock, raising=False)
    monkeypatch.setattr(
        activity,
        "append_record",
        lambda *args, **kwargs: events.append(("append", args, kwargs)),
    )

    def award(*args):
        assert locked
        events.append(("award", args))

    monkeypatch.setattr(activity, "award_xp_once", award)

    record, created, changed = activity.add(
        "  Outro  ",
        TARGET,
        item_id="stable-id",
    )

    assert record == {
        "id": "stable-id",
        "data": "2026-08-25",
        "tipo": "Outro",
        "feito": "Sim",
    }
    assert (created, changed) == (True, True)
    assert events == [
        (
            "append",
            ("Atividade", ["stable-id", "2026-08-25", "Outro", "Sim"]),
            {"value_input_option": "RAW"},
        ),
        "lock-enter",
        "xp-lookup",
        (
            "award",
            (
                "activity:2026-08-25:outro",
                20,
                "atividade",
                "Atividade física registrada",
            ),
        ),
        "lock-exit",
    ]


@pytest.mark.parametrize(
    "invalid_type",
    ["", "   ", "Natação", None],
)
def test_add_rejects_unknown_activity_type_before_read(monkeypatch, invalid_type):
    monkeypatch.setattr(
        activity,
        "records",
        lambda _name: pytest.fail("invalid data must not read storage"),
    )

    with pytest.raises(ValueError):
        activity.add(invalid_type, TARGET, item_id="stable-id")


def test_retry_after_principal_write_recovers_xp_without_duplicate(monkeypatch):
    stored = []
    append_count = 0
    award_count = 0

    def records(name):
        return [dict(row) for row in stored] if name == "Atividade" else []

    def append(_name, values, value_input_option):
        nonlocal append_count
        assert value_input_option == "RAW"
        append_count += 1
        stored.append(dict(zip(("id", "data", "tipo", "feito"), values)))

    def award(*_args):
        nonlocal award_count
        award_count += 1
        if award_count == 1:
            raise RuntimeError("XP unavailable")

    monkeypatch.setattr(activity, "records", records)
    monkeypatch.setattr(activity, "append_record", append)
    monkeypatch.setattr(activity, "xp_write_lock", _unlocked(), raising=False)
    monkeypatch.setattr(activity, "award_xp_once", award)

    with pytest.raises(RuntimeError, match="XP unavailable"):
        activity.add("Caminhada", TARGET, item_id="stable-id")

    result = activity.add("caminhada", TARGET, item_id="stable-id")

    assert result == (stored[0], False, False)
    assert append_count == 1
    assert award_count == 2


def test_streamlit_wrapper_keeps_optional_date_and_id(monkeypatch):
    monkeypatch.setattr(activity, "records", lambda _name: [])
    monkeypatch.setattr(activity, "new_id", lambda: "streamlit-id")
    monkeypatch.setattr(activity, "append_record", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(activity, "xp_write_lock", _unlocked(), raising=False)
    monkeypatch.setattr(activity, "award_xp_once", lambda *_args: None)
    monkeypatch.setattr(activity, "date", type("FakeDate", (), {"today": staticmethod(lambda: TARGET)}))

    record, created, changed = activity.add("Treino")

    assert record["id"] == "streamlit-id"
    assert record["data"] == "2026-08-25"
    assert (created, changed) == (True, True)


def test_streamlit_displays_completed_legacy_activity_without_type(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(activity, "records", lambda _name: [
        {"data": str(date.today()), "feito": "Sim"},
    ])
    app = AppTest.from_string("from views.activity import render\nrender()").run()
    assert not app.exception
    assert app.success[0].value == "Atividade registrada"
