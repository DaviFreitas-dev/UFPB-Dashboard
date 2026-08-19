from datetime import date

from modules.database import append_record, new_id, records


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
            total += int(row.get("feitas", 0))
            correct += int(row.get("acertos", 0))
            wrong += int(row.get("erros", 0))
        except (TypeError, ValueError):
            continue

    accuracy = correct / total if total else 0

    return {
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "accuracy": accuracy,
    }


def history():
    return records("Questoes")
