from modules.database import append_record, new_id, records, update_record


def all_books():
    return records("Leitura")


def add(title, author, total_pages, daily_goal):
    append_record(
        "Leitura",
        [new_id(), title, author, 0, int(total_pages), int(daily_goal), "Lendo"],
    )


def update(book_id, page, status=None):
    changes = {"pagina_atual": int(page)}
    if status:
        changes["status"] = status
    update_record("Leitura", book_id, changes)
