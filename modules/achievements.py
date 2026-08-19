from datetime import date

from modules.database import get_xp, records, replace_records
from modules.studies import stats


def check():
    xp = get_xp()
    s = stats()

    items = [
        ("1", "Primeiro passo", "Conclua sua primeira hora de estudo.", s["hours"] >= 1),
        ("2", "500 XP", "Alcance 500 XP.", xp >= 500),
        ("3", "1.000 XP", "Alcance 1.000 XP.", xp >= 1000),
        ("4", "Uma semana", "Estude por 7 dias seguidos.", s["streak"] >= 7),
        ("5", "10 horas", "Estude 10 horas no total.", s["hours"] >= 10),
    ]

    existing = {str(row["id"]): row for row in records("Conquistas")}
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

        if not previous:
            changed = True
        else:
            comparable = [
                str(previous.get("id", "")),
                str(previous.get("nome", "")),
                str(previous.get("descricao", "")),
                str(previous.get("desbloqueada", "")),
                str(previous.get("data", "")),
            ]
            if comparable != [str(value) for value in row]:
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
