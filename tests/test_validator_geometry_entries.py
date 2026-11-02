"""Validator: Geometrie, Gitter und Zahlengerade: Einträge, Achsen, Farben und Linien (AN007/AN011 bis AN015, OP005).

Aus `test_blatt_validator.py` nach Themen aufgeteilt (300-Zeilen-Regel), Tests unverändert."""

from app.core.blatt_validator import inspect_markdown_text
from validator_doc_support import build_document


def test_geometry_yaml_marker_show_values_are_accepted():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "points:\n"
        "  - {col: 1, row: 1, show: '§'}\n"
        "sequence:\n"
        "  - {x: 0, y: 0, show: '&'}\n"
        "functions:\n"
        "  - {expr: 'x', domain: '-1:1', show: '%'}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN007" not in codes


def test_geometry_yaml_legacy_show_values_emit_an007_error():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "points:\n"
        "  - {col: 1, row: 1, show: 'both'}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an007 = [d for d in inspected.diagnostics if d.code == "AN007"]
    assert an007
    assert an007[0].severity == "error"


def test_grid_line_dashed_option_is_accepted():
    text = build_document(":::grid rows=2 line=dashed\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP002" not in codes


def test_geometry_unknown_entry_key_emits_an011_warning():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "functions:\n"
        "  - {expr: 'x^2', lable: 'typo'}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an011 = [d for d in inspected.diagnostics if d.code == "AN011"]
    assert an011
    assert "lable" in an011[0].message


def test_geometry_all_allowed_entry_keys_do_not_emit_an011():
    text = build_document(
        ":::geometry width=4 height=4 axis=true origin=\"2,2\"\n"
        "points:\n"
        "  - {x: 0, y: 0, col: 0, row: 0, label: p, show: '&', color: red, thickness: 1}\n"
        "sequence:\n"
        "  - {x: 0, y: 0, label: s, show: '&', color: red, thickness: 1}\n"
        "pairs:\n"
        "  - {x1: 0, y1: 0, x2: 1, y2: 1, line: solid, label: l, show: '&', color: red, thickness: 1}\n"
        "polygons:\n"
        "  - {vertices: [{x: 0, y: 0}, {x: 1, y: 0}, {x: 1, y: 1}], label: g, show: '&', color: red, thickness: 1, fill: blue}\n"
        "circles:\n"
        "  - {cx: 0, cy: 0, r: 1, start_angle: 0, end_angle: 90, label: c, show: '&', color: red, thickness: 1, fill: blue}\n"
        "functions:\n"
        "  - {expr: x, domain: '-1:1', label: f, show: '&', color: red, thickness: 1}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN011" not in codes


def test_geometry_axis_true_without_origin_emits_op005_error():
    text = build_document(":::geometry width=4 height=4 axis=true\n:::")
    inspected = inspect_markdown_text(text)
    op005 = [d for d in inspected.diagnostics if d.code == "OP005"]
    assert op005
    assert op005[0].severity == "error"


def test_geometry_axis_true_with_unparsable_origin_emits_op005_error():
    text = build_document(":::geometry width=4 height=4 axis=true origin=\"not-a-pair\"\n:::")
    inspected = inspect_markdown_text(text)
    op005 = [d for d in inspected.diagnostics if d.code == "OP005"]
    assert op005


def test_geometry_axis_true_with_valid_origin_does_not_emit_op005():
    text = build_document(":::geometry width=4 height=4 axis=true origin=\"2,2\"\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP005" not in codes


def test_geometry_without_axis_does_not_emit_op005_even_without_origin():
    text = build_document(":::geometry width=4 height=4\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP005" not in codes


def test_geometry_functions_without_axis_emits_an015_warning():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "functions:\n"
        "  - {expr: 'x'}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an015 = [d for d in inspected.diagnostics if d.code == "AN015"]
    assert an015
    assert an015[0].severity == "warning"


def test_geometry_functions_with_axis_does_not_emit_an015():
    text = build_document(
        ":::geometry width=4 height=4 axis=true origin=\"2,2\"\n"
        "functions:\n"
        "  - {expr: 'x'}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN015" not in codes


def test_geometry_pairs_without_axis_does_not_emit_an015():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "pairs:\n"
        "  - {x1: 0, y1: 0, x2: 1, y2: 1}\n"
        "sequence:\n"
        "  - {x: 0, y: 0}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN015" not in codes


def test_geometry_pairs_line_invalid_value_emits_an012_error_separately_from_op002():
    text = build_document(
        ":::geometry width=4 height=4 line=dashed\n"
        "pairs:\n"
        "  - {x1: 0, y1: 0, x2: 1, y2: 1, line: wavy}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an012 = [d for d in inspected.diagnostics if d.code == "AN012"]
    assert an012
    assert an012[0].severity == "error"
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP002" not in codes


def test_geometry_invalid_color_emits_an013_warning():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "points:\n"
        "  - {x: 0, y: 0, color: 'red;}body{display:none'}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an013 = [d for d in inspected.diagnostics if d.code == "AN013"]
    assert an013
    assert an013[0].severity == "warning"


def test_geometry_valid_color_does_not_emit_an013():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "points:\n"
        "  - {x: 0, y: 0, color: '#ff00aa'}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN013" not in codes


def test_geometry_non_positive_thickness_emits_an014_warning():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "points:\n"
        "  - {x: 0, y: 0, thickness: 0}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an014 = [d for d in inspected.diagnostics if d.code == "AN014"]
    assert an014


def test_geometry_positive_thickness_does_not_emit_an014():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "points:\n"
        "  - {x: 0, y: 0, thickness: 2.5}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN014" not in codes


def test_geometry_invalid_fill_emits_an013_warning():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "polygons:\n"
        "  - {vertices: [{x: 0, y: 0}, {x: 1, y: 0}, {x: 1, y: 1}], fill: 'red;}body{display:none'}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an013 = [d for d in inspected.diagnostics if d.code == "AN013"]
    assert an013
    assert "fill" in an013[0].message


def test_geometry_polygon_too_few_vertices_emits_an017():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "polygons:\n"
        "  - {vertices: [{x: 0, y: 0}, {x: 1, y: 1}]}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an017 = [d for d in inspected.diagnostics if d.code == "AN017"]
    assert an017


def test_geometry_polygon_one_invalid_vertex_emits_an017():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "polygons:\n"
        "  - {vertices: [{x: 0, y: 0}, {x: 1, y: 0}, {x: not-a-number, y: 1}, {x: 0, y: 1}]}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an017 = [d for d in inspected.diagnostics if d.code == "AN017"]
    assert an017


def test_geometry_valid_polygon_does_not_emit_an017():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "polygons:\n"
        "  - {vertices: [{x: 0, y: 0}, {x: 1, y: 0}, {x: 1, y: 1}]}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN017" not in codes


def test_geometry_polygon_show_marker_is_validated_via_an007():
    text = build_document(
        ":::geometry width=4 height=4\n"
        "polygons:\n"
        "  - {vertices: [{x: 0, y: 0}, {x: 1, y: 0}, {x: 1, y: 1}], show: 'both'}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an007 = [d for d in inspected.diagnostics if d.code == "AN007"]
    assert an007
