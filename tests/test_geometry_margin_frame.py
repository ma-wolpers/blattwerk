"""`:::geometry`: Randbereich (`margin`) und optionaler Rahmen (`frame`).

Der Randbereich ist ein Saum um die Hauptfläche: Hintergrund, Achsen, Graphen und
Punkte laufen dort weiter, Ticks nicht; die Box (`--cols`/`--rows`) umfasst ihn.
Der Rahmen ist wie beim Zahlenstrahl standardmäßig aus.
"""

from __future__ import annotations

import re

import pytest

from app.core.answer_grid_frame import parse_geometry_margin, resolve_geometry_frame
from app.core.answer_grid_plot import render_geometry_answer
from app.core.blatt_validator import inspect_markdown_text
from app.core.blatt_validator_constants import GEOMETRY_MARGIN_DEFAULT


def _render(options, content=""):
    return render_geometry_answer({"width": "4", "height": "4", **options}, content, False, lambda *_args: "")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, GEOMETRY_MARGIN_DEFAULT), ("", GEOMETRY_MARGIN_DEFAULT), ("0", 0.0), ("0.5", 0.5), ("0.99", 0.99),
     ("1", None), ("-0.1", None), ("abc", None), ("nan", None), ("inf", None)],
)
def test_parse_geometry_margin_accepts_zero_up_to_below_one_cell(raw, expected):
    assert parse_geometry_margin(raw) == expected


def test_box_includes_margin_on_both_sides():
    frame = resolve_geometry_frame({"width": "10", "height": "13"})
    assert frame.box_units == (11.0, 14.0)
    assert frame.visible_extent == (-0.5, -0.5, 10.5, 13.5)
    assert resolve_geometry_frame({"width": "10", "height": "13", "margin": "kaputt"}).margin_units == GEOMETRY_MARGIN_DEFAULT
    html = _render({"height": "13"})
    assert "--rows:14.0000" in html and "--cols:5.0000" in html


def test_main_area_and_visible_area_differ_only_by_the_margin():
    frame = resolve_geometry_frame({"width": "4", "height": "4", "margin": "0.5"})
    assert frame.is_in_main_area(4.0, 0.0) and frame.is_visible(4.0, 0.0)
    assert not frame.is_in_main_area(4.3, 0.0) and frame.is_visible(4.3, 0.0)
    assert not frame.is_visible(4.6, 0.0)


def test_frame_is_off_by_default_and_opt_in():
    assert "class='answer grid geometry'" in _render({})
    assert "geometry-framed" not in _render({})
    assert "class='answer grid geometry geometry-framed'" in _render({"frame": "true"})


def test_axes_reach_into_margin_but_ticks_stay_on_main_area():
    html = _render({"axis": "true", "origin": "0,0"})
    assert "<line class='grid-axis' x1='-0.5000' y1='4.0000' x2='4.5000' y2='4.0000' />" in html
    tick_x = [float(value) for value in re.findall(r"class='grid-axis-tick' x1='([\d.\-]+)' y1='3\.8200'", html)]
    assert tick_x and min(tick_x) == 0.0 and max(tick_x) == 4.0
    assert "4.8400,4.0000" in html  # Pfeilspitze 0.34 hinter dem Ende des Randbereichs


def test_function_graph_and_point_continue_into_margin():
    html = _render(
        {"axis": "true", "origin": "0,0"},
        "functions:\n  - {expr: 'x', domain: '0:10'}\npoints:\n  - {x: 4.3, y: 1, label: R}\n  - {x: 4.6, y: 1, label: weg}\n",
    )
    graph = re.search(r"class='grid-function-line[^']*' points='([^']+)'", html).group(1)
    xs = [float(pair.split(",")[0]) for pair in graph.split()]
    assert 4.0 < max(xs) <= 4.5
    assert ">R</text>" in html and ">weg</text>" not in html


def test_background_lines_continue_into_margin_and_margin_zero_ends_at_area():
    assert "y1='-0.5000' x2='0.0000' y2='4.5000'" in _render({"background": "lines"})
    assert "y1='0.0000' x2='0.0000' y2='4.0000'" in _render({"background": "lines", "margin": "0"})


HEAD = "---\ndocument_type: worksheet\nTitel: T\nFach: M\nThema: X\n---\n"


def _messages(header, payload):
    """Meldungen `(code, text)` des Validators für einen einzelnen Geometry-Block."""
    report = inspect_markdown_text(f"{HEAD}:::geometry {header}\n{payload}:::\n")
    return [(diagnostic.code, diagnostic.message) for diagnostic in report.diagnostics]


def test_point_in_margin_is_drawn_but_reported_as_outside_the_area():
    messages = _messages('width=4 height=4 axis=true origin="0,0"', "points:\n  - {x: 4.3, y: 1, label: R}\n")
    an040 = [text for code, text in messages if code == "AN040"]
    assert len(an040) == 1 and an040[0].endswith("Punkt 1 in `points` (4.3|1) liegt im Randbereich und damit außerhalb der Fläche.")
    assert ">R</text>" in _render({"axis": "true", "origin": "0,0"}, "points:\n  - {x: 4.3, y: 1, label: R}\n")


def test_point_on_the_far_edge_of_the_area_is_not_reported():
    """Früher rechnete AN040 mit `width - 1` und meldete einen gezeichneten Randpunkt."""
    messages = _messages('width=10 height=10 axis=true origin="5,5"', "points:\n  - {x: 5, y: 5, label: E}\n")
    assert "AN040" not in [code for code, _text in messages]


def test_point_far_outside_and_default_size_are_checked_like_the_renderer():
    messages = _messages("height=3", "points:\n  - {col: 21, row: 1}\n  - {col: 20, row: 3}\n")
    an040 = [text for code, text in messages if code == "AN040"]
    assert len(an040) == 1 and an040[0].endswith("Punkt 1 in `points` (21|1) liegt außerhalb der Fläche.")


@pytest.mark.parametrize("value", ["1", "-0.5", "breit"])
def test_invalid_margin_is_reported(value):
    assert any(code == "OP002" and "`margin`" in text for code, text in _messages(f"width=4 height=4 margin={value}", ""))


def test_valid_margin_and_frame_are_accepted():
    codes = [code for code, _text in _messages("width=4 height=4 margin=0.9 frame=true", "")]
    assert "OP001" not in codes and "OP002" not in codes and "OP008" not in codes
