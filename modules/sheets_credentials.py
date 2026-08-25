import json
import os


READ_ONLY_SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
)
READ_WRITE_SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
)


def _streamlit_service_account_info():
    import streamlit as st

    return dict(st.secrets["gsheets"])


def load_service_account_info() -> dict[str, object]:
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
        return _streamlit_service_account_info()
    except Exception as error:
        raise RuntimeError(
            "Configure GSHEETS_SERVICE_ACCOUNT_JSON ou a seção gsheets do Streamlit."
        ) from error
