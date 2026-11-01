"""Tests für `:::flowchart`, `:::sequencediagram`, `:::syntaxdiagram` und `:::logicgates`."""

from __future__ import annotations

import pytest

from app.core.blatt_validator import inspect_markdown_text
from app.core.diagram_block_dispatch import render_diagram_block
from app.core.diagram_expression import ExpressionError, parse_expression
from app.core.diagram_flow import parse as parse_flow
from app.core.diagram_logic import _GRAMMAR, evaluate, variables_of
from app.core.diagram_logic import parse as parse_logic
from app.core.diagram_sequence import parse as parse_sequence
from app.core.diagram_syntax import parse as parse_syntax
from app.core.struktogramm_parse import parse_struktogramm
from struktogramm_go_examples import GO_EXAMPLES

HEAD = "---\nTitel: T\nFach: I\nThema: X\n---\n"


def _codes(block: str, content: str, options: str = "") -> list[str]:
    """Validator-Codes eines Dokuments mit genau diesem Block."""
    text = f"{HEAD}:::{block} {options}\n{content}\n:::\n"
    return [d.code for d in inspect_markdown_text(text, document_type="worksheet").diagnostics]


@pytest.mark.parametrize("example", GO_EXAMPLES)
def test_flowchart_reads_the_structogram_text_unchanged(example):
    """Derselbe Text ergibt dieselbe Elementstruktur und rendert in beiden Blöcken."""
    signature, content = example
    assert repr(parse_flow(content)) == repr(parse_struktogramm(content))
    assert render_diagram_block("flowchart", {"signature": signature}, content)
    assert render_diagram_block("structogram", {"signature": signature}, content)


def test_flowchart_draws_conditions_loops_and_gaps():
    """Rauten für Bedingungen, Beschriftung wahr/falsch, Lücken wie im Struktogramm."""
    content = "wenn x > 0\n    % rückgabe x\nsonst\n    solange y < 3\n        y <- y + 1\nwiederhole\n    a\nbis b"
    worksheet = render_diagram_block("flowchart", {}, content, include_solutions=False)
    solution = render_diagram_block("flowchart", {}, content, include_solutions=True)
    assert worksheet.count("<polygon class='diagram-tone-2'") >= 3
    assert "wahr" in worksheet and "falsch" in worksheet
    assert "x &gt; 0" in worksheet and "y ←" in worksheet
    assert "diagram-hidden" in worksheet and "diagram-hidden" not in solution
    assert "gib x zurück" in solution


def test_flowchart_handles_switch_and_empty_branches():
    """Mehrfachauswahl und leere Zweige stürzen nicht ab."""
    assert render_diagram_block("flowchart", {}, "auswahl n\n    fall 1\n        a\n    fall 2\n        b\n    sonst\n        c")
    assert render_diagram_block("flowchart", {}, "wenn a\n    b")
    assert render_diagram_block("flowchart", {}, "wenn a\nsonst\n    b")
    assert render_diagram_block("flowchart", {}, "solange a\n    wenn b\n        c")


def test_flowchart_validator_uses_structogram_structure_rules_without_signature_duty():
    """Strukturfehler wie im Struktogramm; `signature=` ist keine Pflicht."""
    assert "FC001" in _codes("flowchart", "")
    assert "SG003" in _codes("flowchart", "sonst") or any(c.startswith("SG") for c in _codes("flowchart", "sonst"))
    assert "SG020" not in _codes("flowchart", "rückgabe x")


def test_sequence_parses_participants_and_message_kinds():
    """`teilnehmer` legt die Reihenfolge fest, `-->` ist die Rückgabe, auch ohne Leerzeichen."""
    model, issues = parse_sequence("teilnehmer B\nA->B: frage\nB --> A: antwort\nA -> A: denken")
    assert not issues
    assert model.participants == ["B", "A"]
    assert [m.reply for m in model.messages] == [False, True, False]


def test_sequence_renders_lifelines_labels_and_gaps():
    """Gestrichelte Lebenslinien und Rückgabe; Beschriftung als Lücke."""
    html = render_diagram_block("sequencediagram", {}, "A -> B: %{frage}\nB --> A: antwort\nB -> B: x", include_solutions=False)
    assert "diagram-dashed" in html
    assert "diagram-hidden" in html
    assert "SQ001" in _codes("sequencediagram", "")
    assert "SQ002" in _codes("sequencediagram", "nur text")


