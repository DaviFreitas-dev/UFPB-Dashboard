from modules.database import (
    append_record,
    delete_record,
    new_id,
    records,
    update_record,
)


def all_books():
    return records("Leitura")


def add(title, author, total_pages, daily_goal):
    append_record(
        "Leitura",
        [
            new_id(),
            title,
            author,
            0,
            int(total_pages),
            int(daily_goal),
            "Lendo",
        ],
    )


def update(book_id, page, status=None):
    changes = {"pagina_atual": int(page)}
    if status:
        changes["status"] = status
    update_record("Leitura", book_id, changes)


def remove(book_id):
    return delete_record("Leitura", book_id)


def remaining_today(book):
    try:
        goal = max(0, int(book.get("meta_diaria", 0)))
        current = max(0, int(book.get("pagina_atual", 0)))
        total = max(0, int(book.get("total_paginas", 0)))
    except (TypeError, ValueError):
        return 0

    if current >= total:
        return 0
    return min(goal, total - current)
