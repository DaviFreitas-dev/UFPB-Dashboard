import threading
from datetime import date, timedelta

from modules.database import (
    new_id,
    records,
    write_values_batch,
)


XP_WRITE_LOCK = threading.RLock()


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def award_xp_once(event_key, amount, source, description):
    """Record one reward and its derived balances in a single Sheets batch."""
    amount = max(0, int(amount))
    if amount <= 0:
        return 0

    event_key = str(event_key).strip()
    if not event_key:
        raise ValueError("A recompensa precisa de um identificador único.")

    with XP_WRITE_LOCK:
        xp_events = records("XPEventos")

        if any(
            str(row.get("event_key")) == event_key
            for row in xp_events
        ):
            return 0

        tables = {
            "XPEventos": xp_events,
            "Usuario": records("Usuario"),
            "Historico": records("Historico"),
        }

        today = str(date.today())
        updates = []

        event_row_number = len(tables["XPEventos"]) + 2
        updates.append(
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
        )

        xp_row = next(
            (
                row
                for row in tables["Usuario"]
                if str(row.get("chave")) == "xp"
            ),
            None,
        )
        if xp_row is None:
            user_row_number = len(tables["Usuario"]) + 2
            updates.append(
                {
                    "sheet": "Usuario",
                    "range": f"A{user_row_number}:B{user_row_number}",
                    "values": [["xp", str(amount)]],
                }
            )
        else:
            current_xp = max(0, _safe_int(xp_row.get("valor")))
            user_row_number = tables["Usuario"].index(xp_row) + 2
            updates.append(
                {
                    "sheet": "Usuario",
                    "range": f"B{user_row_number}",
                    "values": [[str(current_xp + amount)]],
                }
            )

        history_row = next(
            (
                row
                for row in tables["Historico"]
                if str(row.get("data")) == today
            ),
            None,
        )
        if history_row is None:
            history_row_number = len(tables["Historico"]) + 2
            history_values = [today, 0, amount]
        else:
            history_row_number = tables["Historico"].index(history_row) + 2
            history_values = [
                today,
                _safe_int(history_row.get("horas")),
                _safe_int(history_row.get("xp")) + amount,
            ]
        updates.append(
            {
                "sheet": "Historico",
                "range": f"A{history_row_number}:C{history_row_number}",
                "values": [history_values],
            }
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
