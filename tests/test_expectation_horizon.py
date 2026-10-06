"""Erwartungshorizont (Phase 6): Inhalt, Fehlerverhalten, Export."""

import fitz
import pytest

from app.core.exam_expectation_horizon import build_expectation_horizon, build_expectation_horizon_html

HEAD = "---\ndocument_type: exam\nTitel: Klausur 1\nFach: Mathe\nDatum: 1.10.\n---\n"


def _html(body):
    return build_expectation_horizon_html(HEAD + body)


def test_contains_only_numbered_expectations_not_task_text():
    html, diagnostics = _html(
        ":::task points=3 afb=1\nGEHEIMER AUFGABENTEXT\n:::\n:::solution\nFreitext ohne Nummer\n1. Ansatz (1P)\n   - Detail\n2. Ergebnis (2P)\n:::\n"
    )
    assert "GEHEIMER AUFGABENTEXT" not in html and "Freitext ohne Nummer" not in html
    assert "Ansatz - Detail" in html and "Ergebnis" in html
    assert diagnostics == []


def test_merged_solutions_and_targets_are_listed_per_subtask():
    body = (
        ":::task afb=2\nA\n:::\n:::subtask points=2\na\n:::\n:::subtask points=1,5\nb\n:::\n"
        ":::solution\n1. zu b (1,5P)\n:::\n:::solution target=a\n1. zu a (1P)\n:::\n:::solution target=a\n1. auch zu a (1P)\n:::\n"
    )
    html, _ = _html(body)
    a_pos, b_pos = html.index("Aufgabe 1a (2 P)"), html.index("Aufgabe 1b (1,5 P)")
    assert a_pos < html.index("zu a") < html.index("auch zu a") < b_pos < html.index("zu b")
    assert "<td class='pts'>1,5</td>" in html


def test_missing_points_and_missing_expectations_are_warnings():
    html, diagnostics = _html(":::task points=2 afb=1\nA\n:::\n:::solution\n1. ohne Punkte\n:::\n:::task points=1 afb=1\nB\n:::\n")
    codes = [d.code for d in diagnostics]
    assert codes == ["SL005", "SL007"]
    assert "keine Erwartung hinterlegt" in html


def test_parts_subtotals_and_afb_table_relative_to_total():
    html, _ = _html(":::task points=4 afb=1\nA\n:::\n:::solution\n1. x (4P)\n:::\n--hm\n:::task points=6 afb=3\nB\n:::\n:::solution\n1. y (6P)\n:::\n")
    assert html.index("Teil A – hilfsmittelfrei") < html.index("Summe Teil A: 4 P") < html.index("Teil B – mit Hilfsmitteln")
    assert "Summe Teil B: 6 P" in html
    assert "4 P (40 %)" in html and "6 P (60 %)" in html


def test_no_parts_without_aid_split_and_incomplete_afb_without_percent():
    html, _ = _html(":::task points=4\nA\n:::\n:::solution\n1. x (4P)\n:::\n")
    assert "Teil A" not in html and "Summe Teil" not in html
    assert "unvollständig" in html and "%" not in html.split("Anforderungsbereiche")[1]


@pytest.mark.parametrize(
    "body",
    [
        ":::task points=10\nA\n:::\n:::subtask points=3\na\n:::\n:::subtask points=4\nb\n:::\n",  # PK001
        ":::task points=4\nA\n:::\n:::solution\n1. x (3P)\n:::\n",  # PK002
        ":::task\nA\n:::\n:::subtask points=1\na\n:::\n:::subtask\nb\n:::\n",  # PK004
        ":::task\nA\n:::\n:::subtask points=1\na\n:::\n:::subtask points=1\nb\n:::\n:::solution target=task\n1. x (2P)\n:::\n",  # PK005
        ":::task\nA\n:::\n:::subtask\na\n:::\n:::subtask\nb\n:::\n:::solution target=z\n1. x\n:::\n",  # SL008
    ],
)
def test_point_errors_block_export(tmp_path, body):
    source = tmp_path / "k.kbw"
    source.write_text(HEAD + body, encoding="utf-8")
    with pytest.raises(ValueError):
        build_expectation_horizon(source, tmp_path / "ewh.html")
    assert not (tmp_path / "ewh.html").exists()


def test_html_and_pdf_export(tmp_path):
    source = tmp_path / "k.kbw"
    source.write_text(HEAD + ":::task points=2 afb=1\nA\n:::\n:::solution\n1. Formel $x^2$ (2P)\n:::\n", encoding="utf-8")
    diagnostics = []

    html_out = build_expectation_horizon(source, tmp_path / "ewh.html", diagnostics_out=diagnostics)
    pdf_out = build_expectation_horizon(source, tmp_path / "ewh.pdf")

    assert "Erwartungshorizont" in html_out.read_text(encoding="utf-8") and diagnostics == []
    with fitz.open(pdf_out) as doc:
        assert "Erwartungshorizont" in doc[0].get_text()


def test_export_dialog_offers_expectation_horizon_only_as_pdf_or_html():
    from app.ui.export_dialog_worksheet import WorksheetExportDialog

    class _Var:
        def __init__(self, value):
            self.value = value

        def get(self):
            return self.value

        def set(self, value):
            self.value = value

    dialog = WorksheetExportDialog.__new__(WorksheetExportDialog)
    dialog.mode_var = _Var("expectation")
    assert dialog._allowed_formats() == ["pdf", "html"]
    dialog.mode_var = _Var("worksheet")
    assert "png" in dialog._allowed_formats()
