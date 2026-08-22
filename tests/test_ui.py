from modules.ui import without_emoji


def test_without_emoji_removes_legacy_subject_icon():
    assert without_emoji("📐 Matemática (Assaad)") == "Matemática (Assaad)"
    assert without_emoji("🖋️ Redação") == "Redação"


def test_without_emoji_preserves_plain_text():
    assert without_emoji("História Geral") == "História Geral"
