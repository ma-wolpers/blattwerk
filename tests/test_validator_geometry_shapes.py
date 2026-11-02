"""Validator: Geometrie: Kreise, Linienoptionen, Hintergrund, Inhaltsform und Zahlengerade (AN004/AN007/AN018, OP001/OP002).

Aus `test_blatt_validator.py` nach Themen aufgeteilt (300-Zeilen-Regel), Tests unverändert."""

from app.core.blatt_validator import inspect_markdown_text
from validator_doc_support import build_document


def test_geometry_circle_invalid_radius_emits_an018():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "circles:\n"
        "  - {cx: 1, cy: 1, r: -5}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an018 = [d for d in inspected.diagnostics if d.code == "AN018"]
    assert an018


def test_geometry_circle_missing_center_emits_an018():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "circles:\n"
        "  - {r: 2}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an018 = [d for d in inspected.diagnostics if d.code == "AN018"]
    assert an018


def test_geometry_circle_only_start_angle_emits_an018():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "circles:\n"
        "  - {cx: 1, cy: 1, r: 1, start_angle: 0}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an018 = [d for d in inspected.diagnostics if d.code == "AN018"]
    assert an018
    assert "start_angle" in an018[0].message


def test_geometry_circle_only_end_angle_emits_an018():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "circles:\n"
        "  - {cx: 1, cy: 1, r: 1, end_angle: 90}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an018 = [d for d in inspected.diagnostics if d.code == "AN018"]
    assert an018


def test_geometry_circle_both_angles_set_but_one_unparsable_emits_an018():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "circles:\n"
        "  - {cx: 1, cy: 1, r: 1, start_angle: 0, end_angle: not-a-number}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an018 = [d for d in inspected.diagnostics if d.code == "AN018"]
    assert an018
    assert "parsebar" in an018[0].message


def test_geometry_circle_valid_full_circle_does_not_emit_an018():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "circles:\n"
        "  - {cx: 1, cy: 1, r: 1}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN018" not in codes


def test_geometry_circle_valid_arc_does_not_emit_an018():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "circles:\n"
        "  - {cx: 1, cy: 1, r: 1, start_angle: 0, end_angle: 90}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN018" not in codes


def test_geometry_circle_show_marker_is_validated_via_an007():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "circles:\n"
        "  - {cx: 1, cy: 1, r: 1, show: 'both'}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an007 = [d for d in inspected.diagnostics if d.code == "AN007"]
    assert an007


def test_geometry_line_invalid_value_emits_op002_error():
    text = build_document(":::geometry height=2 line=wavy\n:::")
    inspected = inspect_markdown_text(text)
    op002 = [d for d in inspected.diagnostics if d.code == "OP002"]
    assert op002
    assert "line" in op002[0].message


def test_geometry_legacy_rows_cols_options_emit_op001_unknown_option():
    text = build_document(":::geometry rows=4 cols=4\n:::")
    inspected = inspect_markdown_text(text)
    op001 = [d for d in inspected.diagnostics if d.code == "OP001"]
    assert {d.message.split("`")[1] for d in op001} == {"rows", "cols"}


def test_geometry_background_invalid_value_emits_op002_error():
    text = build_document(":::geometry width=4 height=4 background=wavy\n:::")
    inspected = inspect_markdown_text(text)
    op002 = [d for d in inspected.diagnostics if d.code == "OP002"]
    assert op002
    assert "background" in op002[0].message


def test_geometry_background_valid_values_do_not_emit_op002():
    for value in ("none", "lines", "dots"):
        text = build_document(f":::geometry width=4 height=4 background={value}\n:::")
        inspected = inspect_markdown_text(text)
        codes = {diagnostic.code for diagnostic in inspected.diagnostics}
        assert "OP002" not in codes


def test_grid_plain_marker_text_does_not_emit_an004():
    text = build_document(":::grid rows=2\n§\n% Muster\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN004" not in codes


def test_geometry_scalar_content_emits_an004():
    text = build_document(":::geometry height=2\nNur Text\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN004" in codes


def test_geometry_list_root_emits_an004():
    text = build_document(":::geometry height=2\n- 1\n- 2\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN004" in codes


def test_numberline_yaml_marker_show_values_are_accepted():
    text = build_document(
        ":::numberline min=-3 max=3\n"
        "labels:\n"
        "  - {value: -2, show: '§'}\n"
        "answers:\n"
        "  - {value: 0, show: '&'}\n"
        "arcs:\n"
        "  - {from: -2, to: 0, show: '%'}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN007" not in codes


def test_numberline_yaml_legacy_show_values_emit_an007_error():
    text = build_document(
        ":::numberline min=-3 max=3\n"
        "labels:\n"
        "  - {value: -1, show: 'both'}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an007 = [d for d in inspected.diagnostics if d.code == "AN007"]
    assert an007
    assert an007[0].severity == "error"
