"""Tests für Beziehungszeilen, Ebenen-Layout und Kantenführung."""

from __future__ import annotations

from app.core.diagram_edges import parse_edge_line
from app.core.diagram_layout import layered_layout
from app.core.diagram_route import Box, box_exit, diamond_exit, ellipse_exit, orthogonal_route


def _overlaps(layout, sizes) -> list[tuple[str, str]]:
    """Paare von Knoten, deren Rechtecke sich überlappen."""
    names = list(sizes)
    found = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ax, ay = layout.centers[a]
            bx, by = layout.centers[b]
            if abs(ax - bx) < (sizes[a][0] + sizes[b][0]) / 2 and abs(ay - by) < (sizes[a][1] + sizes[b][1]) / 2:
                found.append((a, b))
    return found


def test_edge_line_splits_names_operators_and_label():
    """Pfeile gehen auch ohne Leerzeichen, der erste Doppelpunkt trennt die Beschriftung."""
    edge = parse_edge_line("q0->q1: (#, a) : -> #", ("->", "-"))
    assert edge.names == ("q0", "q1")
    assert edge.operators == ("->",)
    assert edge.label == "(#, a) : -> #"


def test_edge_line_plain_dash_needs_spaces_and_chains():
    """`Wi-Fi` bleibt ein Name; Ketten liefern alle Glieder."""
    edge = parse_edge_line("PC-1 - Switch - Router", ("-",))
    assert edge.names == ("PC-1", "Switch", "Router")
    assert edge.operators == ("-", "-")
    assert parse_edge_line("Wi-Fi", ("-",)) is None


def test_edge_line_prefers_longer_operator_and_rejects_missing_name():
    """`-|>` wird nicht als `-` gelesen; fehlt ein Name, ist es keine Beziehung."""
    assert parse_edge_line("A -|> B", ("-|>", "-")).operators == ("-|>",)
    assert parse_edge_line("A -> ", ("->",)) is None


def test_parent_is_above_children_and_association_stays_beside():
    """Vererbung bestimmt die Ebene, Assoziationspartner bleiben auf derselben Ebene."""
    sizes = {name: (80.0, 40.0) for name in ("Person", "Adresse", "Schueler", "Lehrer")}
    layout = layered_layout(sizes, [("Person", "Schueler"), ("Person", "Lehrer")], [("Person", "Adresse")])
    assert layout.centers["Person"][1] < layout.centers["Schueler"][1]
    assert layout.centers["Person"][1] == layout.centers["Adresse"][1]
    assert not _overlaps(layout, sizes)


def test_layout_is_deterministic_and_survives_cycles_and_self_edges():
    """Gleiche Eingabe, gleiches Ergebnis, auch mit Kreis und Selbstkante."""
    sizes = {name: (40.0, 40.0) for name in "ABC"}
    edges = [("A", "B"), ("B", "C"), ("C", "A"), ("A", "A")]
    assert layered_layout(sizes, edges) == layered_layout(sizes, edges)
    assert not _overlaps(layered_layout(sizes, edges), sizes)


def test_layout_handles_one_and_thirty_nodes_without_overlap():
    """Randfälle: leer, ein Knoten, viele Knoten in beide Richtungen."""
    assert layered_layout({}, []).width == 0
    one = {"A": (50.0, 20.0)}
    assert layered_layout(one, []).centers["A"] == (37.0, 22.0)
    many = {f"N{i}": (60.0, 30.0) for i in range(30)}
    edges = [(f"N{i}", f"N{(i * 2 + 1)}") for i in range(14)]
    for direction in ("TB", "LR"):
        assert not _overlaps(layered_layout(many, edges, direction=direction), many)


def test_left_right_layout_runs_along_x():
    """`LR` legt die Ebenen nebeneinander."""
    layout = layered_layout({"A": (30.0, 30.0), "B": (30.0, 30.0)}, [("A", "B")], direction="LR")
    assert layout.centers["A"][0] < layout.centers["B"][0]
    assert layout.centers["A"][1] == layout.centers["B"][1]


def test_exit_points_lie_on_the_outline():
    """Austrittspunkte liegen auf Rechteck, Ellipse und Raute."""
    assert box_exit(Box(0, 0, 20, 10), (100, 0)) == (10, 0)
    assert ellipse_exit(0, 0, 10, 5, (0, 100)) == (0, 5)
    assert diamond_exit(0, 0, 10, 5, (100, 0)) == (10, 0)


def test_orthogonal_route_is_straight_when_boxes_overlap_on_an_axis():
    """Übereinander: senkrecht; nebeneinander: waagerecht; sonst rechtwinkliges Z."""
    assert orthogonal_route(Box(0, 0, 40, 20), Box(10, 100, 40, 20)) == [(5, 10), (5, 90)]
    assert orthogonal_route(Box(0, 0, 40, 20), Box(100, 5, 40, 20)) == [(20, 2.5), (80, 2.5)]
    route = orthogonal_route(Box(0, 0, 40, 20), Box(100, 100, 40, 20))
    assert len(route) == 4
    assert all(a[0] == b[0] or a[1] == b[1] for a, b in zip(route, route[1:]))