def test_syntax_parses_all_constructs_and_reports_errors():
    """Alle Konstrukte werden gelesen; falsche Klammern sind Fehler."""
    rules, issues = parse_syntax('Zahl = Ziffer { Ziffer }\nVz = [ "+" | "-" ] ( a | b ) "c"')
    assert not issues
    assert [rule.name for rule in rules] == ["Zahl", "Vz"]
    assert rules[0].expression.kind == "seq"
    assert rules[0].expression.children[1].kind == "rep"
    assert "SY001" in _codes("syntaxdiagram", "")
    assert "SY002" in _codes("syntaxdiagram", "keine regel")
    assert "SY003" in _codes("syntaxdiagram", "A = { b")
    assert "SY003" in _codes("syntaxdiagram", "A = b )")
    assert "SY003" in _codes("syntaxdiagram", "A = | b")


def test_syntax_terminals_are_round_and_names_square():
    """Terminal rund, Nichtterminal eckig."""
    html = render_diagram_block("syntaxdiagram", {}, 'A = "x" y')
    assert html.count(" rx=") == 1
    assert ">x<" in html.replace("<span>", "").replace("</span>", "") and "y" in html


def test_expression_precedence_and_errors():
    """Und bindet stärker als oder; kaputte Ausdrücke melden einen Fehler."""
    tree = parse_expression("A oder B und nicht C", _GRAMMAR)
    assert tree.value == "oder"
    assert tree.children[1].value == "und"
    assert tree.children[1].children[1].value == "nicht"
    for broken in ("(A und B", "A und", "und A", "A B", "A § B"):
        with pytest.raises(ExpressionError):
            parse_expression(broken, _GRAMMAR)


def test_logic_keeps_names_containing_operator_words():
    """`Sonder` und `Hund` sind Variablen, keine Operatoren."""
    assert variables_of(parse_expression("Sonder und Hund", _GRAMMAR)) == ["Sonder", "Hund"]


def test_logic_evaluates_all_operators():
    """Wertetabelle der Operatoren."""
    for text, expected in (("A und B", False), ("A oder B", True), ("A xoder B", True), ("A nand B", True), ("A nor B", False), ("nicht B", True)):
        assert evaluate(parse_expression(text, _GRAMMAR), {"A": True, "B": False}) is expected


def test_logic_norms_differ_and_iec_uses_symbols():
    """IEC zeigt `&` und `≥1`, ANSI zeichnet Pfade."""
    content = "Q = (A und B) oder nicht C"
    iec = render_diagram_block("logicgates", {}, content)
    ansi = render_diagram_block("logicgates", {"norm": "ansi"}, content)
    assert "&amp;" in iec and "≥1" in iec
    assert "≥1" not in ansi and "<path" in ansi


def test_logic_truth_table_is_computed_and_can_hide_results():
    """Tabelle aus der Formel; `gaps=true` lässt Ergebnisse im Arbeitsblatt offen."""
    options = {"truthtable": "true", "gaps": "true"}
    worksheet = render_diagram_block("logicgates", options, "Q = A und B", include_solutions=False)
    solution = render_diagram_block("logicgates", options, "Q = A und B", include_solutions=True)
    assert worksheet.count("<tr>") == 5
    assert worksheet.count("diagram-hidden") == 4
    assert "diagram-hidden" not in solution
    assert "<td>1</td><td>1</td><td>1</td>" in solution


def test_logic_validator_codes():
    """Struktur und Tabellengröße."""
    assert "LG001" in _codes("logicgates", "")
    assert "LG002" in _codes("logicgates", "A und B")
    assert "LG003" in _codes("logicgates", "Q = (A und")
    assert "LG004" in _codes("logicgates", "Q = A und B und C und D und E und F und G", "truthtable=true")
    circuits, issues = parse_logic("Q = A\nR = nicht A")
    assert not issues and len(circuits) == 2


def test_flowchart_checks_a_given_signature_like_the_structogram():
    """Eine angegebene Signatur wird geprüft, eine fehlende nicht verlangt."""
    assert "SG021" in _codes("flowchart", "rückgabe x", 'signature="f(x: Ganzzahl)"')
    assert "SG010" in _codes("flowchart", "x", 'signature="kaputt"') or any(c.startswith("SG01") for c in _codes("flowchart", "x", 'signature="kaputt"'))


def test_sequence_warns_about_silent_participants():
    """Angekündigte Teilnehmer ohne Nachricht fallen auf."""
    assert "SQ003" in _codes("sequencediagram", "teilnehmer C\nA -> B: x")
