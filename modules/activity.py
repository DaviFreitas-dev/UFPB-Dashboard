from datetime import date

from modules.database import append_record, new_id, records, update_record


def today():
    today_text = str(date.today())
    return [
        row
        for row in records("Atividade")
        if row.get("data") == today_text and row.get("feito") == "Sim"
    ]


def add(activity_type):
    rows = records("Atividade")
    today_text = str(date.today())
    existing = next(
        (
            row
            for row in rows
            if row.get("data") == today_text
            and row.get("tipo") == activity_type
        ),
        None,
    )

    if existing and existing.get("id"):
        update_record("Atividade", existing["id"], {"feito": "Sim"})
        return

    append_record("Atividade", [new_id(), today_text, activity_type, "Sim"])
