from api.dashboard import (
    _completed,
    _date,
    _equals,
    _row_id,
    _rows,
    _text,
    _today,
    _user,
)
from api.models import RoutineDashboard, RoutineItem
from api.sheets import read_dashboard_tables
from modules.config import WEEKDAYS


def _time_key(item):
    parts = item.time.split(":", 1)
    try:
        hour, minute = (int(part) for part in parts)
    except (TypeError, ValueError):
        return 24, 60, item.time, item.id
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        return 24, 60, item.time, item.id
    return hour, minute, item.time, item.id


def _items(tables, reference):
    result = []
    checkins = {
        _text(row.get("agenda_id")): row
        for row in _rows(tables, "AgendaCheckins")
        if _date(row.get("data")) == reference
    }
    weekday = WEEKDAYS[reference.weekday()]

    for index, row in enumerate(_rows(tables, "AgendaSemanal")):
        if not _equals(row.get("ativo"), "Sim"):
            continue
        if not _equals(row.get("dia_semana"), weekday):
            continue
        source_id = _row_id(row, "weekly", index)
        result.append(
            RoutineItem(
                id=f"fixed:{source_id}",
                time=_text(row.get("hora"), "--:--"),
                title=_text(row.get("atividade"), "Atividade sem título"),
                category=_text(row.get("categoria"), "Agenda fixa"),
                kind="fixed",
                completed=_completed(checkins.get(source_id, {}).get("status")),
            )
        )

    for index, row in enumerate(_rows(tables, "Rotina")):
        if _date(row.get("data")) != reference:
            continue
        source_id = _row_id(row, "routine", index)
        result.append(
            RoutineItem(
                id=f"custom:{source_id}",
                time=_text(row.get("hora"), "--:--"),
                title=_text(row.get("atividade"), "Compromisso sem título"),
                category="Avulso",
                kind="custom",
                completed=_completed(row.get("status")),
            )
        )

    return sorted(result, key=_time_key)


def build_routine_dashboard(tables, reference=None):
    reference = reference or _today()
    items = _items(tables, reference)
    fixed_count = sum(item.kind == "fixed" for item in items)
    return RoutineDashboard(
        date=str(reference),
        user=_user(tables, reference),
        total=len(items),
        completed=sum(item.completed for item in items),
        fixed_count=fixed_count,
        custom_count=len(items) - fixed_count,
        items=items,
    )


def load_routine_dashboard(reference=None):
    return build_routine_dashboard(read_dashboard_tables(), reference)
