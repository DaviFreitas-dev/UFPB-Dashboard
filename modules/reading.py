from modules.database import (
    append_record,
    delete_record,
    new_id,
    records,
    update_record,
)


MAX_READING_ITEM_ID_LENGTH = 512
_UNSAFE_READING_ITEM_IDS = {".", ".."}


class ReadingIdConflict(ValueError):
    pass


def is_safe_reading_item_id(value):
    item_id = str(value or "").strip()
    return (
        bool(item_id)
        and len(item_id) <= MAX_READING_ITEM_ID_LENGTH
        and item_id not in _UNSAFE_READING_ITEM_IDS
    )


def _integer(value, default=0):
    try:
        return int(float(value))
    except (OverflowError, TypeError, ValueError):
        return default


def _input_integer(value):
    try:
        parsed = int(value)
    except (OverflowError, TypeError, ValueError) as error:
        raise ValueError("Informe um número inteiro.") from error
    if isinstance(value, bool) or (isinstance(value, float) and value != parsed):
        raise ValueError("Informe um número inteiro.")
    return parsed


def _record_with_id(item_id):
    requested_id = str(item_id or "").strip()
    if not requested_id:
        return None
    return next(
        (
            row
            for row in records("Leitura")
            if str(row.get("id") or "").strip() == requested_id
        ),
        None,
    )


def _normalized_record(record):
    total = max(1, _integer(record.get("total_paginas"), 1))
    current = min(max(0, _integer(record.get("pagina_atual"))), total)
    status = str(record.get("status") or "").strip()
    if status not in {"Lendo", "Concluído"}:
        status = "Concluído" if current >= total else "Lendo"
    return {
        **record,
        "pagina_atual": current,
        "total_paginas": total,
        "meta_diaria": max(0, _integer(record.get("meta_diaria"))),
        "status": status,
    }


def all_books():
    return [_normalized_record(row) for row in records("Leitura")]


def add(title, author, total_pages, daily_goal, item_id=None):
    title_text = str(title or "").strip()
    author_text = str(author or "").strip()
    total = _input_integer(total_pages)
    goal = _input_integer(daily_goal)
    if not title_text:
        raise ValueError("O título é obrigatório.")
    if total <= 0:
        raise ValueError("O total de páginas deve ser positivo.")
    if goal <= 0:
        raise ValueError("A meta diária deve ser positiva.")

    record_id = str(item_id or new_id())
    expected = {
        "id": record_id,
        "titulo": title_text,
        "autor": author_text,
        "pagina_atual": 0,
        "total_paginas": total,
        "meta_diaria": goal,
        "status": "Lendo",
    }
    existing = _record_with_id(record_id)
    if existing is not None:
        comparable = {
            "id": str(existing.get("id") or ""),
            "titulo": str(existing.get("titulo") or ""),
            "autor": str(existing.get("autor") or ""),
            "total_paginas": _integer(existing.get("total_paginas")),
            "meta_diaria": _integer(existing.get("meta_diaria")),
        }
        requested = {
            key: expected[key]
            for key in comparable
        }
        if comparable == requested:
            return _normalized_record(existing), False
        raise ReadingIdConflict("O ID do livro já existe com outro conteúdo.")

    append_record(
        "Leitura",
        [
            expected[column]
            for column in (
                "id",
                "titulo",
                "autor",
                "pagina_atual",
                "total_paginas",
                "meta_diaria",
                "status",
            )
        ],
        value_input_option="RAW",
    )
    return expected, True


def set_progress(book_id, *, current_page=None, status=None):
    current = _record_with_id(book_id)
    if current is None:
        return None, False

    normalized = _normalized_record(current)
    total = normalized["total_paginas"]
    if current_page is None:
        target_page = normalized["pagina_atual"]
    else:
        target_page = _input_integer(current_page)
        if target_page < 0 or target_page > total:
            raise ValueError("A página atual deve ficar entre zero e o total.")

    if status is not None and status not in {"Lendo", "Concluído"}:
        raise ValueError("O status da leitura é inválido.")

    target_status = status or normalized["status"]
    if target_status == "Concluído" or (status is None and target_page == total):
        target_page = total
        target_status = "Concluído"

    changes = {}
    if target_page != normalized["pagina_atual"]:
        changes["pagina_atual"] = target_page
    if target_status != normalized["status"]:
        changes["status"] = target_status
    if not changes:
        return normalized, False

    if not update_record("Leitura", current["id"], changes):
        return None, False
    return {**normalized, **changes}, True


def update(book_id, page, status=None):
    set_progress(book_id, current_page=page, status=status)


def remove(book_id):
    current = _record_with_id(book_id)
    if current is None:
        return False
    return delete_record("Leitura", current["id"])


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
