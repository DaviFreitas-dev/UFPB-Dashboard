from datetime import date

import pytest

from modules import habits


TARGET = date(2026, 8, 25)
CONFIG_ID = "config-1"
LOG_ID = "0482cb36-ff7f-5c83-8f8d-78acdf6e025f"


def test_create_rejects_reused_identity_with_different_name(monkeypatch):
    rows = [{"id": CONFIG_ID, "nome": "Ler", "ativo": "Sim"}]
    appended = []
    monkeypatch.setattr(habits, "records", lambda _name: rows)
    monkeypatch.setattr(habits, "append_record", lambda *a, **kw: appended.append(a))

    with pytest.raises(ValueError, match="outro conteúdo"):
        habits.add("Caminhar", item_id=CONFIG_ID)
    assert appended == []


@pytest.mark.parametrize("completed", [False, True])
def test_legacy_noop_never_confirms_an_unstored_log_id(monkeypatch, completed):
    config = {"id": CONFIG_ID, "nome": "Ler", "ativo": "Sim"}
    log = {"data": str(TARGET), "habito": "Ler", "feito": "Sim" if completed else "Não"}
    writes = []
    monkeypatch.setattr(habits, "records", lambda name: [config] if name == "HabitosConfig" else [log])

    def write_batch(updates):
        writes.extend(updates)
        log.update(dict(zip(("id", "data", "habito", "feito"), updates[0]["values"][0])))

    monkeypatch.setattr(habits, "write_values_batch", write_batch)
    monkeypatch.setattr(habits, "award_xp_once", lambda *args: 0)
    confirmed, changed = habits.set_completed(CONFIG_ID, TARGET, completed)
    assert confirmed["id"] == log.get("id")
    assert changed is completed
    assert len(writes) == int(completed)


def test_records_for_date_is_pure_and_projects_a_missing_log(monkeypatch):
    tables = {
        "HabitosConfig": [
            {"id": CONFIG_ID, "nome": "Ler", "ativo": "Sim"},
            {"nome": "Alongar", "ativo": "Sim"},
            {"id": "archived", "nome": "Arquivado", "ativo": "Não"},
        ],
        "Habitos": [
            {
                "id": "old-log",
                "data": "2026-08-24",
                "habito": "Ler",
                "feito": "Sim",
            }
        ],
    }
    monkeypatch.setattr(habits, "records", lambda name: tables[name])
    monkeypatch.setattr(
        habits,
        "append_record",
        lambda *_args, **_kwargs: pytest.fail("a read must not append"),
    )
    monkeypatch.setattr(
        habits,
        "update_record",
        lambda *_args, **_kwargs: pytest.fail("a read must not update"),
    )

    result = habits.records_for_date(TARGET)

    assert result == [
        {
            "id": None,
            "config_id": CONFIG_ID,
            "data": "2026-08-25",
            "habito": "Ler",
            "feito": "Não",
        },
        {
            "id": None,
            "config_id": "",
            "data": "2026-08-25",
            "habito": "Alongar",
            "feito": "Não",
        },
    ]


def test_today_is_a_compatibility_wrapper(monkeypatch):
    calls = []
    monkeypatch.setattr(
        habits,
        "records_for_date",
        lambda target: calls.append(target) or [{"habito": "Ler"}],
        raising=False,
    )

    assert habits.today() == [{"habito": "Ler"}]
    assert calls == [date.today()]


def test_add_creates_with_the_supplied_id_and_replays_an_active_name(monkeypatch):
    rows = []
    appends = []
    monkeypatch.setattr(habits, "records", lambda _name: list(rows))

    def append_record(name, values, **kwargs):
        appends.append((name, values, kwargs))
        rows.append(dict(zip(("id", "nome", "ativo"), values)))

    monkeypatch.setattr(habits, "append_record", append_record)

    created = habits.add("  Ler   vinte páginas  ", item_id=CONFIG_ID)
    replay = habits.add("ler vinte PÁGINAS", item_id="ignored")

    assert created == (
        {"id": CONFIG_ID, "nome": "Ler vinte páginas", "ativo": "Sim"},
        True,
        False,
    )
    assert replay == (rows[0], False, False)
    assert appends == [
        (
            "HabitosConfig",
            [CONFIG_ID, "Ler vinte páginas", "Sim"],
            {"value_input_option": "RAW"},
        )
    ]


def test_add_reactivates_a_normalized_archived_name(monkeypatch):
    archived = {"id": "legacy-id", "nome": "  LER   vinte PÁGINAS ", "ativo": "Não"}
    updates = []
    monkeypatch.setattr(habits, "records", lambda _name: [archived])
    monkeypatch.setattr(
        habits,
        "append_record",
        lambda *_args, **_kwargs: pytest.fail("reactivation must not append"),
    )

    def update_record(name, item_id, values):
        updates.append((name, item_id, values))
        archived.update(values)
        return True

    monkeypatch.setattr(habits, "update_record", update_record)

    record, created, reactivated = habits.add("ler vinte páginas")

    assert record == {**archived, "ativo": "Sim"}
    assert (created, reactivated) == (False, True)
    assert updates == [("HabitosConfig", "legacy-id", {"ativo": "Sim"})]


def test_set_active_archives_without_touching_history_and_handles_missing(monkeypatch):
    config = {"id": CONFIG_ID, "nome": "Ler", "ativo": "Sim"}
    updates = []
    monkeypatch.setattr(habits, "records", lambda name: [config] if name == "HabitosConfig" else pytest.fail("history must not be read"))

    def update_record(name, item_id, values):
        updates.append((name, item_id, values))
        config.update(values)
        return True

    monkeypatch.setattr(habits, "update_record", update_record)

    first = habits.set_active(CONFIG_ID, False)
    replay = habits.set_active(CONFIG_ID, False)
    missing = habits.set_active("missing", False)

    assert first == ({**config, "ativo": "Não"}, True)
    assert replay == ({**config, "ativo": "Não"}, False)
    assert missing == (None, False)
    assert updates == [("HabitosConfig", CONFIG_ID, {"ativo": "Não"})]


