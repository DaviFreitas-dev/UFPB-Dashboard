from datetime import date

from modules.database import append_record, new_id, records, update_record


def today():
    today_text = str(date.today())
    return [
        row
        for row in records("Atividade")
        if row["data"] == today_text and row["feito"] == "Sim"
    ]


def add(activity_type):
    rows = records("Atividade")
    today_text = str(date.today())
    existing = next(
        (
            row
            for row in rows
            if row["data"] == today_text and row["tipo"] == activity_type
        ),
        None,
    )
    if existing:
        update_record("Atividade", existing["id"], {"feito": "Sim"})
        return
    append_record("Atividade", [new_id(), today_text, activity_type, "Sim"])
