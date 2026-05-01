from app.ui.export_dialog import WorksheetExportDialog


def test_export_shortcuts_help_text_with_mode_selection_mentions_alb():
    text = WorksheetExportDialog._build_shortcuts_help_text(True)

    assert "A/L/B" in text
    assert "Strg+E" in text


def test_export_shortcuts_help_text_without_mode_selection_omits_alb():
    text = WorksheetExportDialog._build_shortcuts_help_text(False)

    assert "A/L/B" not in text
    assert "Strg+E" in text
    assert "K: Black-Screen beides" in text
