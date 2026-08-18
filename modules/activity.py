from datetime import date

from modules.database import new_id, records, replace_records


def today():
    return [
        row for row in records("Atividade")
        if row["data"] == str(date.today())
        and row["feito"] == "Sim"
    ]


def add(activity_type):
    rows = records("Atividade")
    today_text = str(date.today())

    existing = next(
        (
            row for row in rows
            if row["data"] == today_text
            and row["tipo"] == activity_type
        ),
        None,
    )

    if existing:
        existing["feito"] = "Sim"
    else:
        rows.append({
            "id": new_id(),
            "data": today_text,
            "tipo": activity_type,
            "feito": "Sim",
        })

    replace_records(
        "Atividade",
        [[r["id"], r["data"], r["tipo"], r["feito"]] for r in rows],
    )
