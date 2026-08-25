"""Planeja e aplica IDs legados a partir de um plano revisável e imutável."""

import uuid
from uuid import UUID

from modules.config import SHEETS
from modules.database import get_existing_worksheet, write_values_batch


ID_SHEETS = tuple(name for name, columns in SHEETS.items() if "id" in columns)
PLAN_SCHEMA = "nexo-id-backfill-plan"
PLAN_VERSION = 1


def _column_name(column_number):
    label = ""
    current = column_number
    while current:
        current, remainder = divmod(current - 1, 26)
        label = chr(65 + remainder) + label
    return label


def _normalized_rows(rows):
    return [] if rows == [[]] else rows


def _require_expected_header(name, rows):
    normalized = _normalized_rows(rows)
    header = [str(value).strip() for value in normalized[0]] if normalized else []
    if header != SHEETS[name]:
        raise RuntimeError(f"A aba '{name}' não possui o cabeçalho esperado.")
    return normalized, header


def collect_missing_id_updates(name, rows, id_factory=None):
    """Retorna atualizações pontuais para IDs vazios, preservando linhas existentes."""
    normalized, header = _require_expected_header(name, rows)
    id_column = header.index("id")
    id_cell_column = _column_name(id_column + 1)
    make_id = id_factory or (lambda: str(uuid.uuid4()))
    updates = []
    for row_number, row in enumerate(normalized[1:], start=2):
        has_content = any(str(value).strip() for value in row)
        current_id = row[id_column] if id_column < len(row) else ""
        if has_content and not str(current_id).strip():
            updates.append(
                {
                    "sheet": name,
                    "range": f"{id_cell_column}{row_number}",
                    "values": [[make_id()]],
                }
            )
    return updates


def build_backfill_plan(id_factory=None):
    """Lê abas sem criar schema e devolve o plano completo de dry-run."""
    worksheets = []
    for name in ID_SHEETS:
        worksheet = get_existing_worksheet(name)
        if worksheet is None:
            worksheets.append(
                {
                    "worksheet": name,
                    "state": "missing",
                    "expected_header": list(SHEETS[name]),
                    "updates": [],
                }
            )
            continue

        rows = worksheet.get(pad_values=True)
        updates = collect_missing_id_updates(name, rows, id_factory=id_factory)
        worksheets.append(
            {
                "worksheet": name,
                "state": "present",
                "expected_header": list(SHEETS[name]),
                "updates": [
                    {
                        "cell": update["range"],
                        "row": int("".join(filter(str.isdigit, update["range"]))),
                        "uuid": update["values"][0][0],
                    }
                    for update in updates
                ],
            }
        )

    plan = {
        "schema": PLAN_SCHEMA,
        "version": PLAN_VERSION,
        "worksheets": worksheets,
    }
    validate_backfill_plan(plan)
    return plan


def _invalid_plan(reason):
    raise ValueError(f"plano inválido: {reason}")


def validate_backfill_plan(plan):
    """Valida estritamente o formato seguro antes de qualquer acesso de escrita."""
    if not isinstance(plan, dict):
        _invalid_plan("a raiz precisa ser um objeto")
    if set(plan) != {"schema", "version", "worksheets"}:
        _invalid_plan("campos superiores inesperados ou ausentes")
    if plan["schema"] != PLAN_SCHEMA or plan["version"] != PLAN_VERSION:
        _invalid_plan("schema ou versão incompatível")

    worksheets = plan["worksheets"]
    if not isinstance(worksheets, list):
        _invalid_plan("worksheets precisa ser uma lista")
    names = [
        entry.get("worksheet") if isinstance(entry, dict) else None
        for entry in worksheets
    ]
    if names != list(ID_SHEETS):
        _invalid_plan("a lista de abas não corresponde ao schema atual")

    seen_uuids = set()
    for entry in worksheets:
        if set(entry) != {
            "worksheet",
            "state",
            "expected_header",
            "updates",
        }:
            _invalid_plan("uma aba contém campos inesperados ou ausentes")

        name = entry["worksheet"]
        if entry["expected_header"] != list(SHEETS[name]):
            _invalid_plan(f"cabeçalho inesperado para {name}")
        if entry["state"] not in {"present", "missing"}:
            _invalid_plan(f"estado inesperado para {name}")
        updates = entry["updates"]
        if not isinstance(updates, list):
            _invalid_plan(f"updates de {name} precisa ser uma lista")
        if entry["state"] == "missing" and updates:
            _invalid_plan(f"aba ausente {name} não pode conter atualizações")

        id_column = SHEETS[name].index("id") + 1
        cell_column = _column_name(id_column)
        seen_cells = set()
        for update in updates:
            if not isinstance(update, dict) or set(update) != {"cell", "row", "uuid"}:
                _invalid_plan(f"atualização inesperada em {name}")
            row = update["row"]
            if type(row) is not int or row < 2:
                _invalid_plan(f"linha inválida em {name}")
            expected_cell = f"{cell_column}{row}"
            if update["cell"] != expected_cell or expected_cell in seen_cells:
                _invalid_plan(f"célula inválida ou duplicada em {name}")
            seen_cells.add(expected_cell)

            value = update["uuid"]
            try:
                parsed_uuid = UUID(value)
            except (AttributeError, TypeError, ValueError):
                _invalid_plan(f"UUID inválido em {name}")
            if parsed_uuid.version != 4 or str(parsed_uuid) != value:
                _invalid_plan(f"UUID não canônico ou não-v4 em {name}")
            if value in seen_uuids:
                _invalid_plan("UUID duplicado")
            seen_uuids.add(value)

    return plan


def _stale_plan(reason):
    raise RuntimeError(
        f"O plano ficou desatualizado ({reason}). Nenhuma alteração foi realizada."
    )


def apply_backfill_plan(plan):
    """Revalida todas as precondições e aplica exatamente o plano revisado."""
    validate_backfill_plan(plan)
    batch_updates = []
    counts = {}

    for entry in plan["worksheets"]:
        name = entry["worksheet"]
        worksheet = get_existing_worksheet(name)
        counts[name] = len(entry["updates"])

        if entry["state"] == "missing":
            if worksheet is not None:
                _stale_plan(f"a aba '{name}' passou a existir")
            continue

        if worksheet is None:
            _stale_plan(f"a aba '{name}' não existe mais")

        try:
            rows, _header = _require_expected_header(
                name,
                worksheet.get(pad_values=True),
            )
        except RuntimeError as error:
            _stale_plan(str(error))
        if [str(value).strip() for value in rows[0]] != entry["expected_header"]:
            _stale_plan(f"o cabeçalho da aba '{name}' mudou")

        id_column = SHEETS[name].index("id")
        for update in entry["updates"]:
            row_index = update["row"] - 1
            if row_index >= len(rows):
                _stale_plan(f"a linha {update['row']} da aba '{name}' não existe mais")
            row = rows[row_index]
            current_id = row[id_column] if id_column < len(row) else ""
            if str(current_id).strip():
                _stale_plan(f"a célula {update['cell']} da aba '{name}' não está vazia")
            if not any(str(value).strip() for value in row):
                _stale_plan(f"a linha {update['row']} da aba '{name}' ficou vazia")
            batch_updates.append(
                {
                    "sheet": name,
                    "range": update["cell"],
                    "values": [[update["uuid"]]],
                }
            )

    if batch_updates:
        write_values_batch(batch_updates)
    return counts
