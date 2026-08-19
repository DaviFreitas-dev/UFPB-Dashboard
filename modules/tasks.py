from datetime import date

from modules.database import (
    append_record,
    delete_record,
    new_id,
    records,
    update_record,
)


def records_for_date(target_date):
    target = str(target_date)
    return [row for row in records("Tarefas") if row["data"] == target]


def today_records():
    return records_for_date(date.today())


def add(task, category, target_date=None):
    target = target_date or date.today()
    append_record(
        "Tarefas",
        [new_id(), str(target), task, category, "Pendente"],
    )


def toggle(item_id, done):
    update_record(
        "Tarefas",
        item_id,
        {"status": "Concluída" if done else "Pendente"},
    )


def remove(item_id):
    return delete_record("Tarefas", item_id)
