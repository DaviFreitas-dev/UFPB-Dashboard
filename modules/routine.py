from datetime import date

from modules.database import append_record, new_id, records, update_record


def today_records():
    today = str(date.today())
    return [row for row in records("Rotina") if row["data"] == today]


def add(activity, time_text):
    append_record("Rotina", [new_id(), str(date.today()), time_text, activity, "Pendente"])


def toggle(item_id, done):
    update_record("Rotina", item_id, {"status": "Concluída" if done else "Pendente"})
