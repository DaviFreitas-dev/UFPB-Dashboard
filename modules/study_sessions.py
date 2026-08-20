import hashlib
from datetime import date, timedelta

from modules.config import XP_POR_HORA
from modules.database import (
    records,
    write_values_batch,
)
from modules.gamification import XP_WRITE_LOCK


class MissionConsistencyError(RuntimeError):
    """Raised when a pending mission no longer matches the current cycle."""


_MISSION_WRITE_LOCK = XP_WRITE_LOCK


def _derived_id(session_id, suffix):
    value = f"{session_id}:{suffix}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()[:10]


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def question_xp(total, correct):
    total = int(total)
    correct = int(correct)

    if total <= 0:
        return 0

    accuracy = correct / total
    xp = min(total, 100)

    if total >= 10 and accuracy >= 0.80:
        xp += 25

    if total >= 20 and accuracy >= 0.90:
        xp += 25

    return xp


def complete_study_session(
    session_id,
    mission,
    primary_subject,
    topic,
    total,
    correct,
    wrong,
    note="",
):
    """Persist a completed mission as one serialized, idempotent batch."""
    with _MISSION_WRITE_LOCK:
        return _complete_study_session(
            session_id,
            mission,
            primary_subject,
            topic,
            total,
            correct,
            wrong,
            note,
        )


