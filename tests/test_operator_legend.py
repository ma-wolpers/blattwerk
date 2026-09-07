"""Tests for `app.core.operator_legend`: Formen-Matching, Stufengruppen-
Auflösung, `OPR001`/`OPR003`, and the worksheet-only legend placement.
"""

from pathlib import Path

from app.core.blatt_kern_io_build import build_worksheet
from app.core.blatt_validator import inspect_markdown_text
from app.core.operator_legend import (
    _operator_available,
    _resolve_matched_groups,
    collect_used_operators,
    render_operator_legend_html,
)


def _blocks(*contents):
    return [("task", {}, content) for content in contents]


def test_collect_used_operators_is_a_pure_no_op_without_any_marker(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.core.operator_legend.load_operator_data",
        lambda fach: calls.append(fach) or None,
    )
    matched, diagnostics = collect_used_operators(
        _blocks("Ganz normaler Text ohne Marker."), {"Fach": "Mathematik"}
    )
    assert matched == []
    assert diagnostics == []
    assert calls == []  # no filesystem access at all


def test_collect_used_operators_matches_and_deduplicates():
    matched, diagnostics = collect_used_operators(
        _blocks("!!Bestimme!! die Nullstellen. Danach !!bestimme!! die Extrema."),
        {"Fach": "Mathematik"},
    )
    assert [m.key for m in matched] == ["Bestimmen"]
    assert diagnostics == []


def test_collect_used_operators_separable_verb_form_resolves_to_darstellen():
    matched, diagnostics = collect_used_operators(
        _blocks("!!Stelle!! den Sachverhalt grafisch dar."), {"Fach": "Mathematik"}
    )
    assert [m.key for m in matched] == ["Darstellen"]
    assert diagnostics == []


def test_collect_used_operators_unmatched_form_emits_opr001():
    matched, diagnostics = collect_used_operators(
        _blocks("!!Erkläre!! den Zusammenhang."), {"Fach": "Mathematik"}
    )
    assert matched == []
    assert [d.code for d in diagnostics] == ["OPR001"]


def test_collect_used_operators_missing_fach_file_emits_opr003():
    matched, diagnostics = collect_used_operators(_blocks("!!Bestimme!! etwas."), {"Fach": "Chemie"})
    assert matched == []
    assert [d.code for d in diagnostics] == ["OPR003"]


def test_collect_used_operators_no_stufe_keeps_all_operators_available():
    matched, _ = collect_used_operators(_blocks("!!Begründe!! deine Antwort."), {"Fach": "Mathematik"})
    assert [m.key for m in matched] == ["Begründen"]


def test_collect_used_operators_stufe_outside_required_group_excludes_operator():
    matched, diagnostics = collect_used_operators(
        _blocks("!!Begründe!! deine Antwort."), {"Fach": "Mathematik", "Stufe": "7"}
    )
    assert matched == []
    assert [d.code for d in diagnostics] == ["OPR001"]


def test_collect_used_operators_stufe_inside_required_group_includes_operator():
    matched, diagnostics = collect_used_operators(
        _blocks("!!Begründe!! deine Antwort."), {"Fach": "Mathematik", "Stufe": "Q1"}
    )
    assert [m.key for m in matched] == ["Begründen"]
    assert diagnostics == []


def test_resolve_matched_groups_identity_fallback_without_stufengruppen():
    assert _resolve_matched_groups("q1", {}) == {"q1"}


def test_resolve_matched_groups_value_can_belong_to_multiple_groups():
    groups = {"A": ("q1",), "B": ("q1", "q2")}
    assert _resolve_matched_groups("q1", groups) == {"A", "B"}


def test_operator_available_true_without_any_stufe_restriction():
    class _Entry:
        stufen = ()

    assert _operator_available(_Entry(), "q1", set()) is True


def test_operator_available_case_insensitive_group_match():
    class _Entry:
        stufen = ("Oberstufe",)

    assert _operator_available(_Entry(), "q1", {"oberstufe"}) is True


def test_render_operator_legend_html_empty_for_no_matches():
    assert render_operator_legend_html([]) == ""


def test_render_operator_legend_html_lists_key_and_definition():
    from app.core.operator_legend import MatchedOperator

    html = render_operator_legend_html([MatchedOperator(key="Bestimmen", definition="Ergebnis ermitteln.")])
    assert "operator-legend" in html
    assert "Bestimmen" in html
    assert "Ergebnis ermitteln." in html


def test_render_html_legend_appears_only_in_worksheet_mode_not_solution(tmp_path):
    md_path = tmp_path / "doc.md"
    md_path.write_text(
        "---\nTitel: T\nFach: Mathematik\nThema: X\n---\n"
        ":::task\n!!Bestimme!! die Nullstellen.\n:::\n",
        encoding="utf-8",
    )
    html_path = tmp_path / "doc.html"

    build_worksheet(str(md_path), str(html_path), include_solutions=False)
    worksheet_html = html_path.read_text(encoding="utf-8")
    assert "operator-legend" in worksheet_html

    build_worksheet(str(md_path), str(html_path), include_solutions=True)
    solution_html = html_path.read_text(encoding="utf-8")
    assert "operator-legend" not in solution_html


def test_opr_diagnostics_surface_through_document_validation():
    text = (
        "---\nTitel: T\nFach: Chemie\nThema: X\n---\n"
        ":::task\n!!Bestimme!! etwas.\n:::\n"
    )
    diagnostics = inspect_markdown_text(text).diagnostics
    assert any(d.code == "OPR003" for d in diagnostics)


def test_kurzentwurf_runtime_never_imports_operator_legend():
    # operator_legend.py is Arbeitsblatt-only (see Haus/Garage-Prinzip) --
    # this pins down that the Kurzentwurf renderer never wires it in, so a
    # future change can't silently make the legend leak into Kurzentwurf.
    render_html_source = Path("app/core/kurzentwurf_runtime/render_html.py").read_text(encoding="utf-8")
    assert "operator_legend" not in render_html_source
