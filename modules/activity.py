from datetime import date

from modules.database import append_record, new_id, records, update_record
from modules.gamification import award_xp_once


def today():
    today_text = str(date.today())
    return [
        row
        for row in records("Atividade")
        if str(row.get("data")) == today_text
        and row.get("feito") == "Sim"
    ]


def add(activity_type):
    rows = records("Atividade")
    today_text = str(date.today())

    existing = next(
        (
            row
            for row in rows
            if str(row.get("data")) == today_text
            and row.get("tipo") == activity_type
        ),
        None,
    )

    if existing:
        update_record("Atividade", existing["id"], {"feito": "Sim"})
    else:
        append_record(
            "Atividade",
            [new_id(), today_text, activity_type, "Sim"],
        )

    award_xp_once(
        f"activity:{today_text}:{activity_type}",
        20,
        "atividade",
        "Atividade física registrada",
    )
