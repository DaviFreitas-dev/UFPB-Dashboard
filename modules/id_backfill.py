"""Planeja e aplica, somente por opt-in, IDs ausentes em dados legados."""

import uuid

from modules.config import SHEETS
from modules.database import get_existing_worksheet, write_values_batch


ID_SHEETS = tuple(name for name, columns in SHEETS.items() if "id" in columns)


def collect_missing_id_updates(name, rows, id_factory=None):
    """Retorna atualizações pontuais para IDs vazios, preservando linhas existentes."""
    if not rows:
        return []

    header = [str(value).strip() for value in rows[0]]
    if header != SHEETS[name]:
        raise RuntimeError(f"A aba '{name}' não possui o cabeçalho esperado.")

    id_column = header.index("id")
    make_id = id_factory or (lambda: str(uuid.uuid4()))
    updates = []
    for row_number, row in enumerate(rows[1:], start=2):
        has_content = any(str(value).strip() for value in row)
        current_id = row[id_column] if id_column < len(row) else ""
        if has_content and not str(current_id).strip():
            updates.append(
                {
                    "sheet": name,
                    "range": f"A{row_number}",
                    "values": [[make_id()]],
                }
            )
    return updates


def backfill_missing_ids(apply=False):
    """Conta IDs legados ausentes; grava somente quando ``apply`` é verdadeiro."""
    updates = []
    counts = {}
    for name in ID_SHEETS:
        worksheet = get_existing_worksheet(name)
        rows = worksheet.get(pad_values=True) if worksheet is not None else []
        sheet_updates = collect_missing_id_updates(name, rows)
        updates.extend(sheet_updates)
        counts[name] = len(sheet_updates)

    if apply and updates:
        write_values_batch(updates)
    return counts
