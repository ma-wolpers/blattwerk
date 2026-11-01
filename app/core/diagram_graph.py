"""`:::graph`: Graphen und Binärbäume aus kurzen Zeilen, mit automatischem Layout.

Syntax: `A - B: 5` (ungerichtet), `A -> B: 5` (gerichtet), `A` (einzelner Knoten).
`layout=auto|tree|circle` wählt die Anordnung; `binary=true` liest die Kanten als
Binärbaum: Kinder in Zeilenreihenfolge, `_` steht für ein leeres linkes Kind.
"""

from __future__ import annotations

from .diagram_edges import parse_edge_line
from .diagram_graph_model import GraphEdge, GraphModel, auto_layout
from .diagram_layout_tree import PLACEHOLDER, circle_layout, free_layout, tree_children, tree_layout
from .diagram_route import curve_points, edge_label_center, ellipse_exit
from .diagram_svg import Canvas, text_width
from .diagram_text import ParseIssue, iter_source_lines, make_cell

_OPERATORS = ("->", "-")
_MIN_RADIUS = 17.0
_BEND = 14.0
_TRUE_VALUES = ("1", "true", "yes", "on", "ja")


def parse(content) -> tuple[GraphModel, list[ParseIssue]]:
    """Parst den Blockinhalt fehlertolerant (`GR002`, `GR003`)."""
    model = GraphModel()
    issues: list[ParseIssue] = []
    for source in iter_source_lines(content):
        if source.width:
            issues.append(ParseIssue("GR002", "error", source.number, "Im Graphen gibt es keine Einrückung."))
        edge = parse_edge_line(source.text, _OPERATORS)
        if edge is None:
            if ":" in source.text:
                issues.append(ParseIssue("GR003", "error", source.number, "Erwartet `A - B: 5`, `A -> B: 5` oder einen Knotennamen."))
            else:
                model.add_node(source.text.strip(), source.show)
            continue
        label = make_cell(edge.label, source.show) if edge.label else None
        for index, operator in enumerate(edge.operators):
            first, second = edge.names[index], edge.names[index + 1]
            model.add_node(first, source.show)
            if second != PLACEHOLDER:
                model.add_node(second, source.show)
            model.edges.append(GraphEdge(source.number, first, second, operator == "->", label))
    return model, issues


def _enabled(options, key: str) -> bool:
    """Boolesche Blockoption."""
    return str((options or {}).get(key) or "").strip().lower() in _TRUE_VALUES


def _binary_children(model: GraphModel) -> dict[str, list[str]]:
    """Kinder je Knoten in Zeilenreihenfolge; ein einzelnes Kind ist das linke."""
    children: dict[str, list[str]] = {}
    for edge in model.edges:
        children.setdefault(edge.source, []).append(edge.target)
    for kids in children.values():
        if len(kids) == 1:
            kids.append(PLACEHOLDER)
    return children


def _check_edges(collect, model: GraphModel) -> None:
    """Doppelte Kanten und gemischte Kantenarten (`GR007`, `GR008`)."""
    seen = set()
    for edge in model.edges:
        if edge.target == PLACEHOLDER:
            continue
        key = (edge.source, edge.target) if edge.directed else frozenset((edge.source, edge.target))
        if key in seen:
            collect.add("GR007", f"Die Kante `{edge.source}`–`{edge.target}` steht doppelt.", anchor=f"GR007:{edge.line}")
        seen.add(key)
    kinds = {edge.directed for edge in model.edges if edge.target != PLACEHOLDER}
    if len(kinds) == 2:
        collect.add("GR008", "Gerichtete und ungerichtete Kanten sind gemischt.")


