import uuid
from datetime import date, timedelta

from modules.database import (
    append_record,
    new_id,
    records,
    update_record,
    write_values_batch,
)
from modules.gamification import award_xp_once, xp_write_lock


HABIT_LOG_NAMESPACE = uuid.UUID("698cd68b-c9a8-4f34-b527-f6809e2d3f10")


class HabitIdConflict(ValueError):
    pass


def _normalized_name(value):
    return " ".join(str(value or "").split())


def _name_key(value):
    return _normalized_name(value).casefold()


def _is_yes(value):
    return str(value or "").strip().casefold() == "sim"


def _config_with_id(config_id):
    wanted = str(config_id or "").strip()
    if not wanted:
        return None
    return next(
        (
            row
            for row in records("HabitosConfig")
            if str(row.get("id") or "").strip() == wanted
        ),
        None,
    )


def _daily_record(config, target_date, log=None):
    config_id = str(config.get("id") or "").strip()
    name = _normalized_name(config.get("nome"))
    log_id = str(log.get("id") or "").strip() or None if log else None
    return {
        "id": log_id,
        "config_id": config_id,
        "data": str(target_date),
        "habito": name,
        "feito": "Sim" if log and _is_yes(log.get("feito")) else "Não",
    }


def _log_for(logs, name, target_date):
    name_key = _name_key(name)
    target = str(target_date)
    return next(
        (
            row
            for row in logs
            if str(row.get("data")) == target
            and _name_key(row.get("habito")) == name_key
        ),
        None,
    )


def _deterministic_log_id(config_id, target_date):
    return str(uuid.uuid5(HABIT_LOG_NAMESPACE, f"{config_id}:{target_date}"))


def active_configs():
    return [row for row in records("HabitosConfig") if _is_yes(row.get("ativo"))]


def records_for_date(target_date):
    target = str(target_date)
    logs = records("Habitos")
    result = []
    seen = set()
    for config in active_configs():
        name = _normalized_name(config.get("nome"))
        key = _name_key(name)
        if not name or key in seen:
            continue
        seen.add(key)
        result.append(_daily_record(config, target, _log_for(logs, name, target)))
    return result


def today():
    return records_for_date(date.today())


def add(name, item_id=None):
    name_text = _normalized_name(name)
    if not name_text:
        raise ValueError("O nome do hábito é obrigatório.")

    with xp_write_lock():
        configs = records("HabitosConfig")
        requested_id = str(item_id or "").strip()
        if requested_id and any(
            str(row.get("id") or "").strip() == requested_id
            and _name_key(row.get("nome")) != _name_key(name_text)
            for row in configs
        ):
            raise HabitIdConflict("O ID do hábito já existe com outro conteúdo.")
        existing = next(
            (
                row
                for row in configs
                if _name_key(row.get("nome")) == _name_key(name_text)
            ),
            None,
        )
        if existing is not None:
            if _is_yes(existing.get("ativo")):
                return existing, False, False
            persisted_id = str(existing.get("id") or "")
            if not persisted_id.strip() or not update_record(
                "HabitosConfig", persisted_id, {"ativo": "Sim"}
            ):
                raise RuntimeError("Não foi possível reativar o hábito.")
            return {**existing, "ativo": "Sim"}, False, True

        record_id = str(item_id or new_id()).strip()
        if not record_id:
            raise ValueError("O hábito precisa de um identificador.")
        record = {"id": record_id, "nome": name_text, "ativo": "Sim"}
        append_record(
            "HabitosConfig",
            [record["id"], record["nome"], record["ativo"]],
            value_input_option="RAW",
        )
        return record, True, False


def set_active(config_id, active):
    normalized_id = str(config_id or "").strip()
    with xp_write_lock():
        current = _config_with_id(normalized_id)
        if current is None:
            return None, False
        target = "Sim" if active else "Não"
        if str(current.get("ativo") or "").strip().casefold() == target.casefold():
            return {**current, "id": normalized_id, "ativo": target}, False
        persisted_id = str(current.get("id") or "")
        if not update_record("HabitosConfig", persisted_id, {"ativo": target}):
            return None, False
        return {**current, "id": normalized_id, "ativo": target}, True


def archive(config_id):
    _, changed = set_active(config_id, False)
    return changed


def _update_legacy_log(logs, current, log_id, target_date, name, target):
    row_number = logs.index(current) + 2
    write_values_batch(
        [
            {
                "sheet": "Habitos",
                "range": f"A{row_number}:D{row_number}",
                "values": [[log_id, str(target_date), name, target]],
            }
        ]
    )


def set_completed(config_id, target_date, completed):
    normalized_id = str(config_id or "").strip()
    with xp_write_lock():
        config = _config_with_id(normalized_id)
        if config is None:
            return None, False

        target_date_text = str(target_date)
        name = _normalized_name(config.get("nome"))
        logs = records("Habitos")
        current = _log_for(logs, name, target_date_text)
        if current is None:
            if not completed:
                return _daily_record(config, target_date_text), False
            log_id = _deterministic_log_id(normalized_id, target_date_text)
            confirmed = {
                "id": log_id,
                "config_id": normalized_id,
                "data": target_date_text,
                "habito": name,
                "feito": "Sim",
            }
            append_record(
                "Habitos",
                [log_id, target_date_text, name, "Sim"],
                value_input_option="RAW",
            )
            award_xp_once(
                f"habit:{log_id}",
                10,
                "habito",
                "Hábito concluído",
            )
            return confirmed, True

        target = "Sim" if completed else "Não"
        log_id = str(current.get("id") or "").strip()
        already_target = _is_yes(current.get("feito")) == bool(completed)
        if not log_id and already_target and not completed:
            return _daily_record(config, target_date_text, current), False
        needs_identity = not log_id
        if not log_id:
            log_id = _deterministic_log_id(normalized_id, target_date_text)
        if not already_target or needs_identity:
            persisted_id = str(current.get("id") or "")
            if persisted_id.strip():
                if not update_record("Habitos", persisted_id, {"feito": target}):
                    return None, False
            else:
                _update_legacy_log(
                    logs,
                    current,
                    log_id,
                    target_date_text,
                    name,
                    target,
                )

        confirmed = {
            "id": log_id,
            "config_id": normalized_id,
            "data": target_date_text,
            "habito": name,
            "feito": target,
        }
        if completed:
            award_xp_once(
                f"habit:{log_id}",
                10,
                "habito",
                "Hábito concluído",
            )
        return confirmed, not already_target or needs_identity


def toggle(config_id, done, target_date=None):
    return set_completed(config_id, target_date or date.today(), done)


def streaks(habit_names):
    wanted = {_name_key(name): _normalized_name(name) for name in habit_names}
    completed = {key: set() for key in wanted}

    for row in records("Habitos"):
        key = _name_key(row.get("habito"))
        if key not in wanted or not _is_yes(row.get("feito")):
            continue
        try:
            completed[key].add(date.fromisoformat(str(row.get("data"))))
        except (TypeError, ValueError):
            continue

    result = {}
    for key, completed_days in completed.items():
        name = wanted[key]
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
