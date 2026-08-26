"""Tests für die reine Doc-Discovery-Logik des Hilfe-Popups (`app/ui/blatt_ui_help_docs.py`).

Deckt nur das ab, was ohne laufendes Tk-Fenster testbar ist: welche Dateien
aus einem Ordner als Katalog erscheinen, in welcher Reihenfolge, mit welchem
Label -- inklusive des leeren-Ordner-Falls, der das Popup nicht zum Absturz
bringen darf. Das eigentliche Rendern in ein Text-Widget (bw_gui.widgets)
ist an anderer Stelle abgedeckt; hier geht es nur um die Blattwerk-seitige
Dateiauswahl.
"""

from app.ui.blatt_ui_help_docs import discover_help_docs


def test_discovers_markdown_files_sorted_by_filename(tmp_path):
    (tmp_path / "ZULETZT.md").write_text("# Zuletzt\n", encoding="utf-8")
    (tmp_path / "ANFANG.md").write_text("# Anfang\n", encoding="utf-8")

    catalog = discover_help_docs(tmp_path)

    assert [path.name for _label, path in catalog] == ["ANFANG.md", "ZULETZT.md"]


def test_label_uses_first_h1_heading(tmp_path):
    doc = tmp_path / "NUTZERHANDBUCH.md"
    doc.write_text("<!-- autogen -->\n\n# Blattwerk – Nutzerhandbuch\n\nText.\n", encoding="utf-8")

    catalog = discover_help_docs(tmp_path)

    assert catalog == [("Blattwerk – Nutzerhandbuch", doc)]


def test_label_falls_back_to_filename_when_no_h1_heading(tmp_path):
    doc = tmp_path / "OHNE_UEBERSCHRIFT.md"
    doc.write_text("Nur Fliesstext, keine Ueberschrift.\n", encoding="utf-8")

    catalog = discover_help_docs(tmp_path)

    assert catalog == [("Ohne Ueberschrift", doc)]


def test_non_markdown_files_are_ignored(tmp_path):
    (tmp_path / "README.txt").write_text("kein Markdown", encoding="utf-8")
    (tmp_path / "GUIDE.md").write_text("# Guide\n", encoding="utf-8")

    catalog = discover_help_docs(tmp_path)

    assert [path.name for _label, path in catalog] == ["GUIDE.md"]


def test_empty_directory_returns_empty_catalog(tmp_path):
    assert discover_help_docs(tmp_path) == []


def test_missing_directory_returns_empty_catalog(tmp_path):
    assert discover_help_docs(tmp_path / "does-not-exist") == []
