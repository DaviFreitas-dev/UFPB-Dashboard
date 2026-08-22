import copy
import json
import os
import threading
import time
from functools import lru_cache

import gspread
from google.oauth2.service_account import Credentials
from gspread.http_client import BackOffHTTPClient

from modules.config import SHEETS


DASHBOARD_SHEETS = (
    "Usuario",
    "Historico",
    "Questoes",
    "SessoesEstudo",
    "Revisoes",
    "AgendaSemanal",
    "AgendaCheckins",
    "Avaliacoes",
    "Metas",
    "Planejamento",
    "Rotina",
    "Tarefas",
    "Leitura",
    "HabitosConfig",
    "Habitos",
    "Atividade",
)

_READ_ONLY_SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
)
_CACHE_SECONDS = 15
_CACHE_LOCK = threading.RLock()
_CACHE_VALUE = None
_CACHE_EXPIRES_AT = 0.0


def _service_account_info():
    raw = os.getenv("GSHEETS_SERVICE_ACCOUNT_JSON", "").strip()
    if raw:
        try:
            info = json.loads(raw)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                "GSHEETS_SERVICE_ACCOUNT_JSON não contém um JSON válido."
            ) from error
        if not isinstance(info, dict):
            raise RuntimeError(
                "GSHEETS_SERVICE_ACCOUNT_JSON precisa conter um objeto JSON."
            )
        return info

    try:
        import streamlit as st

        return dict(st.secrets["gsheets"])
    except Exception as error:
        raise RuntimeError(
            "Configure GSHEETS_SERVICE_ACCOUNT_JSON no servidor da API."
        ) from error


@lru_cache(maxsize=1)
def _open_workbook():
    credentials = Credentials.from_service_account_info(
        _service_account_info(),
        scopes=_READ_ONLY_SCOPES,
    )
    client = gspread.authorize(
        credentials,
        http_client=BackOffHTTPClient,
    )
    return client.open("Banco_UFPB")


def _column_name(index):
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _sheet_range(name):
    escaped = name.replace("'", "''")
    last_column = _column_name(len(SHEETS[name]))
    return f"'{escaped}'!A:{last_column}"


def _records_from_range(name, value_range):
    values = value_range.get("values", [])
    if not values:
        return []

    header = [str(value).strip() for value in values[0]]
    if not any(column in SHEETS[name] for column in header):
        raise RuntimeError(f"A aba '{name}' não possui um cabeçalho reconhecido.")

    rows = []
    for values_row in values[1:]:
        if not any(str(value).strip() for value in values_row):
            continue
        rows.append(
            {
                column: values_row[index] if index < len(values_row) else ""
                for index, column in enumerate(header)
                if column
            }
        )
    return rows


def clear_dashboard_cache():
    global _CACHE_VALUE, _CACHE_EXPIRES_AT

    with _CACHE_LOCK:
        _CACHE_VALUE = None
        _CACHE_EXPIRES_AT = 0.0


def read_dashboard_tables():
    global _CACHE_VALUE, _CACHE_EXPIRES_AT

    now = time.monotonic()
    with _CACHE_LOCK:
        if _CACHE_VALUE is not None and now < _CACHE_EXPIRES_AT:
            return copy.deepcopy(_CACHE_VALUE)

        response = _open_workbook().values_batch_get(
            [_sheet_range(name) for name in DASHBOARD_SHEETS]
        )
        value_ranges = response.get("valueRanges", [])
        if len(value_ranges) != len(DASHBOARD_SHEETS):
            raise RuntimeError(
                "O Google Sheets retornou um lote incompleto para o painel."
            )

        tables = {
            name: _records_from_range(name, value_range)
            for name, value_range in zip(DASHBOARD_SHEETS, value_ranges)
        }
        _CACHE_VALUE = tables
        _CACHE_EXPIRES_AT = now + _CACHE_SECONDS
        return copy.deepcopy(tables)
