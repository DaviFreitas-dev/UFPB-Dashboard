from copy import deepcopy

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


def test_mission_completion_is_atomic_and_idempotent(monkeypatch):
    tables = {
        "Ciclo": [{"disciplina": "Física", "restantes": 3}],
        "Usuario": [{"chave": "xp", "valor": "100"}],
        "Historico": [],
        "SessoesEstudo": [],
        "Questoes": [],
        "Revisoes": [],
        "Erros": [],
        "XPEventos": [],
    }
    writes = []

    monkeypatch.setattr(
        study_sessions,
        "records",
        lambda name: deepcopy(tables[name]),
    )

    def write_values_batch(updates):
        writes.append(deepcopy(updates))
        xp_update = next(
            update for update in updates if update["sheet"] == "XPEventos"
        )
        tables["XPEventos"] = [
            {
                "id": row[0],
                "event_key": row[1],
                "data": row[2],
                "fonte": row[3],
                "descricao": row[4],
                "xp": row[5],
            }
            for row in xp_update["values"]
        ]
        session_update = next(
            update for update in updates if update["sheet"] == "SessoesEstudo"
        )
        session_row = session_update["values"][0]
        tables["SessoesEstudo"] = [
            {
                "id": session_row[0],
                "horas": session_row[4],
                "questoes": session_row[5],
                "acertos": session_row[6],
            }
        ]

    monkeypatch.setattr(
        study_sessions,
        "write_values_batch",
        write_values_batch,
    )

    first = study_sessions.complete_study_session(
        "session-1",
        {"Física": 2},
        "Física",
        "Cinemática",
        total=10,
        correct=8,
        wrong=2,
        note="Rever gráficos",
    )
    second = study_sessions.complete_study_session(
        "session-1",
        {"Física": 2},
        "Física",
        "Cinemática",
        total=10,
        correct=8,
        wrong=2,
        note="Rever gráficos",
    )

    assert len(writes) == 1
    assert first == {
        "id": "session-1",
        "hours": 2,
        "base_xp": 200,
        "question_xp": 35,
        "questions": 10,
        "correct": 8,
        "already_completed": False,
    }
    assert second == {**first, "already_completed": True}
    assert len(tables["XPEventos"]) == 2
    ranges = {
        (update["sheet"], update["range"]): update["values"]
        for update in writes[0]
    }
    assert ranges[("Ciclo", "B2")] == [[1]]
    assert ranges[("Usuario", "B2")] == [["335"]]
    assert ranges[("SessoesEstudo", "A2:I2")][0][0] == "session-1"
    assert len(ranges[("Revisoes", "A2:G4")]) == 3
    assert ranges[("Erros", "A2:G2")][0][4] == 2


def test_mission_completion_rejects_a_stale_cycle(monkeypatch):
    tables = {
        "Ciclo": [{"disciplina": "Física", "restantes": 1}],
        "Usuario": [],
        "Historico": [],
        "SessoesEstudo": [],
        "Questoes": [],
        "Revisoes": [],
        "Erros": [],
        "XPEventos": [],
    }
    monkeypatch.setattr(
        study_sessions,
        "records",
        lambda name: deepcopy(tables[name]),
    )
    monkeypatch.setattr(
        study_sessions,
        "write_values_batch",
        lambda _updated: (_ for _ in ()).throw(AssertionError("unexpected write")),
    )

    with pytest.raises(study_sessions.MissionConsistencyError, match="mudou"):
        study_sessions.complete_study_session(
            "session-2",
            {"Física": 2},
            "Física",
            "Cinemática",
            total=0,
            correct=0,
            wrong=0,
        )
