import pytest

from modules.config import SHEETS
from modules.database import SheetSchemaError, _ensure_header


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
