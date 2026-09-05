from datetime import date

from modules.database import append_record, new_id, records, update_record
from modules.gamification import award_xp_once, xp_write_lock


ACTIVITY_TYPES = ("Treino", "Caminhada", "Corrida", "Alongamento", "Outro")
_ACTIVITY_TYPE_KEYS = {activity_type.casefold() for activity_type in ACTIVITY_TYPES}


class ActivityIdConflict(ValueError):
    pass


def normalize_activity_type(activity_type):
    normalized = str(activity_type or "").strip()
    if normalized.casefold() not in _ACTIVITY_TYPE_KEYS:
        raise ValueError("Escolha um tipo de atividade válido.")
    return normalized


def _same_activity(row, target, activity_key):
    return (
        str(row.get("data") or "").strip() == target
        and str(row.get("tipo") or "").strip().casefold() == activity_key
    )


def _completed(row):
    return str(row.get("feito") or "").strip().casefold() == "sim"


def _has_equivalent_xp_event(target, activity_key):
    prefix = f"activity:{target}:"
    for row in records("XPEventos"):
        event_key = str(row.get("event_key") or "").strip()
        if not event_key.startswith(prefix):
            continue
        if event_key[len(prefix) :].strip().casefold() == activity_key:
            return True
    return False


def _award_activity_xp(target, activity_key):
    with xp_write_lock():
        if _has_equivalent_xp_event(target, activity_key):
            return 0
        return award_xp_once(
            f"activity:{target}:{activity_key}",
            20,
            "atividade",
            "Atividade física registrada",
        )


def records_for_date(target_date):
    target = str(target_date)
    return [
        row
        for row in records("Atividade")
        if str(row.get("data") or "").strip() == target and _completed(row)
    ]


def today():
    return records_for_date(date.today())


def add(activity_type, target_date=None, item_id=None):
    activity_text = normalize_activity_type(activity_type)
    activity_key = activity_text.casefold()
    target = str(target_date or date.today())
    record_id = str(item_id or new_id()).strip()
    if not record_id:
        raise ValueError("O identificador da atividade é obrigatório.")

    rows = records("Atividade")
    requested_record = next(
        (
            row
            for row in rows
            if str(row.get("id") or "").strip() == record_id
        ),
        None,
    )
    if requested_record is not None and not _same_activity(
        requested_record,
        target,
        activity_key,
    ):
        raise ActivityIdConflict(
            "O ID da atividade já existe com outro conteúdo."
        )

    existing = requested_record or next(
        (
            row
            for row in rows
            if _same_activity(row, target, activity_key)
        ),
        None,
    )
    if existing is not None:
        if not _completed(existing):
            existing_id = str(existing.get("id") or "").strip()
            if not existing_id:
                raise ActivityIdConflict(
                    "O registro legado precisa de um ID antes da atualização."
                )
            if not update_record("Atividade", existing["id"], {"feito": "Sim"}):
                raise RuntimeError("A atividade não pôde ser confirmada.")
            confirmed = {**existing, "feito": "Sim"}
            _award_activity_xp(target, activity_key)
            return confirmed, False, True

        _award_activity_xp(target, activity_key)
        return existing, False, False

    expected = {
        "id": record_id,
        "data": target,
        "tipo": activity_text,
        "feito": "Sim",
    }
    append_record(
        "Atividade",
        [expected[column] for column in ("id", "data", "tipo", "feito")],
        value_input_option="RAW",
    )
    _award_activity_xp(target, activity_key)
    return expected, True, True
