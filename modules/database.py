import json
import uuid
from datetime import date

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

from modules.config import CICLO_PADRAO, SHEETS, XP_POR_HORA


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
    client = gspread.authorize(creds)
    return client.open("Banco_UFPB")


@st.cache_resource
def get_worksheet(name):
    book = connect_sheet()
    try:
        return book.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = book.add_worksheet(
            title=name,
            rows=1000,
            cols=max(10, len(SHEETS[name]) + 2),
        )
        ws.update([SHEETS[name]])
        return ws


@st.cache_resource
def initialize_database():
    for name in SHEETS:
        get_worksheet(name)
    migrate_legacy_data()
    ensure_defaults()
    return True


def records(name):
    try:
        return get_worksheet(name).get_all_records() or []
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


def append_record(name, values):
    get_worksheet(name).append_row(
        values,
        value_input_option="USER_ENTERED",
    )


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
    for field, value in updates.items():
        if field in SHEETS[name]:
            ws.update_cell(
                row_number,
                SHEETS[name].index(field) + 1,
                value,
            )
    return True


def delete_record(name, record_id):
    row_number = _find_record_row(name, record_id)
    if row_number is None:
        return False
    get_worksheet(name).delete_rows(row_number)
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
    found = False
    for row in rows:
        if str(row.get("chave")) == key:
            row["valor"] = str(value)
            found = True
            break
    if not found:
        rows.append({"chave": key, "valor": str(value)})
    replace_records(
        "Usuario",
        [[row["chave"], row["valor"]] for row in rows],
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
        first_sheet = book.worksheets()[0]
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
    found = False

    for row in rows:
        if row["data"] == today:
            row["horas"] = int(row["horas"]) + int(hours)
            row["xp"] = int(row["xp"]) + int(xp)
            found = True
            break

    if not found:
        rows.append(
            {
                "data": today,
                "horas": int(hours),
                "xp": int(xp),
            }
        )

    replace_records(
        "Historico",
        [
            [row["data"], row["horas"], row["xp"]]
            for row in rows
        ],
    )


def get_history():
    return records("Historico")


def update_user_config(rows):
    replace_records("Config", rows)
    reset_cycle()


def reset_progress():
    set_xp(0)
    replace_records("Historico", [])
    reset_cycle()
