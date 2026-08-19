from datetime import date, timedelta

from modules.database import append_record, new_id, records, update_record


def active_configs():
    return [
        row
        for row in records("HabitosConfig")
        if row["ativo"] == "Sim"
    ]


def add(name):
    rows = records("HabitosConfig")
    existing = next(
        (
            row
            for row in rows
            if str(row["nome"]).lower() == name.lower()
        ),
        None,
    )

    if existing:
        if existing["ativo"] != "Sim":
            update_record("HabitosConfig", existing["id"], {"ativo": "Sim"})
            return True
        return False

    append_record("HabitosConfig", [new_id(), name, "Sim"])
    return True


def archive(config_id):
    return update_record("HabitosConfig", config_id, {"ativo": "Não"})


def today():
    configs = active_configs()
    logs = records("Habitos")
    today_text = str(date.today())
    today_logs = {
        row["habito"]: row
        for row in logs
        if row["data"] == today_text
    }

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
            [
                new_log["id"],
                new_log["data"],
                new_log["habito"],
                new_log["feito"],
            ],
        )
        today_logs[name] = new_log

    return [
        today_logs[config["nome"]]
        for config in configs
        if config["nome"] in today_logs
    ]


def toggle(log_id, done):
    update_record(
        "Habitos",
        log_id,
        {"feito": "Sim" if done else "Não"},
    )


def streaks(habit_names):
    wanted = set(habit_names)
    completed = {name: set() for name in wanted}

    for row in records("Habitos"):
        name = row.get("habito")
        if name not in wanted or row.get("feito") != "Sim":
            continue
        try:
            completed[name].add(date.fromisoformat(str(row["data"])))
        except (TypeError, ValueError):
            continue

    result = {}
    for name, completed_days in completed.items():
        if not completed_days:
            result[name] = 0
            continue

        cursor = date.today()
        if cursor not in completed_days:
            cursor -= timedelta(days=1)

        count = 0
        while cursor in completed_days:
            count += 1
            cursor -= timedelta(days=1)

        result[name] = count

    return result
