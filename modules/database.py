import json
import re
import uuid
from datetime import date

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials
from gspread.http_client import BackOffHTTPClient
from gspread.utils import numericise_all, to_records

from modules.config import CICLO_PADRAO, SHEETS, XP_POR_HORA


class SheetSchemaError(RuntimeError):
    """Raised when an existing worksheet has an unexpected header."""


_HEADER_NOT_PROVIDED = object()


@st.cache_resource
def connect_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gsheets"]),
        scopes=scopes,
    )
    client = gspread.authorize(creds, http_client=BackOffHTTPClient)
    return client.open("Banco_UFPB")


@st.cache_resource
def _worksheets_by_name():
    return {ws.title: ws for ws in connect_sheet().worksheets()}


@st.cache_resource
def get_worksheet(name):
    worksheets = _worksheets_by_name()
    ws = worksheets.get(name)

    if ws is None:
        book = connect_sheet()
        ws = book.add_worksheet(
            title=name,
            rows=1000,
            cols=max(10, len(SHEETS[name]) + 2),
        )
        ws.update([SHEETS[name]])
        worksheets[name] = ws

    return ws


def _ensure_header(name, ws, current=_HEADER_NOT_PROVIDED):
    expected = SHEETS[name]
    if current is _HEADER_NOT_PROVIDED:
        current = ws.row_values(1)

    if current == expected:
        return

    if not current:
        ws.update([expected])
        return

    missing = [column for column in expected if column not in current]
    unexpected = [column for column in current if column not in expected]

    details = []
    if missing:
        details.append(f"colunas ausentes: {', '.join(missing)}")
    if unexpected:
        details.append(f"colunas inesperadas: {', '.join(unexpected)}")
    if not details:
        details.append("ordem das colunas diferente do schema esperado")

    raise SheetSchemaError(
        f"A aba '{name}' possui um cabeçalho incompatível "
        f"({'; '.join(details)}). Nenhuma alteração foi realizada. "
        "Faça uma cópia da planilha antes de executar uma migração explícita."
    )


def _read_headers(book, names):
    ranges = []
    for name in names:
        escaped_name = name.replace("'", "''")
        ranges.append(f"'{escaped_name}'!1:1")
    response = book.values_batch_get(ranges)
    value_ranges = response.get("valueRanges", [])

    if len(value_ranges) != len(names):
        raise RuntimeError("A API do Google Sheets retornou cabeçalhos incompletos.")

    headers = {}
    for name, value_range in zip(names, value_ranges):
        values = value_range.get("values", [])
        headers[name] = values[0] if values else []
    return headers


@st.cache_data(ttl=15, show_spinner=False)
def _records_cached(name):
    ws = get_worksheet(name)
    entire_sheet = ws.get(pad_values=True)

    if entire_sheet == [[]]:
        entire_sheet = []

    current = entire_sheet[0] if entire_sheet else []
    _ensure_header(name, ws, current=current)
    if not entire_sheet:
        return []

    values = [
        numericise_all(row, False, "", False, [])
        for row in entire_sheet[1:]
    ]
    return to_records(current, values)


def clear_records_cache(name=None):
    if name is None:
        _records_cached.clear()
    else:
        _records_cached.clear(name)


@st.cache_resource
def initialize_database():
    names = list(SHEETS)
    worksheets = {name: get_worksheet(name) for name in names}
    headers = _read_headers(connect_sheet(), names)

    for name, ws in worksheets.items():
        _ensure_header(name, ws, current=headers[name])

    clear_records_cache()
    migrate_legacy_data()
    ensure_defaults()
    return True


def records(name):
    try:
        return [dict(row) for row in _records_cached(name)]
    except gspread.exceptions.APIError as error:
        st.error(f"Erro ao acessar a aba '{name}' do Google Sheets.")
        raise error


def replace_records(name, rows):
    ws = get_worksheet(name)
    header = SHEETS[name]
    ws.clear()
    ws.update(
        [header] + rows if rows else [header],
        value_input_option="USER_ENTERED",
    )
    clear_records_cache(name)


def append_record(name, values):
    get_worksheet(name).append_row(
        values,
        value_input_option="USER_ENTERED",
    )
    clear_records_cache(name)


def write_values_batch(updates):
    """Write multiple ranges atomically and invalidate only affected caches."""
    if not updates:
        return

    data = []
    names = []
    for update in updates:
        name = update["sheet"]
        if name not in SHEETS:
            raise KeyError(f"Aba desconhecida: {name}")
        escaped_name = name.replace("'", "''")
        data.append(
            {
                "range": f"'{escaped_name}'!{update['range']}",
                "majorDimension": "ROWS",
                "values": update["values"],
            }
        )
        names.append(name)

    required_rows = {}
    for update in updates:
        row_numbers = [
            int(value)
            for value in re.findall(r"[A-Za-z]+(\d+)", update["range"])
        ]
        if row_numbers:
            name = update["sheet"]
            required_rows[name] = max(
                required_rows.get(name, 0),
                max(row_numbers),
            )

    for name, required in required_rows.items():
        worksheet = get_worksheet(name)
        current = int(worksheet.row_count)
        if required > current:
            worksheet.add_rows(required - current)

    connect_sheet().values_batch_update(
        {
            "valueInputOption": "USER_ENTERED",
            "data": data,
        }
    )

    for name in dict.fromkeys(names):
        clear_records_cache(name)


