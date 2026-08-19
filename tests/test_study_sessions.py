import pytest

from modules import study_sessions


def test_invalid_question_totals_fail_before_any_write(monkeypatch):
    writes = []
    monkeypatch.setattr(
        study_sessions,
        "append_record",
        lambda *args, **kwargs: writes.append((args, kwargs)),
    )

    with pytest.raises(ValueError, match=r"Acertos \+ erros"):
        study_sessions.record_study_session(
            {"Física": 2},
            "Física",
            "Cinemática",
            total=10,
            correct=7,
            wrong=4,
        )

    assert writes == []


def test_negative_question_values_fail_before_any_write(monkeypatch):
    writes = []
    monkeypatch.setattr(
        study_sessions,
        "append_record",
        lambda *args, **kwargs: writes.append((args, kwargs)),
    )

    with pytest.raises(ValueError, match="não podem ser negativos"):
        study_sessions.record_study_session(
            {"Física": 2},
            "Física",
            "Cinemática",
            total=-1,
            correct=0,
            wrong=0,
        )

    assert writes == []