def test_set_completed_creates_deterministic_log_and_recovers_xp_on_replay(monkeypatch):
    configs = [{"id": CONFIG_ID, "nome": "Ler", "ativo": "Sim"}]
    logs = []
    appends = []
    awards = []
    monkeypatch.setattr(
        habits,
        "records",
        lambda name: list(configs if name == "HabitosConfig" else logs),
    )

    def append_record(name, values, **kwargs):
        appends.append((name, values, kwargs))
        logs.append(dict(zip(("id", "data", "habito", "feito"), values)))

    monkeypatch.setattr(habits, "append_record", append_record)
    monkeypatch.setattr(
        habits,
        "award_xp_once",
        lambda *args: awards.append(args) or (10 if len(awards) == 1 else 0),
    )

    first = habits.set_completed(CONFIG_ID, TARGET, True)
    replay = habits.set_completed(CONFIG_ID, TARGET, True)

    expected = {
        "id": LOG_ID,
        "config_id": CONFIG_ID,
        "data": "2026-08-25",
        "habito": "Ler",
        "feito": "Sim",
    }
    assert first == (expected, True)
    assert replay == (expected, False)
    assert appends == [
        (
            "Habitos",
            [LOG_ID, "2026-08-25", "Ler", "Sim"],
            {"value_input_option": "RAW"},
        )
    ]
    assert awards == [
        (f"habit:{LOG_ID}", 10, "habito", "Hábito concluído"),
        (f"habit:{LOG_ID}", 10, "habito", "Hábito concluído"),
    ]


def test_set_completed_matches_a_legacy_log_by_normalized_name_and_date(monkeypatch):
    config = {"id": CONFIG_ID, "nome": "Ler vinte páginas", "ativo": "Sim"}
    legacy = {
        "id": "legacy-log",
        "data": "2026-08-25",
        "habito": "  LER   vinte PÁGINAS ",
        "feito": "Não",
    }
    updates = []
    monkeypatch.setattr(
        habits,
        "records",
        lambda name: [config] if name == "HabitosConfig" else [legacy],
    )
    monkeypatch.setattr(
        habits,
        "append_record",
        lambda *_args, **_kwargs: pytest.fail("compatible legacy log must not duplicate"),
    )

    def update_record(name, item_id, values):
        updates.append((name, item_id, values))
        legacy.update(values)
        return True

    monkeypatch.setattr(habits, "update_record", update_record)
    monkeypatch.setattr(habits, "award_xp_once", lambda *_args: 10)

    record, changed = habits.set_completed(CONFIG_ID, TARGET, True)

    assert changed is True
    assert record["id"] == "legacy-log"
    assert record["config_id"] == CONFIG_ID
    assert record["feito"] == "Sim"
    assert updates == [("Habitos", "legacy-log", {"feito": "Sim"})]


def test_unchecking_a_missing_log_is_confirmed_without_writes(monkeypatch):
    monkeypatch.setattr(
        habits,
        "records",
        lambda name: [{"id": CONFIG_ID, "nome": "Ler", "ativo": "Sim"}]
        if name == "HabitosConfig"
        else [],
    )
    monkeypatch.setattr(
        habits,
        "append_record",
        lambda *_args, **_kwargs: pytest.fail("false state must not create"),
    )
    monkeypatch.setattr(
        habits,
        "update_record",
        lambda *_args, **_kwargs: pytest.fail("false state must not update"),
    )
    monkeypatch.setattr(
        habits,
        "award_xp_once",
        lambda *_args: pytest.fail("false state must not award XP"),
    )

    record, changed = habits.set_completed(CONFIG_ID, TARGET, False)

    assert changed is False
    assert record == {
        "id": None,
        "config_id": CONFIG_ID,
        "data": "2026-08-25",
        "habito": "Ler",
        "feito": "Não",
    }


def test_set_completed_returns_missing_for_an_unknown_or_legacy_config(monkeypatch):
    monkeypatch.setattr(
        habits,
        "records",
        lambda name: [{"nome": "Legado", "ativo": "Sim"}]
        if name == "HabitosConfig"
        else [],
    )

    assert habits.set_completed("missing", TARGET, True) == (None, False)
    assert habits.set_completed("", TARGET, True) == (None, False)


def test_partial_xp_failure_retries_the_same_event_without_a_second_log_write(monkeypatch):
    config = {"id": CONFIG_ID, "nome": "Ler", "ativo": "Sim"}
    logs = []
    writes = []
    attempts = []
    monkeypatch.setattr(
        habits,
        "records",
        lambda name: [config] if name == "HabitosConfig" else list(logs),
    )

    def append_record(_name, values, **_kwargs):
        writes.append(values)
        logs.append(dict(zip(("id", "data", "habito", "feito"), values)))

    def award(event_key, *_args):
        attempts.append(event_key)
        if len(attempts) == 1:
            raise RuntimeError("xp unavailable")
        return 10

    monkeypatch.setattr(habits, "append_record", append_record)
    monkeypatch.setattr(habits, "award_xp_once", award)

    with pytest.raises(RuntimeError, match="xp unavailable"):
        habits.set_completed(CONFIG_ID, TARGET, True)
    record, changed = habits.set_completed(CONFIG_ID, TARGET, True)

    assert record["id"] == LOG_ID
    assert changed is False
    assert len(writes) == 1
    assert attempts == [f"habit:{LOG_ID}", f"habit:{LOG_ID}"]
