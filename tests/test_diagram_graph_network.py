"""Tests für `:::graph`, `:::networkdiagram` und das Baum-/freie Layout."""

from __future__ import annotations

from app.core.blatt_validator import inspect_markdown_text
from app.core.diagram_block_dispatch import render_diagram_block
from app.core.diagram_graph import parse as parse_graph
from app.core.diagram_layout_tree import PLACEHOLDER, circle_layout, free_layout, tree_children, tree_layout
from app.core.diagram_network import parse as parse_network
from app.core.diagram_network import symbol_for

HEAD = "---\nTitel: T\nFach: I\nThema: X\n---\n"


def _codes(block: str, content: str, options: str = "") -> list[str]:
    """Validator-Codes eines Dokuments mit genau diesem Block."""
    text = f"{HEAD}:::{block} {options}\n{content}\n:::\n"
    return [d.code for d in inspect_markdown_text(text, document_type="worksheet").diagnostics]


def _no_overlap(layout, sizes) -> bool:
    """Prüft paarweise, dass sich keine Knotenrechtecke schneiden."""
    names = list(sizes)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ax, ay = layout.centers[a]
            bx, by = layout.centers[b]
            if abs(ax - bx) < (sizes[a][0] + sizes[b][0]) / 2 and abs(ay - by) < (sizes[a][1] + sizes[b][1]) / 2:
                return False
    return True


def test_tree_layout_centers_parent_and_reserves_placeholder_side():
    """Eltern mittig; ein leeres linkes Kind schiebt das rechte nach rechts."""
    sizes = {name: (30.0, 30.0) for name in "ABC"}
    layout = tree_layout(sizes, {"A": ["B", "C"]}, "A")
    assert layout.centers["A"][0] == (layout.centers["B"][0] + layout.centers["C"][0]) / 2
    assert layout.centers["A"][1] < layout.centers["B"][1]
    only_right = tree_layout({"A": (30.0, 30.0), "C": (30.0, 30.0)}, {"A": [PLACEHOLDER, "C"]}, "A")
    assert only_right.centers["C"][0] > only_right.centers["A"][0]


def test_tree_children_detects_trees_and_picks_busiest_root():
    """Baum erkannt, Kreis abgelehnt, unzusammenhängend abgelehnt."""
    root, children = tree_children("RABC", [("A", "R"), ("B", "R"), ("C", "R")])
    assert root == "R" and set(children["R"]) == {"A", "B", "C"}
    assert tree_children("ABC", [("A", "B"), ("B", "C"), ("C", "A")]) is None
    assert tree_children("ABCD", [("A", "B"), ("A", "B"), ("C", "D")]) is None


def test_free_and_circle_layout_are_deterministic_without_overlap():
    """Gleiche Eingabe, gleiches Ergebnis; Knoten überlappen nicht, auch bei 30 Knoten."""
    sizes = {f"N{i}": (40.0, 40.0) for i in range(30)}
    edges = [(f"N{i}", f"N{(i + 1) % 30}") for i in range(30)]
    assert free_layout(sizes, edges) == free_layout(sizes, edges)
    assert _no_overlap(free_layout(sizes, edges), sizes)
    assert _no_overlap(circle_layout(sizes), sizes)
    assert free_layout({"A": (40.0, 40.0)}, []).width > 0


def test_graph_parses_edges_weights_and_lone_nodes():
    """Gerichtet, ungerichtet, Gewicht und einzelner Knoten."""
    model, issues = parse_graph("A - B: 5\nB -> C\nD")
    assert not issues
    assert list(model.nodes) == ["A", "B", "C", "D"]
    assert model.edges[0].label.text == "5" and not model.edges[0].directed
    assert model.edges[1].directed


