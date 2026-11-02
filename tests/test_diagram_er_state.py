"""Tests für `:::erdiagram` (GO S. 8) und `:::statediagram` (GO S. 12)."""

from __future__ import annotations

from app.core.blatt_validator import inspect_markdown_text
from app.core.diagram_block_dispatch import render_diagram_block
from app.core.diagram_er import parse as parse_er
from app.core.diagram_state import parse as parse_state
from diagram_go_examples import GO_DFA, GO_ER_DIAGRAM, GO_MEALY, GO_PUSHDOWN

HEAD = "---\nTitel: T\nFach: I\nThema: X\n---\n"


def _codes(block: str, content: str, options: str = "") -> list[str]:
    """Validator-Codes eines Dokuments mit genau diesem Block."""
    text = f"{HEAD}:::{block} {options}\n{content}\n:::\n"
    return [d.code for d in inspect_markdown_text(text, document_type="worksheet").diagnostics]


def test_er_go_example_has_no_structure_errors_and_finds_recursion():
    """Das GO-Beispiel parst fehlerfrei; die rekursive Beziehung erzeugt zwei Kanten."""
    model, issues = parse_er(GO_ER_DIAGRAM)
    assert not issues
    relation = next(name for name in model.nodes if name.startswith("istPateVon"))
    assert [link.entity for link in model.links if link.relation == relation] == ["Schueler", "Schueler"]
    assert [cell.text for cell in model.nodes[next(n for n in model.nodes if n.startswith("gehoertZu"))].attributes] == ["seitSchuljahr"]


def test_er_key_uses_existing_underline_and_cardinality_splits_multiword_names():
    """`__x__` unterstreicht; Namen mit Leerzeichen bleiben von der Kardinalität getrennt."""
    html = render_diagram_block("erdiagram", {}, "entität A\n    __k__\nentität Mein Fach\n    __x__\nA 1 - r - n Mein Fach")
    assert "<u>k</u>" in html
    model, _ = parse_er("A 1 - r - n Mein Fach")
    assert list(model.nodes)[1:] == ["A", "Mein Fach"]


def test_er_validator_reports_structure_and_go_duties():
    """Fehler für Struktur, Warnungen für die GO-Pflichten Schlüssel und Kardinalität."""
    assert "ER001" in _codes("erdiagram", "")
    assert "ER002" in _codes("erdiagram", "nur text")
    assert "ER003" in _codes("erdiagram", "    attribut")
    assert "ER004" in _codes("erdiagram", "entität A\nentität A")
    assert "ER005" in _codes("erdiagram", "entität A\n    __k__\nA 1 - r - n B")
    assert "ER006" in _codes("erdiagram", "entität A\n    x")
    assert "ER007" in _codes("erdiagram", "entität A\n    __k__\nentität B\n    __j__\nA - r - B")
    assert not [c for c in _codes("erdiagram", GO_ER_DIAGRAM) if c.startswith("ER")]


def test_er_gaps_cover_attributes_and_cardinalities():
    """Lücken gelten für Attribute (Zeilenmarker) und Kardinalitäten (`%{…}`)."""
    content = "entität A\n    % __k__\nentität B\n    __j__\nA %{1} - r - %{n} B"
    worksheet = render_diagram_block("erdiagram", {}, content, include_solutions=False)
    solution = render_diagram_block("erdiagram", {}, content, include_solutions=True)
    assert worksheet.count("diagram-hidden") == 3
    assert "diagram-hidden" not in solution


def test_er_render_is_deterministic():
    """Das freie Layout nutzt keinen Zufall."""
    assert render_diagram_block("erdiagram", {}, GO_ER_DIAGRAM) == render_diagram_block("erdiagram", {}, GO_ER_DIAGRAM)


def test_state_parses_start_ends_and_merges_parallel_transitions():
    """Start und Ende sind keine Knoten, parallele Übergänge teilen sich eine Kante."""
    model, issues = parse_state(GO_PUSHDOWN[2])
    assert not issues
    assert model.start == "q0"
    assert model.ends == {"q3"}
    assert "start" not in model.states
    assert len(model.transitions[("q1", "q1")].labels) == 6
    assert model.transitions[("q2", "q2")].labels[0].text == "(A, a) : ε"


def test_state_render_shows_go_elements():
    """„Start“-Pfeil, Doppelkreis, Tiefstellung und Alphabetzeile."""
    alphabet, content = GO_DFA
    html = render_diagram_block("statediagram", {"input": alphabet}, content)
    assert "Start" in html
    assert "S<sub>0</sub>" in html
    assert "Eingabealphabet Σ = {a, b, c}" in html
    assert html.count("<ellipse class='diagram-tone") == 4


