from app.ui.export_dialog import PresentationExportDialog, WorksheetExportDialog


def test_export_shortcuts_help_text_with_mode_selection_mentions_alb():
    text = WorksheetExportDialog._build_shortcuts_help_text(True)

    assert "A/L/B" in text
    assert "Strg+E" in text
    assert "K: Black-Screen beides" not in text


def test_export_shortcuts_help_text_without_mode_selection_omits_alb():
    text = WorksheetExportDialog._build_shortcuts_help_text(False)

    assert "A/L/B" not in text
    assert "Strg+E" in text
    assert "K: Black-Screen beides" not in text


def test_presentation_export_shortcuts_help_mentions_black_screen_shortcut():
    text = PresentationExportDialog._build_shortcuts_help_text()

    assert "K: Black-Screen beides" in text