def check(collect, options, model: GraphModel) -> None:
    """Prüft Binärbaum (`GR004`, `GR005`) und erzwungenes Baumlayout (`GR006`)."""
    real_edges = [(edge.source, edge.target) for edge in model.edges if edge.target != PLACEHOLDER]
    _check_edges(collect, model)
    if _enabled(options, "binary"):
        for parent, kids in _binary_children(model).items():
            if len(kids) > 2:
                collect.add("GR004", f"`{parent}` hat mehr als zwei Kinder.", anchor=f"GR004:{parent}")
        targets = {target for _source, target in real_edges}
        roots = [name for name in model.nodes if name not in targets]
        if len(roots) != 1:
            collect.add("GR005", "Ein Binärbaum braucht genau eine Wurzel und keine Kreise.")
    elif str(options.get("layout") or "") == "tree" and tree_children(model.nodes, real_edges) is None:
        collect.add("GR006", "`layout=tree`, aber die Kanten bilden keinen Baum; die Anordnung ist frei.")


def _radius(name: str) -> float:
    """Knotenradius passend zum Namen."""
    return max(_MIN_RADIUS, text_width(name) / 2 + 8)


def _layout(options, model: GraphModel, sizes):
    """Wählt die Anordnung nach den Optionen; ohne Baum bleibt `auto` frei."""
    edges = [(edge.source, edge.target) for edge in model.edges if edge.target != PLACEHOLDER]
    if _enabled(options, "binary"):
        targets = {target for _source, target in edges}
        roots = [name for name in model.nodes if name not in targets]
        if len(roots) == 1:
            return tree_layout(sizes, _binary_children(model), roots[0])
        return free_layout(sizes, edges)
    if str((options or {}).get("layout") or "") == "circle":
        return circle_layout(sizes)
    return auto_layout(sizes, edges, first_is_root=True)


def _draw_edge(canvas: Canvas, edge: GraphEdge, centers, radii, bend: float) -> None:
    """Kante mit optionalem Pfeil, Gewicht seitlich der Mitte."""
    ax, ay = centers[edge.source]
    bx, by = centers[edge.target]
    ra, rb = radii[edge.source], radii[edge.target]
    if edge.source == edge.target:
        canvas.path(f"M {ax - ra * 0.6:.1f} {ay - ra * 0.8:.1f} C {ax - ra - 12:.1f} {ay - ra - 28:.1f}, {ax + ra + 12:.1f} {ay - ra - 28:.1f}, {ax + ra * 0.6:.1f} {ay - ra * 0.8:.1f}")
        if edge.label is not None:
            canvas.label(edge.label, ax, ay - ra - 30, text_width(edge.label.text) + 8)
        return
    if bend:
        control, apex = curve_points((ax, ay), (bx, by), bend)
        start = ellipse_exit(ax, ay, ra, ra, control)
        end = ellipse_exit(bx, by, rb, rb, control)
        canvas.path(f"M {start[0]:.1f} {start[1]:.1f} Q {control[0]:.1f} {control[1]:.1f} {end[0]:.1f} {end[1]:.1f}")
        tail = control
        middle = apex
    else:
        start = ellipse_exit(ax, ay, ra, ra, (bx, by))
        end = ellipse_exit(bx, by, rb, rb, (ax, ay))
        canvas.line(*start, *end)
        tail = start
        middle = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
    if edge.directed:
        canvas.arrow(end, tail, "solid")
    if edge.label is not None:
        width = text_width(edge.label.text) + 8
        canvas.label(edge.label, *edge_label_center(start, end, middle, width, 17.0), width)


def render(options, content, include_solutions=False) -> str:
    """Rendert den Graphen; ein leerer Block ergibt nichts."""
    model, _issues = parse(content)
    if not model:
        return ""
    radii = {name: _radius(name) for name in model.nodes}
    sizes = {name: (2 * radii[name], 2 * radii[name]) for name in model.nodes}
    layout = _layout(options, model, sizes)
    canvas = Canvas(include_solutions)
    pairs = {(edge.source, edge.target) for edge in model.edges}
    for edge in model.edges:
        if edge.target == PLACEHOLDER:
            continue
        reverse = edge.directed and (edge.target, edge.source) in pairs and edge.source != edge.target
        _draw_edge(canvas, edge, layout.centers, radii, _BEND if reverse else 0.0)
    for name, cell in model.nodes.items():
        cx, cy = layout.centers[name]
        canvas.ellipse(cx, cy, radii[name], radii[name], "diagram-tone-3")
        canvas.label(cell, cx, cy, 2 * radii[name])
    return canvas.finish("graph", options, layout.width, layout.height)
