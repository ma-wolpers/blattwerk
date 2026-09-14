"""Tests for `app.core.operator_legend`: Formen-Matching, Stufengruppen-
Auflösung, `OPR001`/`OPR003`, and the worksheet-only legend placement.
"""

from pathlib import Path

from app.core.blatt_kern_io_build import build_worksheet
from app.core.blatt_validator import inspect_markdown_text
from app.core.operator_legend import (
    _operator_available,
    _resolve_matched_groups,
    _slugify_fach,
    collect_used_operators,
    list_operator_suggestion_details,
    list_operator_suggestions,
    load_operator_data,
    render_operator_legend_html,
)


def _blocks(*contents):
    return [("task", {}, content) for content in contents]


def test_collect_used_operators_survives_unquoted_yaml_stufe_int():
    # Stufe: 11 (unquoted) parses as a YAML int, not a str -- real bug found
    # by the user, previously crashed with AttributeError in
    # _resolve_matched_groups (stufe_value.strip() on an int).
    matched_int, diagnostics_int = collect_used_operators(
        _blocks("!!Begründe!! deine Antwort."), {"Fach": "Mathematik", "Stufe": 11}
    )
    matched_str, diagnostics_str = collect_used_operators(
        _blocks("!!Begründe!! deine Antwort."), {"Fach": "Mathematik", "Stufe": "11"}
    )
    assert matched_int == matched_str
    assert [d.code for d in diagnostics_int] == [d.code for d in diagnostics_str]


def test_slugify_fach_handles_non_string_input():
    assert _slugify_fach(123) == "123"


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
    assert [m.key for m in matched] == ["Bestimmen/Ermitteln"]
    assert diagnostics == []


def test_collect_used_operators_separable_verb_form_resolves_to_darstellen():
    matched, diagnostics = collect_used_operators(
        _blocks("!!Stelle!! den Sachverhalt grafisch dar."), {"Fach": "Mathematik"}
    )
    assert [m.key for m in matched] == ["Grafisch darstellen/Zeichnen"]
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
    assert [m.key for m in matched] == ["Begründen/Nachweisen/Zeigen"]


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
    assert [m.key for m in matched] == ["Begründen/Nachweisen/Zeigen"]
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
    assert "<table class='operator-legend'>" in html
    assert "<td class='operator-legend-key'>Bestimmen</td>" in html
    assert "Ergebnis ermitteln." in html


def test_render_operator_legend_html_has_no_heading():
    from app.core.operator_legend import MatchedOperator

    html = render_operator_legend_html([MatchedOperator(key="Bestimmen", definition="Ergebnis ermitteln.")])
    assert "<h4" not in html
    assert "Operatoren<" not in html


def test_full_pipeline_survives_unquoted_stufe_int_in_frontmatter(tmp_path):
    md_path = tmp_path / "doc.md"
    md_path.write_text(
        "---\nTitel: T\nFach: Mathematik\nThema: X\nStufe: 11\n---\n"
        ":::task\n!!Begründe!! deine Antwort.\n:::\n",
        encoding="utf-8",
    )
    html_path = tmp_path / "doc.html"

    diagnostics = inspect_markdown_text(md_path.read_text(encoding="utf-8")).diagnostics
    assert not any(d.code == "OPR001" for d in diagnostics)

    build_worksheet(str(md_path), str(html_path), include_solutions=False)
    html = html_path.read_text(encoding="utf-8")
    assert "<table class='operator-legend'>" in html
    assert "Begründen/Nachweisen/Zeigen" in html


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
    assert "<table class='operator-legend'>" in worksheet_html

    build_worksheet(str(md_path), str(html_path), include_solutions=True)
    solution_html = html_path.read_text(encoding="utf-8")
    # The .operator-legend CSS class is embedded in every document's
    # <style> block regardless of whether the legend renders -- only the
    # actual <table> element must be absent in solution mode.
    assert "<table class='operator-legend'>" not in solution_html


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


def test_list_operator_suggestions_returns_official_forms_for_mathematik():
    suggestions = list_operator_suggestions("Mathematik", None)
    assert "Bestimmen" in suggestions
    assert "Ermitteln" in suggestions
    assert suggestions == tuple(sorted(suggestions))  # alphabetically sorted


def test_list_operator_suggestions_unknown_fach_returns_empty_tuple():
    assert list_operator_suggestions("Chemie", None) == ()


def test_list_operator_suggestions_unknown_fach_and_stufe_together_no_exception():
    assert list_operator_suggestions("Chemie", "q1") == ()


def test_list_operator_suggestions_excludes_operator_outside_stufe():
    with_q1 = list_operator_suggestions("Mathematik", "Q1")
    with_7 = list_operator_suggestions("Mathematik", "7")
    assert "Begründen" in with_q1
    assert "Begründen" not in with_7


def test_list_operator_suggestions_only_returns_vorschlag_not_all_formen_variants():
    # "Bestimmen/Ermitteln" has 6 conjugated formen (bestimmen, bestimme,
    # bestimmt, ermitteln, ermittle, ermittelt) but only 2 official
    # vorschlag entries -- autocomplete must never leak the conjugations.
    suggestions = list_operator_suggestions("Mathematik", None)
    assert "Bestimmen" in suggestions
    assert "Ermitteln" in suggestions
    for leaked_conjugation in ("bestimme", "bestimmt", "ermittle", "ermittelt"):
        assert leaked_conjugation not in suggestions


