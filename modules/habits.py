from datetime import date

from modules.database import append_record, new_id, records, update_record


def add(name):
    rows = records("HabitosConfig")
    if any(str(row["nome"]).lower() == name.lower() for row in rows):
        return False
    append_record("HabitosConfig", [new_id(), name, "Sim"])
    return True


def today():
    configs = [row for row in records("HabitosConfig") if row["ativo"] == "Sim"]
    logs = records("Habitos")
    today_text = str(date.today())
    today_logs = {row["habito"]: row for row in logs if row["data"] == today_text}

    for habit in configs:
        name = habit["nome"]
        if name in today_logs:
            continue
        new_log = {
            "id": new_id(),
            "data": today_text,
            "habito": name,
            "feito": "Não",
        }
        append_record(
            "Habitos",
            [new_log["id"], new_log["data"], new_log["habito"], new_log["feito"]],
        )
        today_logs[name] = new_log

    return list(today_logs.values())


def toggle(log_id, done):
    update_record("Habitos", log_id, {"feito": "Sim" if done else "Não"})
