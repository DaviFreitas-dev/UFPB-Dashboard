from datetime import date

from modules.database import get_xp, records, replace_records
from modules.gamification import general_streak
from modules.questions import totals as question_totals
from modules.studies import stats


def check():
    xp = get_xp()
    study = stats()
    questions = question_totals()
    streak = general_streak()

    reviews_done = sum(
        row.get("status") == "Concluída"
        for row in records("Revisoes")
    )
    bosses_done = sum(
        row.get("status") == "Concluída" and row.get("tipo") == "Prova"
        for row in records("Avaliacoes")
    )

    items = [
        ("1", "Primeiro passo", "Conclua sua primeira hora de estudo.", study["hours"] >= 1),
        ("2", "10 horas", "Acumule 10 horas de estudo.", study["hours"] >= 10),
        ("3", "50 horas", "Acumule 50 horas de estudo.", study["hours"] >= 50),
        ("4", "100 questões", "Resolva 100 questões.", questions["total"] >= 100),
        ("5", "500 questões", "Resolva 500 questões.", questions["total"] >= 500),
        ("6", "1.000 questões", "Resolva 1.000 questões.", questions["total"] >= 1000),
        (
            "7",
            "Precisão",
            "Mantenha 80% de acerto em pelo menos 100 questões.",
            questions["total"] >= 100 and questions["accuracy"] >= 0.80,
        ),
        ("8", "Uma semana", "Mantenha uma sequência geral de 7 dias.", streak >= 7),
        ("9", "Revisor", "Conclua 10 revisões programadas.", reviews_done >= 10),
        ("10", "Boss derrotado", "Conclua uma prova cadastrada.", bosses_done >= 1),
        ("11", "Nível alto", "Alcance 5.000 XP.", xp >= 5000),
    ]

    existing = {
        str(row.get("id")): row
        for row in records("Conquistas")
    }
    changed = False
    rows = []

    for item_id, name, description, unlocked in items:
        previous = existing.get(item_id, {})
        previous_unlocked = previous.get("desbloqueada") == "Sim"
        unlocked_now = unlocked or previous_unlocked
        unlock_date = previous.get("data", "")

        if unlocked and not previous_unlocked:
            unlock_date = str(date.today())
            changed = True

        row = [
            item_id,
            name,
            description,
            "Sim" if unlocked_now else "Não",
            unlock_date,
        ]
        rows.append(row)

        comparable = [
            str(previous.get("id", "")),
            str(previous.get("nome", "")),
            str(previous.get("descricao", "")),
            str(previous.get("desbloqueada", "")),
            str(previous.get("data", "")),
        ]

        if not previous or comparable != [str(value) for value in row]:
            changed = True

    if changed:
        replace_records("Conquistas", rows)

    return [
        (
            item_id,
            name,
            description,
            unlocked or existing.get(item_id, {}).get("desbloqueada") == "Sim",
        )
        for item_id, name, description, unlocked in items
    ]
