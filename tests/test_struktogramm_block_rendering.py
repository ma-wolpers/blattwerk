"""Tests für den Struktogramm-Renderer (`app/core/answer_special_struktogramm.py`)."""

import pytest

from app.core.answer_special_struktogramm import estimate_struktogramm_weight, render_struktogramm_block
from app.core.blatt_kern_task_render import render_block
from struktogramm_go_examples import GO_EXAMPLE_1, GO_EXAMPLE_3, GO_EXAMPLES


def _render(content, include_solutions=False, **options):
    """Rendert mit Standard-Signatur, sofern keine angegeben ist."""
    options.setdefault("signature", "f(x: Zahl): Zahl")
    return render_struktogramm_block(options, content, include_solutions)


def test_empty_content_renders_nothing():
    """Ohne Elemente kein HTML (wie andere Blöcke ohne Inhalt)."""
    assert render_struktogramm_block({}, "  \n") == ""


@pytest.mark.parametrize(("signature", "content"), GO_EXAMPLES)
def test_go_examples_render(signature, content):
    """Alle GO-Beispiele rendern mit Kopf und Diagrammrahmen."""
    html = render_struktogramm_block({"signature": signature}, content)
    assert html.startswith("<div class='stg-block'>")
    assert "<div class='stg-sig'>" in html and "<div class='stg'>" in html


def test_example_1_structure_and_texts():
    """Bsp. 1: Kopfschleife, Verzweigung mit leerem falsch-Zweig, Rückgabetexte."""
    html = render_struktogramm_block({"signature": GO_EXAMPLE_1[0]}, GO_EXAMPLE_1[1])
    assert "stg-loop stg-loop-head" in html
    assert "stg-branch" in html and ">wahr<" in html and ">falsch<" in html
    assert "gib wahr zurück" in html and "gib falsch zurück" in html
    assert "minmax(0, 15fr) 4.6em" in html
    assert "stg-cell stg-empty" in html


def test_example_3_switch_and_foot_loop():
    """Bsp. 3: Auswahl mit `sonst`-Gegenschräge, Fußschleife unten, `←`."""
    html = render_struktogramm_block({"signature": GO_EXAMPLE_3[0]}, GO_EXAMPLE_3[1])
    assert "stg-switch" in html and ">sonst<" in html
    assert html.count("points='0,100 100,0'") >= 1
    assert "stg-loop stg-loop-foot" in html and "wiederhole bis anzahlRot &gt; 30" in html
    assert "f ← leere" in html and "<-" not in html


def test_gap_in_worksheet_keeps_text_hidden_with_min_height():
    """Lücke: Arbeitsblatt enthält den Text unsichtbar (Höhe) + `stg-gap` (Mindesthöhe)."""
    worksheet = _render("wenn x > 0\n    % rückgabe x\nsonst\n    rückgabe 0")
    assert "stg-gap" in worksheet
    assert "<span class='stg-hidden'>gib x zurück</span>" in worksheet


def test_gap_in_solution_is_visible_and_marked():
    """Lösung: der Lückentext ist sichtbar und farbig markiert, keine Lücke."""
    solution = _render("wenn x > 0\n    % rückgabe x\nsonst\n    rückgabe 0", include_solutions=True)
    assert "stg-hidden" not in solution and "stg-gap" not in solution
    assert "table-solution-marker'>gib x zurück" in solution


def test_partial_gap_hides_only_the_token():
    """`rückgabe %{x}`: nur `x` ist Lücke, „gib … zurück“ bleibt sichtbar."""
    html = _render("rückgabe %{x}")
    assert "gib <span class='stg-hidden'>x</span> zurück" in html


def test_condition_gap_marks_branch_head():
    """`% wenn …`: die Bedingung ist Lücke, der Dreieckskopf bekommt die Mindesthöhe."""
    html = _render("% wenn x > 0\n    rückgabe x\nsonst\n    rückgabe 0")
    assert "class='stg-head stg-gap'" in html


def test_text_is_escaped():
    """Zelltexte werden escaped: kein rohes HTML, Vergleiche wie `a<b` bleiben Text."""
    html = _render("rückgabe <b>x</b>")
    assert "<b>" not in html
    assert "a&lt;b" in _render("wenn a<b\n    rückgabe a\nsonst\n    rückgabe b")


def test_width_option_is_sanitized():
    """Nur einfache CSS-Längen landen im `style`; alles andere wird ignoriert."""
    assert "style='width:70%;'" in _render("rückgabe x", width="70%")
    assert "style=" not in _render("rückgabe x", width="70%;color:red").split("<div class='stg-sig'>")[0]


def test_alias_renders_identically_through_dispatcher():
    """`structogram` und `struktogramm` liefern im Block-Dispatcher dasselbe HTML."""
    options = {"signature": GO_EXAMPLE_1[0]}
    main = render_block("struktogramm", dict(options), GO_EXAMPLE_1[1], include_solutions=False)
    alias = render_block("structogram", dict(options), GO_EXAMPLE_1[1], include_solutions=False)
    assert main.replace("struktogramm", "X") == alias.replace("structogram", "X")
    assert "stg-block" in main


def test_weight_grows_with_lines():
    """Mehr Zeilen → größeres Layoutgewicht; leer → 0."""
    assert estimate_struktogramm_weight({}, "") == 0.0
    assert estimate_struktogramm_weight({}, "a\nb\nc") > estimate_struktogramm_weight({}, "a")
