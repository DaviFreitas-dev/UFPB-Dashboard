from datetime import date

from modules.database import new_id, records, replace_records


def add(name):
    rows = records("HabitosConfig")
    if any(row["nome"].lower() == name.lower() for row in rows):
        return

    rows.append({
        "id": new_id(),
        "nome": name,
        "ativo": "Sim",
    })

    replace_records(
        "HabitosConfig",
        [[r["id"], r["nome"], r["ativo"]] for r in rows],
    )


def today():
    configs = [r for r in records("HabitosConfig") if r["ativo"] == "Sim"]
    logs = records("Habitos")
    today_text = str(date.today())

    for habit in configs:
        existing = next(
            (
                row for row in logs
                if row["data"] == today_text
                and row["habito"] == habit["nome"]
            ),
            None,
        )

        if existing is None:
            logs.append({
                "id": new_id(),
                "data": today_text,
                "habito": habit["nome"],
                "feito": "Não",
            })

    replace_records(
        "Habitos",
        [[r["id"], r["data"], r["habito"], r["feito"]] for r in logs],
    )

    return [
        row for row in logs
        if row["data"] == today_text
    ]


def toggle(log_id, done):
    rows = records("Habitos")

    for row in rows:
        if row["id"] == log_id:
            row["feito"] = "Sim" if done else "Não"

    replace_records(
        "Habitos",
        [[r["id"], r["data"], r["habito"], r["feito"]] for r in rows],
    )
