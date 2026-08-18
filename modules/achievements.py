from datetime import date

from modules.database import get_xp, replace_records
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

    rows = [
        [
            item[0],
            item[1],
            item[2],
            "Sim" if item[3] else "Não",
            str(date.today()) if item[3] else "",
        ]
        for item in items
    ]

    replace_records("Conquistas", rows)
    return items
