from datetime import date

import pytest

from modules import database
from modules.config import SHEETS
from modules.database import SheetSchemaError, _ensure_header, _read_headers


class FakeWorksheet:
    def __init__(self, header):
        self.header = list(header)
        self.updates = []
        self.insertions = []

    def row_values(self, row_number):
        assert row_number == 1
        return list(self.header)

    def update(self, values):
        self.updates.append(values)

    def insert_row(self, values, row_number):
        self.insertions.append((values, row_number))


def test_empty_worksheet_receives_expected_header():
    worksheet = FakeWorksheet([])

    _ensure_header("Atividade", worksheet)

    assert worksheet.updates == [[SHEETS["Atividade"]]]
    assert worksheet.insertions == []


def test_matching_header_is_left_untouched():
    worksheet = FakeWorksheet(SHEETS["Atividade"])

    _ensure_header("Atividade", worksheet)

    assert worksheet.updates == []
    assert worksheet.insertions == []


def test_legacy_header_is_not_shifted_or_rewritten():
    worksheet = FakeWorksheet(["data", "tipo", "feito"])

    with pytest.raises(SheetSchemaError, match="Nenhuma alteração foi realizada"):
        _ensure_header("Atividade", worksheet)

    assert worksheet.updates == []
    assert worksheet.insertions == []


def test_reordered_header_requires_explicit_migration():
    worksheet = FakeWorksheet(["data", "id", "tipo", "feito"])

    with pytest.raises(SheetSchemaError, match="ordem das colunas"):
        _ensure_header("Atividade", worksheet)

    assert worksheet.updates == []
    assert worksheet.insertions == []


def test_headers_are_read_in_one_batch_request():
    names = ["Usuario", "Ciclo"]

    class FakeBook:
        def __init__(self):
            self.calls = []

        def values_batch_get(self, ranges):
            self.calls.append(ranges)
            return {
                "valueRanges": [
                    {"values": [SHEETS[name]]}
                    for name in names
                ]
            }

    book = FakeBook()

    assert _read_headers(book, names) == {
        name: SHEETS[name] for name in names
    }
    assert len(book.calls) == 1
    assert book.calls[0] == ["'Usuario'!1:1", "'Ciclo'!1:1"]


def test_records_use_one_sheet_read_and_validate_its_header(monkeypatch):
    class ReadWorksheet:
        def __init__(self):
            self.get_calls = []
            self.updates = []

        def get(self, **kwargs):
            self.get_calls.append(kwargs)
            return [
                SHEETS["Atividade"],
                ["activity-1", "2026-08-19", "Corrida", "TRUE"],
            ]

        def update(self, values):
            self.updates.append(values)

    worksheet = ReadWorksheet()
    monkeypatch.setattr(database, "get_worksheet", lambda _name: worksheet)
    database._records_cached.clear()

    result = database._records_cached("Atividade")

    assert result == [
        {
            "id": "activity-1",
            "data": "2026-08-19",
            "tipo": "Corrida",
            "feito": "TRUE",
        }
    ]
    assert worksheet.get_calls == [{"pad_values": True}]
    assert worksheet.updates == []
    database._records_cached.clear()


def test_batch_writer_uses_one_request_and_clears_targeted_caches(monkeypatch):
    class FakeBook:
        def __init__(self):
            self.bodies = []

        def values_batch_update(self, body):
            self.bodies.append(body)

    book = FakeBook()
    cleared = []
    monkeypatch.setattr(database, "connect_sheet", lambda: book)
    monkeypatch.setattr(
        database,
        "get_worksheet",
        lambda _name: type(
            "Worksheet",
            (),
            {"row_count": 1000, "add_rows": lambda self, _amount: None},
        )(),
    )
    monkeypatch.setattr(
        database,
        "clear_records_cache",
        lambda name=None: cleared.append(name),
    )

    database.write_values_batch(
        [
            {"sheet": "Ciclo", "range": "B2", "values": [[2]]},
            {"sheet": "Usuario", "range": "B2", "values": [["300"]]},
        ]
    )

    assert len(book.bodies) == 1
    assert book.bodies[0]["valueInputOption"] == "USER_ENTERED"
    assert [item["range"] for item in book.bodies[0]["data"]] == [
        "'Ciclo'!B2",
        "'Usuario'!B2",
    ]
    assert cleared == ["Ciclo", "Usuario"]


