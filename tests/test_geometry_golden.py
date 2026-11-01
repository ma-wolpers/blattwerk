"""Referenzausgaben des Geometry-Renderers: byte-identisch über interne Umbauten hinweg.

Die Dateien unter `tests/golden/geometry/` entstanden vor dem Umbau auf
Mathe-Koordinaten (Wunschliste Schritt 8) und werden nicht angepasst, solange
sich die Ausgabe nicht gewollt ändert. Abdeckung: alle Sektionen, Achse mit
gebrochenem, außerhalb liegendem und randständigem Ursprung, krumme
Schrittweiten (dort zeigen sich Rundungsunterschiede), Tick-Obergrenze,
Label-Layout `auto`/`fixed`, Hintergründe und Sichtbarkeitsmarker.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.answer_grid_plot import render_geometry_answer

GOLDEN_DIR = Path(__file__).parent / "golden" / "geometry"
_AXIS = {"width": "10", "height": "10", "axis": "true"}
_PLAIN = {"width": "10", "height": "10"}
_MIXED = (
    "points:\n  - {x: 1, y: 1, label: A}\n  - {x: 2, y: 3, label: B}\n"
    "pairs:\n  - {x1: 0, y1: 0, x2: 3, y2: 2, label: s, line: solid}\n"
    "circles:\n  - {cx: 1, cy: 2, r: 1, label: k}\n"
)

SPECS = {
    "plain_points": (_PLAIN, "points:\n  - {col: 1, row: 2, label: P}\n  - {x: 3, y: 7, label: Q}\n  - {col: 20, row: 2, label: raus}\n", False),
    "plain_mixed_sections": (_PLAIN, _MIXED, False),
    "axis_origin_bottom_left": ({**_AXIS, "origin": "0,0"}, _MIXED, False),
    "axis_origin_center": ({**_AXIS, "origin": "5,5"}, _MIXED, False),
    "axis_origin_top_right": ({**_AXIS, "origin": "10,10"}, _MIXED, False),
    "axis_origin_top_left": ({**_AXIS, "origin": "0,10"}, _MIXED, False),
    "axis_origin_outside_high": ({**_AXIS, "origin": "20,20"}, "points:\n  - {x: -15, y: -15, label: A}\n", False),
    "axis_origin_outside_low": ({**_AXIS, "origin": "-3,-2"}, "points:\n  - {x: 5, y: 5, label: A}\n", False),
    "axis_origin_fractional": ({**_AXIS, "origin": "2.5,3.25"}, _MIXED, False),
    "axis_origin_thirds": ({**_AXIS, "origin": "3.3333,6.6667"}, _MIXED, False),
    "axis_step_half": ({**_AXIS, "origin": "5,5", "step_x": "0.5", "step_y": "0.5"}, _MIXED, False),
    "axis_step_anisotropic": ({**_AXIS, "origin": "4,4", "step_x": "2", "step_y": "0.25"}, _MIXED, False),
    "axis_step_crooked": ({**_AXIS, "origin": "1.7,2.3", "step_x": "0.3", "step_y": "0.7"}, _MIXED, False),
    "axis_many_ticks_capped": ({**_AXIS, "origin": "5,5", "step_x": "50", "step_y": "50"}, "", False),
    "axis_stride_labels": ({"width": "40", "height": "30", "axis": "true", "origin": "20,15"}, "", False),
    "axis_long_names": ({**_AXIS, "origin": "5,5", "axis_label_x": "Zeit in Stunden", "axis_label_y": "Strecke in km"}, _MIXED, False),
    "axis_tiny_grid": ({"width": "2", "height": "2", "axis": "true", "origin": "1,1"}, "points:\n  - {x: 0, y: 0, label: O}\n", False),
    "axis_broken_origin": ({**_AXIS, "origin": "kaputt"}, _MIXED, False),
    "functions": ({**_AXIS, "origin": "5,5"}, "functions:\n  - {expr: 'x^2 - 2', domain: '-3:3', label: f}\n  - {expr: 'sin(x)', domain: '-5:5', label: g}\n  - {expr: '1/x', domain: '-5:5'}\n", False),
    "functions_crooked_step": ({**_AXIS, "origin": "2.5,1.5", "step_x": "0.7", "step_y": "1.3"}, "functions:\n  - {expr: '0.3*x + 0.1', domain: '-2:9', label: h}\n", False),
    "sequence": ({**_AXIS, "origin": "1,1"}, "sequence:\n  - {x: 3, y: 1, label: C}\n  - {x: 1, y: 2, label: A}\n  - {x: 2, y: 0.1, label: B}\n", False),
    "pairs_styles": (_PLAIN, "pairs:\n  - {x1: 1, y1: 1, x2: 9, y2: 1, line: solid, color: '#c00', thickness: 2}\n  - {x1: 0.1, y1: 0.2, x2: 0.7, y2: 9.9, label: d}\n", False),
    "polygons": (_PLAIN, "polygons:\n  - {vertices: [{x: 1, y: 1}, {x: 5, y: 1}, {x: 3, y: 4}], label: T, fill: '#eee'}\n  - {vertices: [{x: 6, y: 1}, {x: 9, y: 1}, {x: 9, y: 4}, {x: 8, y: 2}], label: K}\n  - {vertices: [{x: 1, y: 8}, {x: 2, y: 8}, {x: 3, y: 8}]}\n", False),
    "polygons_axis_crooked": ({**_AXIS, "origin": "1.1,2.2", "step_x": "0.9", "step_y": "1.1"}, "polygons:\n  - {vertices: [{x: 0.1, y: 0.2}, {x: 4.3, y: 1.7}, {x: 2.9, y: 5.3}], label: T}\n", False),
    "circles_plain": (_PLAIN, "circles:\n  - {cx: 3, cy: 3, r: 2, label: k}\n  - {cx: 7, cy: 7, r: 1.5, start_angle: 30, end_angle: 120, label: b}\n  - {cx: 7, cy: 3, r: 1.5, start_angle: 200, end_angle: 100}\n  - {cx: 3, cy: 7, r: 1, start_angle: -45, end_angle: 45}\n", False),
    "circles_ellipse": ({**_AXIS, "origin": "5,5", "step_x": "1", "step_y": "2"}, "circles:\n  - {cx: 0, cy: 0, r: 2, label: e}\n  - {cx: 1, cy: 1, r: 1, start_angle: 10, end_angle: 280}\n", False),
    "labels_fixed": ({**_AXIS, "origin": "2,2", "labels": "fixed"}, _MIXED, False),
    "labels_crowded_auto": (_PLAIN, "points:\n" + "".join(f"  - {{x: {x}, y: 5, label: Punkt{x}}}\n" for x in range(2, 7)), False),
    "labels_crowded_fixed": ({**_PLAIN, "labels": "fixed"}, "points:\n" + "".join(f"  - {{x: {x}, y: 5, label: Punkt{x}}}\n" for x in range(2, 7)), False),
    "background_lines_dashed": ({**_AXIS, "origin": "3,3", "background": "lines", "line": "dashed"}, _MIXED, False),
    "background_dots": ({**_PLAIN, "background": "dots"}, _MIXED, False),
    "show_markers_worksheet": (_PLAIN, "points:\n  - {x: 1, y: 1, label: W, show: '§'}\n  - {x: 2, y: 2, label: L, show: '%'}\n  - {x: 3, y: 3, label: B, show: '&'}\n", False),
    "show_markers_solution": (_PLAIN, "points:\n  - {x: 1, y: 1, label: W, show: '§'}\n  - {x: 2, y: 2, label: L, show: '%'}\n  - {x: 3, y: 3, label: B, show: '&'}\n", True),
}


def render_spec(name: str) -> str:
    """Rendert einen Referenzfall; auch vom einmaligen Erzeugen der Dateien genutzt."""
    options, content, include_solutions = SPECS[name]
    return render_geometry_answer(dict(options), content, include_solutions, lambda *_args: "")


@pytest.mark.parametrize("name", sorted(SPECS))
def test_output_is_byte_identical_to_golden(name):
    assert render_spec(name) == (GOLDEN_DIR / f"{name}.html").read_text(encoding="utf-8")


def test_every_golden_file_has_a_spec():
    assert {path.stem for path in GOLDEN_DIR.glob("*.html")} == set(SPECS)
