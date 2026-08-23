from datetime import date

from modules.database import (
    append_record,
    delete_record,
    new_id,
    records,
    update_record,
)
from modules.gamification import award_xp_once


class TaskIdConflict(ValueError):
    pass


def records_for_date(target_date):
    target = str(target_date)
    return [
        row
        for row in records("Tarefas")
        if str(row.get("data")) == target
    ]


def today_records():
    return records_for_date(date.today())


def add(task, category, target_date=None, item_id=None):
    target = target_date or date.today()
    task_text = str(task).strip()
    category_text = str(category).strip()
    if not task_text or not category_text:
        raise ValueError("Tarefa e categoria são obrigatórias.")

    record_id = str(item_id or new_id())
    expected = {
        "id": record_id,
        "data": str(target),
        "tarefa": task_text,
        "categoria": category_text,
        "status": "Pendente",
    }
    existing = next(
        (row for row in records("Tarefas") if str(row.get("id")) == record_id),
        None,
    )
    if existing is not None:
        immutable_fields = ("id", "data", "tarefa", "categoria")
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
        raise TaskIdConflict("O ID da tarefa já existe com outro conteúdo.")

    append_record(
        "Tarefas",
        [
            expected[column]
            for column in ("id", "data", "tarefa", "categoria", "status")
        ],
    )
    return expected, True


def toggle(item_id, done):
    updated = update_record(
        "Tarefas",
        item_id,
        {"status": "Concluída" if done else "Pendente"},
    )

    if updated and done:
        award_xp_once(
            f"task:{item_id}",
            15,
            "tarefa",
            "Tarefa concluída",
        )


def remove(item_id):
    return delete_record("Tarefas", item_id)