def test_batch_writer_keeps_caches_when_api_request_fails(monkeypatch):
    class FailingBook:
        def values_batch_update(self, _body):
            raise RuntimeError("API unavailable")

    cleared = []
    monkeypatch.setattr(database, "connect_sheet", lambda: FailingBook())
    monkeypatch.setattr(
        database,
        "get_worksheet",
        lambda _name: type(
            "Worksheet",
            (),
            {"row_count": 1000, "add_rows": lambda self, _amount: None},
        )(),
    )
    monkeypatch.setattr(
        database,
        "clear_records_cache",
        lambda name=None: cleared.append(name),
    )

    with pytest.raises(RuntimeError, match="API unavailable"):
        database.write_values_batch(
            [{"sheet": "Ciclo", "range": "B2", "values": [[2]]}]
        )

    assert cleared == []


def test_batch_writer_expands_a_sheet_before_writing_past_its_grid(monkeypatch):
    class FakeBook:
        def __init__(self):
            self.bodies = []

        def values_batch_update(self, body):
            self.bodies.append(body)

    class FakeWorksheetWithCapacity:
        def __init__(self):
            self.row_count = 1000
            self.expansions = []

        def add_rows(self, amount):
            self.expansions.append(amount)
            self.row_count += amount

    book = FakeBook()
    worksheet = FakeWorksheetWithCapacity()
    monkeypatch.setattr(database, "connect_sheet", lambda: book)
    monkeypatch.setattr(database, "get_worksheet", lambda _name: worksheet)
    monkeypatch.setattr(database, "clear_records_cache", lambda _name: None)

    database.write_values_batch(
        [
            {
                "sheet": "XPEventos",
                "range": "A1001:F1005",
                "values": [["event"]] * 5,
            }
        ]
    )

    assert worksheet.expansions == [5]
    assert worksheet.row_count == 1005
    assert len(book.bodies) == 1


def test_set_user_updates_only_the_matching_value_cell(monkeypatch):
    writes = []
    monkeypatch.setattr(
        database,
        "records",
        lambda name: [
            {"chave": "schema_version", "valor": "2"},
            {"chave": "xp", "valor": "100"},
        ] if name == "Usuario" else [],
    )
    monkeypatch.setattr(
        database,
        "write_values_batch",
        lambda updates: writes.append(updates),
    )

    database.set_user("xp", 125)

    assert writes == [
        [
            {
                "sheet": "Usuario",
                "range": "B3",
                "values": [["125"]],
            }
        ]
    ]


def test_set_user_appends_a_missing_key_without_rewriting_the_sheet(monkeypatch):
    writes = []
    monkeypatch.setattr(
        database,
        "records",
        lambda name: [
            {"chave": "schema_version", "valor": "2"},
        ] if name == "Usuario" else [],
    )
    monkeypatch.setattr(
        database,
        "write_values_batch",
        lambda updates: writes.append(updates),
    )

    database.set_user("xp", 25)

    assert writes == [
        [
            {
                "sheet": "Usuario",
                "range": "A3:B3",
                "values": [["xp", "25"]],
            }
        ]
    ]


def test_add_history_updates_one_row_and_tolerates_legacy_values(monkeypatch):
    writes = []
    today = str(date.today())
    monkeypatch.setattr(
        database,
        "records",
        lambda name: [
            {"data": "2026-08-18", "horas": 1, "xp": 100},
            {"data": today, "horas": "inválido", "xp": "200"},
        ] if name == "Historico" else [],
    )
    monkeypatch.setattr(
        database,
        "write_values_batch",
        lambda updates: writes.append(updates),
    )

    database.add_history(2, 50)

    assert writes == [
        [
            {
                "sheet": "Historico",
                "range": "A3:C3",
                "values": [[today, 2, 250]],
            }
        ]
    ]