def test_state_label_gap_hides_text_in_worksheet():
    """`%{c}` lässt die Beschriftung im Arbeitsblatt offen."""
    content = "start -> A\nA -> B: %{c}"
    assert "diagram-hidden" in render_diagram_block("statediagram", {}, content, include_solutions=False)
    assert "diagram-hidden" not in render_diagram_block("statediagram", {}, content, include_solutions=True)


def test_state_validator_checks_go_notation_by_kind():
    """DEA, Mealy und Keller prüfen je ihre Notation; die GO-Beispiele sind sauber."""
    assert "ST001" in _codes("statediagram", "")
    assert "ST002" in _codes("statediagram", "A B")
    assert "ST003" in _codes("statediagram", "start -> A\nstart -> B")
    assert "ST004" in _codes("statediagram", "A -> B: c")
    assert "ST005" in _codes("statediagram", "start -> A\nA -> B: c\nA -> A: c\nB -> B: c", "kind=dfa")
    assert "ST006" in _codes("statediagram", "start -> A\nA -> A: a", 'kind=dfa input="a, b"')
    assert "ST007" in _codes("statediagram", "start -> A\nA -> A: a", "kind=mealy")
    assert "ST007" in _codes("statediagram", "start -> A\nA -> A: a", "kind=pda")
    assert not [c for c in _codes("statediagram", GO_DFA[1], 'kind=dfa input="a, b, c"') if c.startswith("ST")]
    assert not [c for c in _codes("statediagram", GO_MEALY[2], 'kind=mealy input="a, b, c" output="A, B"') if c.startswith("ST")]
    assert not [c for c in _codes("statediagram", GO_PUSHDOWN[2], 'kind=pda input="a, b" stack="A, B, #"') if c.startswith("ST")]


def test_state_edge_detours_around_state_in_between():
    """Regression: `N -> F` lief gerade hinter X und war unsichtbar; jetzt ist es ein Bogen."""
    html = render_diagram_block("statediagram", {}, "N -> X: a\nX -> F: b\nN -> F: c")
    assert html.count(" Q ") == 1


def test_state_alphabet_is_compared_with_the_arrows():
    """Zeichen außerhalb des Alphabets sind Fehler, ungenutzte eine Warnung, in allen Alphabeten."""
    assert "ST008" in _codes("statediagram", "start -> A\nA -> A: b", 'input="a"')
    assert "ST009" in _codes("statediagram", "start -> A\nA -> A: a", 'input="a, z"')
    assert "ST008" in _codes("statediagram", "start -> A\nA -> A: a / X", 'kind=mealy output="A"')
    assert "ST008" in _codes("statediagram", "start -> A\nA -> A: (Z, a) : Z", 'kind=pda stack="A"')
    errors = [d for d in inspect_markdown_text(f"{HEAD}:::statediagram input=a\nstart -> A\nA -> A: b\n:::\n", document_type="worksheet").diagnostics if d.code == "ST008"]
    assert errors[0].severity == "error"


def test_state_dfa_needs_one_arrow_per_symbol_even_without_input_option():
    """Ohne `input` ergibt sich das Alphabet aus den Pfeilen; Selbstpfeile zählen."""
    assert "ST006" in _codes("statediagram", "start -> A\nA -> B: a\nB -> B: b\nA -> A: b", "kind=dfa")
    assert "ST006" not in _codes("statediagram", "start -> A\nA -> B: a\nA -> A: b\nB -> B: a, b", "kind=dfa")
    assert "ST010" in _codes("statediagram", "start -> A\nA -> A: eps", "kind=dfa")


def test_state_mealy_is_checked_for_determinism_too():
    """Mealy: je Zustand und Eingabe genau ein Pfeil."""
    assert "ST005" in _codes("statediagram", "start -> A\nA -> A: a / X\nA -> B: a / Y\nB -> B: a / X", "kind=mealy")
    assert "ST006" in _codes("statediagram", "start -> A\nA -> A: a / X\nA -> B: b / X\nB -> B: a / X", "kind=mealy")


def test_state_detects_unreachable_states():
    """Nicht erreichbare Zustände fallen auf."""
    assert "ST011" in _codes("statediagram", "start -> A\nA -> A: a\nB -> B: a")
    assert "ST011" in _codes("statediagram", "start -> A\nA -> A: a\nende: C")
