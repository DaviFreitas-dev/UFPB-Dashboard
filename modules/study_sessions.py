from datetime import date

from modules.database import append_record, new_id
from modules.gamification import award_xp_once
from modules.planner import add_error, schedule_reviews
from modules.questions import record_session as record_question_session


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


def record_study_session(
    mission,
    primary_subject,
    topic,
    total,
    correct,
    wrong,
    note="",
):
    total = int(total)
    correct = int(correct)
    wrong = int(wrong)

    if min(total, correct, wrong) < 0:
        raise ValueError("Os valores não podem ser negativos.")

    if correct + wrong != total:
        raise ValueError("Acertos + erros precisam ser iguais ao total.")

    session_id = new_id()
    hours = sum(int(value) for value in mission.values())

    append_record(
        "SessoesEstudo",
        [
            session_id,
            str(date.today()),
            primary_subject,
            topic.strip() or "Revisão geral",
            hours,
            total,
            correct,
            wrong,
            note.strip(),
        ],
    )

    record_question_session(mission, total, correct, wrong)

    schedule_reviews(
        primary_subject,
        topic,
        origin=f"session:{session_id}",
    )

    if wrong > 0:
        add_error(
            primary_subject,
            topic,
            wrong,
            note,
        )

    bonus = question_xp(total, correct)
    bonus_awarded = award_xp_once(
        f"session:{session_id}:questions",
        bonus,
        "questoes",
        "Questões e desempenho da sessão",
    )

    return {
        "id": session_id,
        "hours": hours,
        "question_xp": bonus_awarded,
    }
