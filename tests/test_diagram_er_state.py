"""Tests für `:::erdiagram` (GO S. 8) und `:::statediagram` (GO S. 12)."""

from __future__ import annotations

import re

from app.core.blatt_validator import inspect_markdown_text
from app.core.diagram_block_dispatch import render_diagram_block
from app.core.diagram_er import parse as parse_er
from app.core.diagram_er_layout import arrange, relation_groups
from app.core.diagram_er_route import route_edges
from app.core.diagram_er_shapes import shape_size, title_box
from app.core.diagram_route import diamond_corner, rects_overlap, segment_hits_rect, segments_cross, segments_overlap
from app.core.diagram_svg import balanced_lines
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


KITA = """\
entität Gruppe
    __Gruppenname__
    Dauer der Betreuung
entität Kind
    __Vorname__
    __Nachname__
    Alter
    Besonderheit
    Art des Mittagessens
entität Person
    Vorname
    Name
    Handynummer
entität Adresse
    Festnetznummer
    Faxnummer
entität MitarbeitendeR
MitarbeitendeR 1 - ist - 1 Person
MitarbeitendeR n - arbeitet in - 1 Gruppe
Kind n - gehtIn - 1 Gruppe
Person n - hat - n Adresse
Person n - ist sorgeberechtigt für - n Kind
Person n - ist abholberechtigt für - n Kind
Person n - ist im Notfall ansprechbar für - n Kind"""


def _er_routes(content: str):
    """Modell, Anordnung und rechtwinklige Kantenwege eines ER-Diagramms."""
    model, _ = parse_er(content)
    layout = arrange(model)
    sizes = {name: shape_size(node) for name, node in model.nodes.items()}
    return model, layout, route_edges(sizes, layout.centers, relation_groups(model))


def test_er_layout_is_flat_and_free_of_crossings():
    """Flach, aber kein einzeiliges Band; keine Kante kreuzt oder überdeckt eine andere oder
    läuft durch eine Form."""
    for content in (GO_ER_DIAGRAM, KITA):
        model, layout, routes = _er_routes(content)
        assert 1.5 * layout.height < layout.width < 4 * layout.height
        segments = [(key, pair) for key, points in routes.items() for pair in zip(points, points[1:])]
        for index, (key, segment) in enumerate(segments):
            for other_key, other in segments[index + 1:]:
                assert key == other_key or not segments_overlap(segment, other)
                assert key[0] == other_key[0] or key[1] == other_key[1] or not segments_cross(segment, other)
            for name, node in model.nodes.items():
                if name in layout.centers and name not in key:
                    assert not segment_hits_rect(segment, (*layout.centers[name], *shape_size(node)))


def test_er_parallel_relations_fan_out_and_edges_end_at_diamond_corners():
    """Drei Beziehungen zwischen Person und Kind liegen nebeneinander; Kanten sind rechtwinklig und enden an Ecken."""
    model, layout, routes = _er_routes(KITA)
    fan = next(relations for first, second, relations in relation_groups(model) if {first, second} == {"Person", "Kind"})
    rects = [(*layout.centers[name], *shape_size(model.nodes[name])) for name in fan]
    assert len(rects) == 3
    assert not any(rects_overlap(a, b) for i, a in enumerate(rects) for b in rects[i + 1:])
    for (_entity, relation), points in routes.items():
        cx, cy = layout.centers[relation]
        width, height = shape_size(model.nodes[relation])
        assert points[-1] in {(cx - width / 2, cy), (cx + width / 2, cy), (cx, cy - height / 2), (cx, cy + height / 2)}
        assert all(abs(a[0] - b[0]) < 1e-6 or abs(a[1] - b[1]) < 1e-6 for a, b in zip(points, points[1:]))


def test_er_cardinalities_and_attributes_do_not_overlap():
    """Kein Oval und keine Kardinalität überdeckt ein anderes Element (Rechtecke aus dem SVG)."""
    html = render_diagram_block("erdiagram", {}, KITA)
    boxes = [tuple(float(v) for v in match) for match in re.findall(r"<foreignObject x='([-\d.]+)' y='([-\d.]+)' width='([\d.]+)' height='([\d.]+)'", html)]
    centred = [(x + w / 2, y + h / 2, w - 8, h - 4) for x, y, w, h in boxes]
    assert not [(a, b) for i, a in enumerate(centred) for b in centred[i + 1:] if rects_overlap(a, b)]


