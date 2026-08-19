from modules import gamification


def test_award_xp_once_deduplicates_event_key(monkeypatch):
    events = []
    history = []
    state = {"xp": 100}

    monkeypatch.setattr(
        gamification,
        "records",
        lambda name: list(events) if name == "XPEventos" else [],
    )

    def append_record(name, values):
        assert name == "XPEventos"
        events.append({"event_key": values[1], "xp": values[5]})

    monkeypatch.setattr(gamification, "append_record", append_record)
    monkeypatch.setattr(gamification, "new_id", lambda: "event-1")
    monkeypatch.setattr(gamification, "get_xp", lambda: state["xp"])
    monkeypatch.setattr(
        gamification,
        "set_xp",
        lambda value: state.__setitem__("xp", value),
    )
    monkeypatch.setattr(
        gamification,
        "add_history",
        lambda hours, xp: history.append((hours, xp)),
    )

    first = gamification.award_xp_once(
        "task:abc",
        15,
        "tarefa",
        "Tarefa concluída",
    )
    second = gamification.award_xp_once(
        "task:abc",
        15,
        "tarefa",
        "Tarefa concluída",
    )

    assert first == 15
    assert second == 0
    assert state["xp"] == 115
    assert events == [{"event_key": "task:abc", "xp": 15}]
    assert history == [(0, 15)]


def test_non_positive_award_has_no_side_effects(monkeypatch):
    monkeypatch.setattr(
        gamification,
        "records",
        lambda _name: (_ for _ in ()).throw(AssertionError("unexpected read")),
    )

    assert gamification.award_xp_once("noop", 0, "teste", "Nada") == 0
