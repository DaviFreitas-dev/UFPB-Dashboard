import json

import pytest

from modules import sheets_credentials


def test_credentials_prefer_server_environment(monkeypatch):
    expected = {"client_email": "service@example.test", "private_key": "test-only"}
    monkeypatch.setenv("GSHEETS_SERVICE_ACCOUNT_JSON", json.dumps(expected))
    monkeypatch.setattr(
        sheets_credentials,
        "_streamlit_service_account_info",
        lambda: pytest.fail("Streamlit fallback must not run"),
    )

    assert sheets_credentials.load_service_account_info() == expected


def test_credentials_reject_invalid_server_json(monkeypatch):
    monkeypatch.setenv("GSHEETS_SERVICE_ACCOUNT_JSON", "not-json")

    with pytest.raises(RuntimeError, match="JSON válido"):
        sheets_credentials.load_service_account_info()


def test_credentials_fall_back_to_current_streamlit_section(monkeypatch):
    monkeypatch.delenv("GSHEETS_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.setattr(
        sheets_credentials,
        "_streamlit_service_account_info",
        lambda: {"client_email": "streamlit@example.test"},
    )

    assert sheets_credentials.load_service_account_info() == {
        "client_email": "streamlit@example.test"
    }