def test_er_kita_fits_two_rows_with_the_diagonal_relation_in_between():
    """Person, Kind, Adresse, Gruppe stehen im 2x2-Raster; „arbeitet in“ sitzt schräg dazwischen
    und erreicht obere und untere Rautenecke, ohne „hat“ oder „geht in“ zu berühren."""
    model, layout, routes = _er_routes(KITA.replace("entität MitarbeitendeR\n", "").replace("MitarbeitendeR 1 - ist - 1 Person\n", "").replace("MitarbeitendeR n", "Person 1"))
    rows = {round(layout.centers[name][1]) for name in ("Person", "Kind", "Adresse", "Gruppe")}
    assert len(rows) == 2
    works = next(name for name in model.nodes if name.startswith("arbeitet in"))
    cx, cy = layout.centers[works]
    height = shape_size(model.nodes[works])[1]
    assert {routes[("Person", works)][-1], routes[("Gruppe", works)][-1]} == {(cx, cy - height / 2), (cx, cy + height / 2)}


def test_er_gender_marks_stay_characters():
    """`*`, `:` und `_` in Namen sprengen weder die Syntax noch werden sie Formatierung."""
    content = (
        "entität Mitarbeiter:in\n    __Personal_nr__\nentität Kund*in\n    __Kund*innen_ID__\n"
        "    Lehrer*innen und Schüler*innen\nMitarbeiter:in 1 - berät - n Kund*in"
    )
    model, issues = parse_er(content)
    assert not issues
    assert list(model.nodes)[:2] == ["Mitarbeiter:in", "Kund*in"]
    html = render_diagram_block("erdiagram", {}, content)
    assert "<u>Personal_nr</u>" in html and "<u>Kund*innen_ID</u>" in html
    assert "Lehrer*innen und Schüler*innen" in html and "<em>" not in html
    assert "<em>kursiv</em>" in render_diagram_block("erdiagram", {}, "entität A\n    __k__\n    *kursiv*")


def test_er_long_names_wrap_only_where_the_shape_gets_smaller():
    """Rauten brechen nur um, wenn die Raute dadurch kleiner wird; Wörter bleiben ganz."""
    assert balanced_lines("ist im Notfall ansprechbar für", 0.0, 2) == ["ist im Notfall", "ansprechbar für"]
    assert balanced_lines("Erziehungsberechtigte*r", 0.0, 3) == ["Erziehungsberechtigte*r"]
    model, _ = parse_er(KITA)
    lines = {name.split("#")[0]: title_box(node)[1] for name, node in model.nodes.items()}
    assert lines["ist im Notfall ansprechbar für"] == 2
    assert lines["ist sorgeberechtigt für"] == 1 and lines["Kind"] == 1
    assert "diagram-wrap" in render_diagram_block("erdiagram", {}, KITA)


def test_route_helpers_detect_crossings_overlaps_and_corners():
    """Geometrie-Helfer: echte Kreuzung, aufeinanderliegende Strecken, Rechtecktreffer, Rautenecke."""
    assert segments_cross(((0, 0), (10, 10)), ((0, 10), (10, 0)))
    assert not segments_cross(((0, 0), (10, 0)), ((10, 0), (20, 5)))
    assert segments_overlap(((0, 0), (0, 10)), ((0, 5), (0, 20)))
    assert not segments_overlap(((0, 0), (0, 10)), ((0, 10), (0, 20)))
    assert segment_hits_rect(((-10, 0), (10, 0)), (0, 0, 4, 4))
    assert not segment_hits_rect(((-10, 5), (10, 5)), (0, 0, 4, 4))
    assert diamond_corner(0, 0, 30, 20, (100, 10)) == (30, 0)
    assert diamond_corner(0, 0, 30, 20, (100, 10), taken=[(30, 0)]) == (0, 20)


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
