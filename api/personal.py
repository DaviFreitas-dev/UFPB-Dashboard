from datetime import timedelta

from api.dashboard import (
    _completed,
    _date,
    _equals,
    _integer,
    _row_id,
    _rows,
    _text,
    _today,
    _user,
)
from api.sheets import read_dashboard_tables
from api.workspace_models import (
    ActivityCollection,
    HabitCollection,
    PersonalHabit,
    PersonalTask,
    PersonalWorkspace,
    PhysicalActivity,
    ReadingBook,
    ReadingCollection,
    TaskCollection,
)


MAX_HABIT_CONFIG_ID_LENGTH = 512


def _safe_habit_config_id(value):
    config_id = _text(value)
    return (
        bool(config_id)
        and len(config_id) <= MAX_HABIT_CONFIG_ID_LENGTH
        and config_id not in {".", ".."}
    )


def _habit_name_key(value):
    return " ".join(_text(value).split()).casefold()


def _tasks(tables, reference):
    items = []
    for index, row in enumerate(_rows(tables, "Tarefas")):
        if _date(row.get("data")) != reference:
            continue
        persisted_id = _text(row.get("id"))
        items.append(
            PersonalTask(
                id=persisted_id or _row_id(row, "task", index),
                title=_text(row.get("tarefa"), "Tarefa sem título"),
                category=_text(row.get("categoria"), "Outro"),
                completed=_completed(row.get("status")),
                mutable=bool(persisted_id),
            )
        )
    return TaskCollection(
        total=len(items),
        completed=sum(item.completed for item in items),
        items=items,
    )


def _habit_streak(rows, name, reference):
    completed_days = {
        day
        for row in rows
        if _habit_name_key(row.get("habito")) == _habit_name_key(name)
        and _completed(row.get("feito"))
        and (day := _date(row.get("data"))) is not None
    }
    if not completed_days:
        return 0
    cursor = reference if reference in completed_days else reference - timedelta(days=1)
    count = 0
    while cursor in completed_days:
        count += 1
        cursor -= timedelta(days=1)
    return count


def _habits(tables, reference):
    rows = _rows(tables, "Habitos")
    logs = {
        _habit_name_key(row.get("habito")): row
        for row in rows
        if _date(row.get("data")) == reference
    }
    items = []
    seen = set()
    for index, config in enumerate(_rows(tables, "HabitosConfig")):
        if not _equals(config.get("ativo"), "Sim"):
            continue
        name = _text(config.get("nome"))
        if not name or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        log = logs.get(_habit_name_key(name))
        config_id = _text(config.get("id"))
        items.append(
            PersonalHabit(
                config_id=config_id,
                log_id=_text(log.get("id")) if log and _text(log.get("id")) else None,
                title=name,
                completed=_completed(log.get("feito")) if log else False,
                streak_days=_habit_streak(rows, name, reference),
                mutable=_safe_habit_config_id(config_id),
            )
        )
    return HabitCollection(
        total=len(items),
        completed=sum(item.completed for item in items),
        items=items,
    )


def _reading(tables):
    items = []
    for index, row in enumerate(_rows(tables, "Leitura")):
        current = max(0, _integer(row.get("pagina_atual")))
        total = max(1, _integer(row.get("total_paginas"), 1))
        current = min(current, total)
        target = max(0, _integer(row.get("meta_diaria")))
        items.append(
            ReadingBook(
                id=_row_id(row, "book", index),
                title=_text(row.get("titulo"), "Livro sem título"),
                author=_text(row.get("autor"), "Autor não informado"),
                current_page=current,
                total_pages=total,
                daily_target=target,
                remaining_target=min(target, max(total - current, 0)),
                status=_text(row.get("status"), "Lendo"),
                progress=current / total,
            )
        )
    return ReadingCollection(items=items)


def _activity(tables, reference):
    items = []
    for index, row in enumerate(_rows(tables, "Atividade")):
        if _date(row.get("data")) != reference:
            continue
        activity_type = _text(row.get("tipo"))
        if not activity_type:
            continue
        items.append(
            PhysicalActivity(
                id=_row_id(row, "activity", index),
                type=activity_type,
                completed=_completed(row.get("feito")),
            )
        )
    return ActivityCollection(items=items)


def build_personal_workspace(tables, reference=None):
    reference = reference or _today()
    return PersonalWorkspace(
        date=str(reference),
        user=_user(tables, reference),
        tasks=_tasks(tables, reference),
        habits=_habits(tables, reference),
        reading=_reading(tables),
        activity=_activity(tables, reference),
    )


def load_personal_workspace(reference=None):
    return build_personal_workspace(read_dashboard_tables(), reference)