def test_graph_renders_weight_gap_and_arrows():
    """Gewichte als Lücke, Pfeil nur bei gerichteten Kanten, deterministisch."""
    worksheet = render_diagram_block("graph", {}, "A - B: %{5}", include_solutions=False)
    solution = render_diagram_block("graph", {}, "A - B: %{5}", include_solutions=True)
    assert "diagram-hidden" in worksheet and "diagram-hidden" not in solution
    assert "diagram-solid" not in worksheet
    assert "diagram-solid" in render_diagram_block("graph", {}, "A -> B")
    content = "A - B: 5\nB - C: 2\nC - A: 7\nC - D: 1\nD - B: 4"
    assert render_diagram_block("graph", {}, content) == render_diagram_block("graph", {}, content)


def test_graph_handles_self_edge_opposite_edges_and_all_layouts():
    """Selbstkante, Hin- und Rückweg und alle Layoutoptionen rendern."""
    assert " C " in render_diagram_block("graph", {}, "A - A: x")
    assert " Q " in render_diagram_block("graph", {}, "A -> B\nB -> A")
    for layout in ("auto", "tree", "circle"):
        assert render_diagram_block("graph", {"layout": layout}, "A - B\nB - C")


def test_binary_tree_keeps_left_and_right():
    """Einzelnes Kind links, mit `_` rechts."""
    left = render_diagram_block("graph", {"binary": "true"}, "8 - 3")
    right = render_diagram_block("graph", {"binary": "true"}, "8 - _\n8 - 9")
    assert left and right and left != right


def test_graph_validator_codes():
    """Struktur und Binärbaum-Regeln."""
    assert "GR001" in _codes("graph", "")
    assert "GR002" in _codes("graph", "A\n    B")
    assert "GR003" in _codes("graph", "A: 5")
    assert "GR004" in _codes("graph", "A - B\nA - C\nA - D", "binary=true")
    assert "GR005" in _codes("graph", "A - B\nB - A", "binary=true")
    assert "GR006" in _codes("graph", "A - B\nB - C\nC - A", "layout=tree")
    assert not [c for c in _codes("graph", "A - B: 5\nB - C") if c.startswith("GR")]


def test_network_symbols_come_from_names_and_can_be_overridden():
    """Namensanfang wählt das Symbol, `Name: symbol` überschreibt es."""
    assert symbol_for("Switch2") == "switch"
    assert symbol_for("Laptop") == "rechner"
    assert symbol_for("Tablet") == "rechner"
    model, issues = parse_network("PC1 - Switch - Router\nDrucker1: rechner")
    assert not issues
    assert [(edge.source, edge.target) for edge in model.edges] == [("PC1", "Switch"), ("Switch", "Router")]
    assert model.symbols == {"Drucker1": "rechner"}


def test_network_renders_and_validates():
    """Plan rendert deterministisch, Fehler werden gemeldet."""
    content = "PC1 - Switch\nPC2 - Switch\nSwitch - Router\nRouter - Internet\nServer - Switch\nDrucker - Switch"
    html = render_diagram_block("networkdiagram", {}, content)
    assert "PC1" in html and "Internet" in html
    assert html == render_diagram_block("networkdiagram", {}, content)
    assert "NW001" in _codes("networkdiagram", "")
    assert "NW002" in _codes("networkdiagram", "nur text")
    assert "NW003" in _codes("networkdiagram", "A: quark")
    assert not [c for c in _codes("networkdiagram", content) if c.startswith("NW")]


def test_graph_tree_starts_at_the_first_node_and_network_at_the_busiest():
    """Im Graphen ist der erste Knoten die Wurzel, im Netzwerk das meistverbundene Gerät."""
    root, _children = tree_children("WAB", [("W", "A"), ("A", "B")], first_is_root=True)
    assert root == "W"
    assert tree_children("WAB", [("W", "A"), ("A", "B")])[0] == "A"


def test_width_option_never_enlarges_beyond_natural_size():
    """`width=` darf verkleinern, die Schrift wächst aber nie mit."""
    html = render_diagram_block("graph", {"width": "90%"}, "A - B")
    assert "width:90%;max-width:min(100%," in html
