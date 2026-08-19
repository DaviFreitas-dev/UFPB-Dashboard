from datetime import date

from modules.database import (
    append_record,
    delete_record,
    new_id,
    records,
    update_record,
)
from modules.gamification import award_xp_once


def records_for_date(target_date):
    target = str(target_date)
    return [
        row
        for row in records("Rotina")
        if str(row.get("data")) == target
    ]


def today_records():
    return records_for_date(date.today())


def add(activity, time_text, target_date=None):
    target = target_date or date.today()
    append_record(
        "Rotina",
        [new_id(), str(target), time_text, activity, "Pendente"],
    )


def toggle(item_id, done):
    updated = update_record(
        "Rotina",
        item_id,
        {"status": "Concluída" if done else "Pendente"},
    )

    if updated and done:
        award_xp_once(
            f"routine:{item_id}",
            10,
            "rotina",
            "Compromisso do dia concluído",
        )


def remove(item_id):
    return delete_record("Rotina", item_id)