def _find_record_row(name, record_id):
    rows = records(name)
    if not rows or "id" not in SHEETS[name]:
        return None

    return next(
        (
            index
            for index, row in enumerate(rows, start=2)
            if str(row.get("id")) == str(record_id)
        ),
        None,
    )


def update_record(name, record_id, updates):
    row_number = _find_record_row(name, record_id)
    if row_number is None:
        return False

    ws = get_worksheet(name)
    cells = []

    for field, value in updates.items():
        if field in SHEETS[name]:
            cells.append(
                gspread.Cell(
                    row_number,
                    SHEETS[name].index(field) + 1,
                    value,
                )
            )

    if cells:
        ws.update_cells(cells, value_input_option="USER_ENTERED")
        clear_records_cache(name)

    return True


def delete_record(name, record_id):
    row_number = _find_record_row(name, record_id)
    if row_number is None:
        return False

    get_worksheet(name).delete_rows(row_number)
    clear_records_cache(name)
    return True


def new_id():
    return uuid.uuid4().hex[:10]


def get_user(key, default=None):
    for row in records("Usuario"):
        if str(row.get("chave")) == key:
            return row.get("valor", default)
    return default


def set_user(key, value):
    rows = records("Usuario")
    for row_number, row in enumerate(rows, start=2):
        if str(row.get("chave")) == key:
            write_values_batch(
                [
                    {
                        "sheet": "Usuario",
                        "range": f"B{row_number}",
                        "values": [[str(value)]],
                    }
                ]
            )
            return

    row_number = len(rows) + 2
    write_values_batch(
        [
            {
                "sheet": "Usuario",
                "range": f"A{row_number}:B{row_number}",
                "values": [[key, str(value)]],
            }
        ]
    )


def get_xp():
    try:
        return max(0, int(get_user("xp", 0)))
    except (TypeError, ValueError):
        return 0


def set_xp(value):
    set_user("xp", max(0, int(value)))


def migrate_legacy_data():
    if get_user("schema_version"):
        return

    book = connect_sheet()

    try:
        first_sheet = next(iter(_worksheets_by_name().values()))
        raw = first_sheet.acell("A1").value
        legacy = json.loads(raw) if raw else {}
    except Exception:
        legacy = {}

    if not isinstance(legacy, dict) or "xp" not in legacy:
        set_user("schema_version", "2")
        return

    set_user("xp", legacy.get("xp", 0))
    config = legacy.get("config_base", CICLO_PADRAO)
    cycle = legacy.get(
        "ciclo_atual",
        {subject: info["horas"] for subject, info in config.items()},
    )
    history = legacy.get("historico_dias", {})

    replace_records(
        "Config",
        [
            [subject, info["horas"], info["ambiente"]]
            for subject, info in config.items()
        ],
    )
    replace_records(
        "Ciclo",
        [[subject, hours] for subject, hours in cycle.items()],
    )
    replace_records(
        "Historico",
        [
            [day, hours, int(hours) * XP_POR_HORA]
            for day, hours in history.items()
        ],
    )
    set_user("schema_version", "2")


def ensure_defaults():
    if not records("Config"):
        replace_records(
            "Config",
            [
                [subject, info["horas"], info["ambiente"]]
                for subject, info in CICLO_PADRAO.items()
            ],
        )

    if not records("Ciclo"):
        config = records("Config")
        replace_records(
            "Ciclo",
            [
                [row["disciplina"], int(row["horas"])]
                for row in config
            ],
        )


def get_config():
    rows = records("Config")

    if not rows:
        ensure_defaults()
        rows = records("Config")

    return rows


def get_cycle():
    rows = records("Ciclo")

    if not rows:
        reset_cycle()
        rows = records("Ciclo")

    return rows


def reset_cycle():
    config = get_config()
    replace_records(
        "Ciclo",
        [
            [row["disciplina"], int(row["horas"])]
            for row in config
        ],
    )


def update_cycle(values):
    replace_records(
        "Ciclo",
        [
            [row["disciplina"], int(row["restantes"])]
            for row in values
        ],
    )


def add_history(hours, xp):
    today = str(date.today())
    rows = records("Historico")
    for row_number, row in enumerate(rows, start=2):
        if str(row.get("data")) == today:
            try:
                current_hours = int(row.get("horas", 0) or 0)
            except (TypeError, ValueError):
                current_hours = 0
            try:
                current_xp = int(row.get("xp", 0) or 0)
            except (TypeError, ValueError):
                current_xp = 0

            write_values_batch(
                [
                    {
                        "sheet": "Historico",
                        "range": f"A{row_number}:C{row_number}",
                        "values": [
                            [
                                today,
                                current_hours + int(hours),
                                current_xp + int(xp),
                            ]
                        ],
                    }
                ]
            )
            return

    row_number = len(rows) + 2
    write_values_batch(
        [
            {
                "sheet": "Historico",
                "range": f"A{row_number}:C{row_number}",
                "values": [[today, int(hours), int(xp)]],
            }
        ]
    )


def get_history():
    return records("Historico")


def update_user_config(rows):
    replace_records("Config", rows)
    reset_cycle()


def reset_progress():
    set_xp(0)
    replace_records("Historico", [])
    replace_records("XPEventos", [])
    reset_cycle()
