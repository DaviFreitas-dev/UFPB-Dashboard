import hashlib
from datetime import date, timedelta

from modules.config import XP_POR_HORA
from modules.database import (
    records,
    write_values_batch,
)
from modules.gamification import build_xp_balance_updates, xp_write_lock


class MissionConsistencyError(RuntimeError):
    """A missão sorteada não corresponde mais ao estado atual do ciclo."""


def _derived_id(session_id, suffix):
    value = f"{session_id}:{suffix}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()[:10]


def _as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _find_row(rows, field, value):
    return next(
        (row for row in rows if str(row.get(field)) == str(value)),
        None,
    )


def _normalize_mission(mission):
    normalized = {}
    for subject, amount in mission.items():
        hours = int(amount)
        if not subject or hours <= 0:
            raise ValueError("A missão possui uma carga horária inválida.")
        normalized[str(subject)] = hours
    return normalized


def _completed_result(
    session_id,
    xp_events,
    base_event_key,
    question_event_key,
    hours,
    total,
    correct,
):
    base_event = _find_row(xp_events, "event_key", base_event_key)
    if base_event is None:
        return None

    session = _find_row(records("SessoesEstudo"), "id", session_id)
    if session is None:
        raise MissionConsistencyError(
            "A missão possui recompensa registrada, mas a sessão não foi "
            "encontrada. Revise o backup antes de tentar novamente."
        )

    question_event = _find_row(
        xp_events,
        "event_key",
        question_event_key,
    )
    return {
        "id": session_id,
        "hours": _as_int(session.get("horas"), hours),
        "base_xp": _as_int(base_event.get("xp")),
        "question_xp": _as_int(
            question_event.get("xp") if question_event else 0
        ),
        "questions": _as_int(session.get("questoes"), total),
        "correct": _as_int(session.get("acertos"), correct),
        "already_completed": True,
    }


def _cycle_updates(cycle_rows, mission):
    updates = []
    missing_subjects = set(mission)

    for row_number, row in enumerate(cycle_rows, start=2):
        subject = str(row.get("disciplina", ""))
        if subject not in mission:
            continue

        remaining = _as_int(row.get("restantes"))
        requested = mission[subject]
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
        missing_subjects.discard(subject)

    if missing_subjects:
        subjects = ", ".join(sorted(missing_subjects))
        raise MissionConsistencyError(
            f"As disciplinas não existem mais no ciclo: {subjects}."
        )

    return updates


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
    with xp_write_lock():
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

    normalized_mission = _normalize_mission(mission)
    hours = sum(normalized_mission.values())
    if hours <= 0:
        raise ValueError("A missão precisa ter ao menos uma hora.")
    if primary_subject not in normalized_mission:
        raise ValueError("A disciplina principal deve fazer parte da missão.")

    base_event_key = f"session:{session_id}:mission"
    question_event_key = f"session:{session_id}:questions"
    xp_events = records("XPEventos")
    completed = _completed_result(
        session_id,
        xp_events,
        base_event_key,
        question_event_key,
        hours,
        total,
        correct,
    )
    if completed:
        return completed

    rows_by_sheet = {
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
    rows_by_sheet["XPEventos"] = xp_events

    updates = _cycle_updates(
        rows_by_sheet["Ciclo"],
        normalized_mission,
    )

    bonus_xp = question_xp(total, correct)
    base_xp = hours * XP_POR_HORA
    total_xp = base_xp + bonus_xp
    today = date.today()
    today_text = str(today)
    updates.extend(
        build_xp_balance_updates(
            rows_by_sheet["Usuario"],
            rows_by_sheet["Historico"],
            total_xp,
            hours=hours,
            day=today_text,
        )
    )

    topic_text = str(topic).strip() or "Revisão geral"
    note_text = str(note).strip()
    session_row_number = len(rows_by_sheet["SessoesEstudo"]) + 2
    updates.append(
        {
            "sheet": "SessoesEstudo",
            "range": f"A{session_row_number}:I{session_row_number}",
            "values": [
                [
                    session_id,
                    today_text,
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

    question_row_number = len(rows_by_sheet["Questoes"]) + 2
    updates.append(
        {
            "sheet": "Questoes",
            "range": f"A{question_row_number}:F{question_row_number}",
            "values": [
                [
                    _derived_id(session_id, "questions"),
                    today_text,
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
                    today_text,
                    str(today + timedelta(days=days)),
                    subject,
                    topic_text,
                    "Pendente",
                    f"session:{session_id}:{subject}:{days}",
                ]
            )
    review_start = len(rows_by_sheet["Revisoes"]) + 2
    review_end = review_start + len(review_values) - 1
    updates.append(
        {
            "sheet": "Revisoes",
            "range": f"A{review_start}:G{review_end}",
            "values": review_values,
        }
    )

    if wrong > 0:
        error_row_number = len(rows_by_sheet["Erros"]) + 2
        updates.append(
            {
                "sheet": "Erros",
                "range": f"A{error_row_number}:G{error_row_number}",
                "values": [
                    [
                        _derived_id(session_id, "error"),
                        today_text,
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
            today_text,
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
                today_text,
                "questoes",
                "Questões e desempenho da sessão",
                bonus_xp,
            ]
        )
    xp_event_start = len(rows_by_sheet["XPEventos"]) + 2
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
