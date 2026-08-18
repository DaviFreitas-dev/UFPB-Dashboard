import json
import uuid

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

from modules.config import (
    AMBIENTES,
    CICLO_PADRAO,
    SHEETS,
    XP_POR_HORA,
)


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


def get_worksheet(name):
    book = connect_sheet()
    try:
        ws = book.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = book.add_worksheet(
            title=name,
            rows=1000,
            cols=max(10, len(SHEETS[name]) + 2),
        )
    if not ws.get_all_values():
        ws.update([SHEETS[name]])
    return ws


def initialize_database():
    for name in SHEETS:
        get_worksheet(name)
    migrate_legacy_data()


def records(name):
    values = get_worksheet(name).get_all_records()
    return values or []


def replace_records(name, rows):
    ws = get_worksheet(name)
    ws.clear()
    ws.update([SHEETS[name]] + rows)


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
        first = book.worksheets()[0]
        raw = first.acell("A1").value
        legacy = json.loads(raw) if raw else {}
    except Exception:
        legacy = {}

    if not isinstance(legacy, dict) or "xp" not in legacy:
        set_user("schema_version", "2")
        ensure_defaults()
        return

    set_user("xp", legacy.get("xp", 0))

    config = legacy.get("config_base", CICLO_PADRAO)
    cycle = legacy.get(
        "ciclo_atual",
        {mat: info["horas"] for mat, info in config.items()},
    )
    history = legacy.get("historico_dias", {})

    replace_records(
        "Config",
        [[mat, info["horas"], info["ambiente"]] for mat, info in config.items()],
    )

    replace_records(
        "Ciclo",
        [[mat, horas] for mat, horas in cycle.items()],
    )

    replace_records(
        "Historico",
        [[day, hours, int(hours) * XP_POR_HORA] for day, hours in history.items()],
    )

    set_user("schema_version", "2")
    ensure_defaults()


def ensure_defaults():
    if not records("Config"):
        replace_records(
            "Config",
            [[mat, info["horas"], info["ambiente"]] for mat, info in CICLO_PADRAO.items()],
        )

    if not records("Ciclo"):
        replace_records(
            "Ciclo",
            [[row["disciplina"], int(row["horas"])] for row in records("Config")],
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
    replace_records(
        "Ciclo",
        [[row["disciplina"], int(row["horas"])] for row in get_config()],
    )


def update_cycle(values):
    replace_records(
        "Ciclo",
        [[row["disciplina"], int(row["restantes"])] for row in values],
    )


def add_history(hours, xp):
    from datetime import date

    today = str(date.today())
    rows = records("Historico")
    found = False

    for row in rows:
        if row["data"] == today:
            row["horas"] = int(row["horas"]) + hours
            row["xp"] = int(row["xp"]) + xp
            found = True
            break

    if not found:
        rows.append({"data": today, "horas": hours, "xp": xp})

    replace_records(
        "Historico",
        [[row["data"], row["horas"], row["xp"]] for row in rows],
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
