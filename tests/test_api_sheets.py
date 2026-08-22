from api import sheets
from modules.config import SHEETS


class FakeWorkbook:
    def __init__(self):
        self.calls = []

    def values_batch_get(self, ranges):
        self.calls.append(ranges)
        value_ranges = []
        for name in sheets.DASHBOARD_SHEETS:
            values = [SHEETS[name]]
            if name == "Usuario":
                values.append(["xp", "250"])
            value_ranges.append({"values": values})
        return {"valueRanges": value_ranges}


def test_api_uses_only_read_scopes():
    assert sheets._READ_ONLY_SCOPES
    assert all(scope.endswith(".readonly") for scope in sheets._READ_ONLY_SCOPES)


def test_dashboard_tables_use_one_cached_batch(monkeypatch):
    workbook = FakeWorkbook()
    monkeypatch.setattr(sheets, "_open_workbook", lambda: workbook)
    sheets.clear_dashboard_cache()

    first = sheets.read_dashboard_tables()
    first["Usuario"][0]["valor"] = "alterado"
    second = sheets.read_dashboard_tables()

    assert len(workbook.calls) == 1
    assert len(workbook.calls[0]) == len(sheets.DASHBOARD_SHEETS)
    assert second["Usuario"] == [{"chave": "xp", "valor": "250"}]

    sheets.clear_dashboard_cache()
