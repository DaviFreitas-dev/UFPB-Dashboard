from datetime import date

from modules.database import append_record, new_id, records, update_record


def today_records():
    today = str(date.today())
    return [row for row in records("Tarefas") if row["data"] == today]


def add(task, category):
    append_record("Tarefas", [new_id(), str(date.today()), task, category, "Pendente"])


def toggle(item_id, done):
    update_record("Tarefas", item_id, {"status": "Concluída" if done else "Pendente"})
