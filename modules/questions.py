from datetime import date, timedelta

from modules.database import append_record, new_id, records

__all__ = [
    "history",
    "questions_between",
    "record_session",
    "subject_totals",
    "totals",
    "weekly_accuracy_series",
]


def questions_between(start_date, end_date):
    """Return question totals for an inclusive date range.

    Kept near the top of the module because other planning modules import it
    during application startup.
    """
    total = 0
    correct = 0
    wrong = 0

    for row in records("Questoes"):
        try:
            day = date.fromisoformat(str(row.get("data")))
            if start_date <= day <= end_date:
                total += int(row.get("feitas", 0) or 0)
                correct += int(row.get("acertos", 0) or 0)
                wrong += int(row.get("erros", 0) or 0)
        except (TypeError, ValueError):
            continue

    return {
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "accuracy": correct / total if total else 0,
    }


def record_session(mission, total, correct, wrong):
    total = int(total)
    correct = int(correct)
    wrong = int(wrong)

    if min(total, correct, wrong) < 0:
        raise ValueError("Os valores não podem ser negativos.")

    if correct + wrong != total:
        raise ValueError("Acertos + erros precisam ser iguais ao total de questões.")

    subjects = " | ".join(mission.keys())

    append_record(
        "Questoes",
        [
            new_id(),
            str(date.today()),
            subjects,
            total,
            correct,
            wrong,
        ],
    )


def totals():
    total = 0
    correct = 0
    wrong = 0

    for row in records("Questoes"):
        try:
            total += int(row.get("feitas", 0) or 0)
            correct += int(row.get("acertos", 0) or 0)
            wrong += int(row.get("erros", 0) or 0)
        except (TypeError, ValueError):
            continue

    accuracy = correct / total if total else 0

    return {
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "accuracy": accuracy,
    }


def subject_totals():
    data = {}

    for row in records("SessoesEstudo"):
        subject = str(row.get("disciplina", "")).strip()
        if not subject:
            continue

        bucket = data.setdefault(
            subject,
            {"total": 0, "correct": 0, "wrong": 0},
        )

        try:
            bucket["total"] += int(row.get("questoes", 0) or 0)
            bucket["correct"] += int(row.get("acertos", 0) or 0)
            bucket["wrong"] += int(row.get("erros", 0) or 0)
        except (TypeError, ValueError):
            continue

    for values in data.values():
        values["accuracy"] = (
            values["correct"] / values["total"]
            if values["total"]
            else 0
        )

    return data


def weekly_accuracy_series(weeks=8):
    today = date.today()
    this_monday = today - timedelta(days=today.weekday())
    result = []

    for offset in reversed(range(weeks)):
        start = this_monday - timedelta(weeks=offset)
        end = start + timedelta(days=6)
        stats = questions_between(start, end)
        result.append(
            {
                "semana": start.strftime("%d/%m"),
                "questoes": stats["total"],
                "acuracia": stats["accuracy"] * 100,
            }
        )

    return result


def history():
    return records("Questoes")
