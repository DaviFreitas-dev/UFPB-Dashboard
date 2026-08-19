from datetime import date, timedelta

from modules.database import (
    add_history,
    append_record,
    get_xp,
    new_id,
    records,
    set_xp,
)


def award_xp_once(event_key, amount, source, description):
    amount = max(0, int(amount))
    if amount <= 0:
        return 0

    if any(
        str(row.get("event_key")) == str(event_key)
        for row in records("XPEventos")
    ):
        return 0

    append_record(
        "XPEventos",
        [
            new_id(),
            str(event_key),
            str(date.today()),
            source,
            description,
            amount,
        ],
    )
    set_xp(get_xp() + amount)
    add_history(0, amount)
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