def test_list_operator_suggestion_details_covers_every_suggestion_label():
    # The detail overlay must never be able to show a definition for a
    # label the suggestion list itself wouldn't offer, and vice versa --
    # both read from the same `_resolve_available_entries()` call.
    labels = list_operator_suggestions("Mathematik", None)
    details = list_operator_suggestion_details("Mathematik", None)
    assert set(details.keys()) == set(labels)


def test_list_operator_suggestion_details_returns_real_definition_text():
    details = list_operator_suggestion_details("Mathematik", None)
    assert "Bestimmen" in details
    assert details["Bestimmen"]  # non-empty redactional text, not a placeholder


def test_list_operator_suggestion_details_grouped_operators_share_one_definition():
    # "Bestimmen" and "Ermitteln" come from the same combined dataset entry
    # ("Bestimmen/Ermitteln") and therefore share one `definition` string.
    details = list_operator_suggestion_details("Mathematik", None)
    assert details["Bestimmen"] == details["Ermitteln"]


def test_list_operator_suggestion_details_unknown_fach_returns_empty_dict():
    assert list_operator_suggestion_details("Chemie", None) == {}


def test_list_operator_suggestion_details_excludes_operator_outside_stufe():
    with_q1 = list_operator_suggestion_details("Mathematik", "Q1")
    with_7 = list_operator_suggestion_details("Mathematik", "7")
    assert "Begründen" in with_q1
    assert "Begründen" not in with_7


def test_legend_and_autocomplete_agree_on_stufe_availability():
    # Architecture test: collect_used_operators (legend/validator) and
    # list_operator_suggestions (autocomplete) must never structurally
    # diverge on which operators are available for a given Stufe, because
    # both call the same _resolve_matched_groups/_operator_available.
    for stufe, should_be_available in (("7", False), ("Q1", True)):
        matched, diagnostics = collect_used_operators(
            _blocks("!!Begründe!! deine Antwort."), {"Fach": "Mathematik", "Stufe": stufe}
        )
        legend_available = bool(matched) and not any(d.code == "OPR001" for d in diagnostics)
        suggestions = list_operator_suggestions("Mathematik", stufe)
        autocomplete_available = "Begründen" in suggestions
        assert legend_available == should_be_available
        assert autocomplete_available == should_be_available


def test_load_operator_data_caches_by_path_not_by_fach_slug(tmp_path, monkeypatch):
    import app.core.operator_legend as operator_legend_module

    data_dir_a = tmp_path / "a"
    data_dir_b = tmp_path / "b"
    data_dir_a.mkdir()
    data_dir_b.mkdir()
    (data_dir_a / "testfach.json").write_text(
        '{"operatoren": [{"key": "A", "vorschlag": ["A"], "formen": ["a"], "definition": "von a"}]}',
        encoding="utf-8",
    )
    (data_dir_b / "testfach.json").write_text(
        '{"operatoren": [{"key": "B", "vorschlag": ["B"], "formen": ["b"], "definition": "von b"}]}',
        encoding="utf-8",
    )

    monkeypatch.setattr(operator_legend_module, "OPERATOR_DATA_DIR", data_dir_a)
    dataset_a = load_operator_data("Testfach")
    assert dataset_a is not None
    assert dataset_a.operatoren[0].key == "A"

    # Same Fach slug ("testfach"), but a DIFFERENT directory/path -- a
    # string-keyed cache (keyed by fach_slug alone) would incorrectly
    # return dataset_a's cached entry here instead of loading data_dir_b's
    # actual file.
    monkeypatch.setattr(operator_legend_module, "OPERATOR_DATA_DIR", data_dir_b)
    dataset_b = load_operator_data("Testfach")
    assert dataset_b is not None
    assert dataset_b.operatoren[0].key == "B"


def test_load_operator_data_reuses_cache_when_file_unchanged(tmp_path, monkeypatch):
    import app.core.operator_legend as operator_legend_module

    data_dir = tmp_path / "cache_test"
    data_dir.mkdir()
    (data_dir / "testfach2.json").write_text(
        '{"operatoren": [{"key": "A", "vorschlag": ["A"], "formen": ["a"], "definition": "x"}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(operator_legend_module, "OPERATOR_DATA_DIR", data_dir)

    calls = []
    original = operator_legend_module._load_operator_dataset_from_path

    def counting(path):
        calls.append(path)
        return original(path)

    monkeypatch.setattr(operator_legend_module, "_load_operator_dataset_from_path", counting)

    first = load_operator_data("Testfach2")
    second = load_operator_data("Testfach2")
    assert first == second
    assert len(calls) == 1  # second call hit the cache, no re-parse


def test_new_fach_is_pluggable_via_data_layer_alone(tmp_path, monkeypatch):
    # A brand-new Fach becomes available purely by adding a data file --
    # no change to completion_catalogs.py or the UI layer is needed.
    import app.core.operator_legend as operator_legend_module

    data_dir = tmp_path / "new_fach_dir"
    data_dir.mkdir()
    (data_dir / "geschichte.json").write_text(
        '{"operatoren": [{"key": "Erörtern", "vorschlag": ["Erörtern"], '
        '"formen": ["erörtern"], "definition": "Eine Streitfrage abwägend beurteilen."}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(operator_legend_module, "OPERATOR_DATA_DIR", data_dir)

    assert list_operator_suggestions("Geschichte", None) == ("Erörtern",)
