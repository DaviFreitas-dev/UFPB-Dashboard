from datetime import date

from modules.database import new_id, records, replace_records


def today_records():
    return [
        row for row in records("Rotina")
        if row["data"] == str(date.today())
    ]


def add(activity, time_text):
    rows = records("Rotina")
    rows.append({
        "id": new_id(),
        "data": str(date.today()),
        "hora": time_text,
        "atividade": activity,
        "status": "Pendente",
    })
    replace_records(
        "Rotina",
        [[r["id"], r["data"], r["hora"], r["atividade"], r["status"]] for r in rows],
    )


def toggle(item_id, done):
    rows = records("Rotina")
    for row in rows:
        if row["id"] == item_id:
            row["status"] = "Concluída" if done else "Pendente"
    replace_records(
        "Rotina",
        [[r["id"], r["data"], r["hora"], r["atividade"], r["status"]] for r in rows],
    )