def _complete_study_session(
    session_id,
    mission,
    primary_subject,
    topic,
    total,
    correct,
    wrong,
    note="",
):
    session_id = str(session_id).strip()
    if not session_id:
        raise ValueError("A sessão precisa de um identificador.")

    total = int(total)
    correct = int(correct)
    wrong = int(wrong)
    if min(total, correct, wrong) < 0:
        raise ValueError("Os valores não podem ser negativos.")
    if correct + wrong != total:
        raise ValueError("Acertos + erros precisam ser iguais ao total.")

    normalized_mission = {}
    for subject, amount in mission.items():
        hours = int(amount)
        if not subject or hours <= 0:
            raise ValueError("A missão possui uma carga horária inválida.")
        normalized_mission[str(subject)] = hours

    hours = sum(normalized_mission.values())
    if hours <= 0:
        raise ValueError("A missão precisa ter ao menos uma hora.")
    if primary_subject not in normalized_mission:
        raise ValueError("A disciplina principal deve fazer parte da missão.")

    base_event_key = f"session:{session_id}:mission"
    question_event_key = f"session:{session_id}:questions"
    xp_events = records("XPEventos")
    existing_base_event = next(
        (
            row
            for row in xp_events
            if str(row.get("event_key")) == base_event_key
        ),
        None,
    )

    if existing_base_event:
        existing_session = next(
            (
                row
                for row in records("SessoesEstudo")
                if str(row.get("id")) == session_id
            ),
            None,
        )
        if existing_session is None:
            raise MissionConsistencyError(
                "A missão possui recompensa registrada, mas a sessão não foi "
                "encontrada. Revise o backup antes de tentar novamente."
            )
        existing_question_event = next(
            (
                row
                for row in xp_events
                if str(row.get("event_key")) == question_event_key
            ),
            None,
        )
        return {
            "id": session_id,
            "hours": _safe_int(existing_session.get("horas"), hours),
            "base_xp": _safe_int(existing_base_event.get("xp")),
            "question_xp": _safe_int(
                existing_question_event.get("xp")
                if existing_question_event
                else 0
            ),
            "questions": _safe_int(existing_session.get("questoes"), total),
            "correct": _safe_int(existing_session.get("acertos"), correct),
            "already_completed": True,
        }

    tables = {
        name: records(name)
        for name in (
            "Ciclo",
            "Usuario",
            "Historico",
            "SessoesEstudo",
            "Questoes",
            "Revisoes",
            "Erros",
        )
    }
    tables["XPEventos"] = xp_events

    updates = []
    remaining_subjects = set(normalized_mission)
    for row_number, row in enumerate(tables["Ciclo"], start=2):
        subject = str(row.get("disciplina", ""))
        if subject not in normalized_mission:
            continue
        remaining = _safe_int(row.get("restantes"))
        requested = normalized_mission[subject]
        if remaining < requested:
            raise MissionConsistencyError(
                f"O ciclo de {subject} mudou desde o sorteio. "
                "Cancele esta missão e sorteie outra."
            )
        updates.append(
            {
                "sheet": "Ciclo",
                "range": f"B{row_number}",
                "values": [[remaining - requested]],
            }
        )
        remaining_subjects.discard(subject)

    if remaining_subjects:
        subjects = ", ".join(sorted(remaining_subjects))
        raise MissionConsistencyError(
            f"As disciplinas não existem mais no ciclo: {subjects}."
        )

    bonus_xp = question_xp(total, correct)
    base_xp = hours * XP_POR_HORA
    total_xp = base_xp + bonus_xp

    xp_row = next(
        (
            row
            for row in tables["Usuario"]
            if str(row.get("chave")) == "xp"
        ),
        None,
    )
    if xp_row is None:
        user_row_number = len(tables["Usuario"]) + 2
        updates.append(
            {
                "sheet": "Usuario",
                "range": f"A{user_row_number}:B{user_row_number}",
                "values": [["xp", str(total_xp)]],
            }
        )
    else:
        current_xp = max(0, _safe_int(xp_row.get("valor")))
        user_row_number = tables["Usuario"].index(xp_row) + 2
        updates.append(
            {
                "sheet": "Usuario",
                "range": f"B{user_row_number}",
                "values": [[str(current_xp + total_xp)]],
            }
        )

    today = str(date.today())
    history_row = next(
        (
            row
            for row in tables["Historico"]
            if str(row.get("data")) == today
        ),
        None,
    )
    if history_row is None:
        history_row_number = len(tables["Historico"]) + 2
        history_values = [today, hours, total_xp]
    else:
        history_row_number = tables["Historico"].index(history_row) + 2
        history_values = [
            today,
            _safe_int(history_row.get("horas")) + hours,
            _safe_int(history_row.get("xp")) + total_xp,
        ]
    updates.append(
        {
            "sheet": "Historico",
            "range": f"A{history_row_number}:C{history_row_number}",
            "values": [history_values],
        }
    )

    topic_text = str(topic).strip() or "Revisão geral"
    note_text = str(note).strip()
    session_row_number = len(tables["SessoesEstudo"]) + 2
    updates.append(
        {
            "sheet": "SessoesEstudo",
            "range": f"A{session_row_number}:I{session_row_number}",
            "values": [
                [
                    session_id,
                    today,
                    primary_subject,
                    topic_text,
                    hours,
                    total,
                    correct,
                    wrong,
                    note_text,
                ]
            ],
        }
    )

    question_row_number = len(tables["Questoes"]) + 2
    updates.append(
        {
            "sheet": "Questoes",
            "range": f"A{question_row_number}:F{question_row_number}",
            "values": [
                [
                    _derived_id(session_id, "questions"),
                    today,
                    " | ".join(normalized_mission),
                    total,
                    correct,
                    wrong,
                ]
            ],
        }
    )

    review_values = []
    for subject in normalized_mission:
        for days in (1, 7, 30):
            review_values.append(
                [
                    _derived_id(session_id, f"review:{subject}:{days}"),
                    today,
                    str(date.today() + timedelta(days=days)),
                    subject,
                    topic_text,
                    "Pendente",
                    f"session:{session_id}:{subject}:{days}",
                ]
            )
    review_start = len(tables["Revisoes"]) + 2
    review_end = review_start + len(review_values) - 1
    updates.append(
        {
            "sheet": "Revisoes",
            "range": f"A{review_start}:G{review_end}",
            "values": review_values,
        }
    )

    if wrong > 0:
        error_row_number = len(tables["Erros"]) + 2
        updates.append(
            {
                "sheet": "Erros",
                "range": f"A{error_row_number}:G{error_row_number}",
                "values": [
                    [
                        _derived_id(session_id, "error"),
                        today,
                        primary_subject,
                        topic_text,
                        wrong,
                        note_text,
                        "Aberto",
                    ]
                ],
            }
        )

    xp_event_values = [
        [
            _derived_id(session_id, "xp:mission"),
            base_event_key,
            today,
            "missao",
            "Missão de estudo concluída",
            base_xp,
        ]
    ]
    if bonus_xp > 0:
        xp_event_values.append(
            [
                _derived_id(session_id, "xp:questions"),
                question_event_key,
                today,
                "questoes",
                "Questões e desempenho da sessão",
                bonus_xp,
            ]
        )
    xp_event_start = len(tables["XPEventos"]) + 2
    xp_event_end = xp_event_start + len(xp_event_values) - 1
    updates.append(
        {
            "sheet": "XPEventos",
            "range": f"A{xp_event_start}:F{xp_event_end}",
            "values": xp_event_values,
        }
    )

    write_values_batch(updates)
    return {
        "id": session_id,
        "hours": hours,
        "base_xp": base_xp,
        "question_xp": bonus_xp,
        "questions": total,
        "correct": correct,
        "already_completed": False,
    }
