import re
from datetime import date

from modules.database import (
    append_record,
    delete_record,
    new_id,
    records,
    update_record,
)
from modules.gamification import award_xp_once


_TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class RoutineIdConflict(ValueError):
    pass


def _record_with_id(item_id):
    requested_id = str(item_id).strip()
    if not requested_id:
        return None
    return next(
        (
            row
            for row in records("Rotina")
            if str(row.get("id") or "").strip() == requested_id
        ),
        None,
    )


def records_for_date(target_date):
    target = str(target_date)
    return [
        row
        for row in records("Rotina")
        if str(row.get("data")) == target
    ]


def today_records():
    return records_for_date(date.today())


def add(activity, time_text, target_date=None, item_id=None):
    target = target_date or date.today()
    activity_text = str(activity).strip()
    normalized_time = str(time_text).strip()
    if not activity_text:
        raise ValueError("A atividade é obrigatória.")
    if len(activity_text) > 160:
        raise ValueError("A atividade deve ter até 160 caracteres.")
    if not _TIME_PATTERN.fullmatch(normalized_time):
        raise ValueError("O horário deve usar o formato HH:MM.")

    record_id = str(item_id or new_id())
    expected = {
        "id": record_id,
        "data": str(target),
        "hora": normalized_time,
        "atividade": activity_text,
        "status": "Pendente",
    }
    existing = _record_with_id(record_id)
    if existing is not None:
        immutable_fields = ("id", "data", "hora", "atividade")
        comparable = {
            key: str(existing.get(key, ""))
            for key in immutable_fields
        }
        requested = {
            key: str(expected[key])
            for key in immutable_fields
        }
        if comparable == requested:
            return existing, False
        raise RoutineIdConflict(
            "O ID do compromisso já existe com outro conteúdo."
        )

    append_record(
        "Rotina",
        [
            expected[column]
            for column in ("id", "data", "hora", "atividade", "status")
        ],
        value_input_option="RAW",
    )
    return expected, True


def set_completed(item_id, completed):
    normalized_id = str(item_id).strip()
    current = _record_with_id(normalized_id)
    if current is None:
        return None, False

    target = "Concluída" if completed else "Pendente"
    current_status = str(current.get("status") or "").strip()
    already_completed = current_status.casefold() in {
        "concluída",
        "concluida",
    }
    if completed and already_completed:
        award_xp_once(
            f"routine:{normalized_id}",
            10,
            "rotina",
            "Compromisso do dia concluído",
        )
        return {**current, "status": target}, False
    if current_status == target:
        return {**current, "status": target}, False

    if not update_record("Rotina", current["id"], {"status": target}):
        return None, False

    confirmed = {**current, "status": target}
    if completed:
        award_xp_once(
            f"routine:{normalized_id}",
            10,
            "rotina",
            "Compromisso do dia concluído",
        )
    return confirmed, True


def toggle(item_id, done):
    return set_completed(item_id, done)


def remove(item_id):
    current = _record_with_id(item_id)
    if current is None:
        return False
    return delete_record("Rotina", current["id"])
