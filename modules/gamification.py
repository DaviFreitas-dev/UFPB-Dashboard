import threading
from datetime import date, timedelta

from modules.database import (
    new_id,
    records,
    write_values_batch,
)


_XP_WRITE_LOCK = threading.RLock()


def _as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _find_row(rows, field, value):
    return next(
        (row for row in rows if str(row.get(field)) == str(value)),
        None,
    )


def xp_write_lock():
    return _XP_WRITE_LOCK


def build_xp_balance_updates(
    user_rows,
    history_rows,
    amount,
    hours=0,
    day=None,
):
    """Monta as atualizações de saldo e histórico para o lote do evento."""
    day = str(day or date.today())
    amount = int(amount)
    hours = int(hours)

    xp_row = _find_row(user_rows, "chave", "xp")
    if xp_row is None:
        user_row_number = len(user_rows) + 2
        user_update = {
            "sheet": "Usuario",
            "range": f"A{user_row_number}:B{user_row_number}",
            "values": [["xp", str(amount)]],
        }
    else:
        current_xp = max(0, _as_int(xp_row.get("valor")))
        user_row_number = user_rows.index(xp_row) + 2
        user_update = {
            "sheet": "Usuario",
            "range": f"B{user_row_number}",
            "values": [[str(current_xp + amount)]],
        }

    history_row = _find_row(history_rows, "data", day)
    if history_row is None:
        history_row_number = len(history_rows) + 2
        history_values = [day, hours, amount]
    else:
        history_row_number = history_rows.index(history_row) + 2
        history_values = [
            day,
            _as_int(history_row.get("horas")) + hours,
            _as_int(history_row.get("xp")) + amount,
        ]

    history_update = {
        "sheet": "Historico",
        "range": f"A{history_row_number}:C{history_row_number}",
        "values": [history_values],
    }
    return [user_update, history_update]


def award_xp_once(event_key, amount, source, description):
    amount = max(0, int(amount))
    if amount <= 0:
        return 0

    event_key = str(event_key).strip()
    if not event_key:
        raise ValueError("A recompensa precisa de um identificador único.")

    with xp_write_lock():
        xp_events = records("XPEventos")
        if _find_row(xp_events, "event_key", event_key) is not None:
            return 0

        today = str(date.today())
        event_row_number = len(xp_events) + 2
        updates = [
            {
                "sheet": "XPEventos",
                "range": f"A{event_row_number}:F{event_row_number}",
                "values": [
                    [
                        new_id(),
                        event_key,
                        today,
                        str(source),
                        str(description),
                        amount,
                    ]
                ],
            }
        ]
        updates.extend(
            build_xp_balance_updates(
                records("Usuario"),
                records("Historico"),
                amount,
                day=today,
            )
        )

        write_values_batch(updates)
        return amount


def general_streak():
    active_days = set()

    sources = [
        ("Historico", lambda row: int(row.get("horas", 0) or 0) > 0),
        ("Tarefas", lambda row: row.get("status") == "Concluída"),
        ("Habitos", lambda row: row.get("feito") == "Sim"),
        ("Atividade", lambda row: row.get("feito") == "Sim"),
        ("AgendaCheckins", lambda row: row.get("status") == "Concluída"),
        ("SessoesEstudo", lambda row: True),
    ]

    for sheet, predicate in sources:
        for row in records(sheet):
            try:
                if predicate(row):
                    active_days.add(date.fromisoformat(str(row.get("data"))))
            except (TypeError, ValueError):
                continue

    if not active_days:
        return 0

    cursor = date.today()
    if cursor not in active_days:
        cursor -= timedelta(days=1)

    streak = 0
    while cursor in active_days:
        streak += 1
        cursor -= timedelta(days=1)

    return streak
