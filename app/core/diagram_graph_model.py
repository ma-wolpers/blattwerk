"""Gemeinsames Modell für `:::graph` und `:::networkdiagram`: Knoten und Kanten aus kurzen Zeilen.

Beide Blöcke lesen dieselbe Schreibweise und wählen das Layout nach derselben Regel: Ein
Baum wird als Baum gezeichnet, alles andere frei.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .diagram_layout import Layout
from .diagram_layout_tree import free_layout, tree_children, tree_layout
from .diagram_text import Cell, make_cell


@dataclass(frozen=True)
class GraphEdge:
    """Eine Kante; `directed` kommt vom Operator `->`."""

    line: int
    source: str
    target: str
    directed: bool
    label: Cell | None


@dataclass
class GraphModel:
    """Knoten in Schreibreihenfolge und Kanten; `nodes` bildet den Namen auf die Zelle ab."""

    nodes: dict[str, Cell] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)

    def __bool__(self) -> bool:
        """Leer heißt: keine Knoten."""
        return bool(self.nodes)

    def add_node(self, name: str, show: str = "both") -> None:
        """Merkt sich einen Knoten; der erste Eintrag bestimmt die Sichtbarkeit."""
        if name not in self.nodes:
            self.nodes[name] = make_cell(name, show)


def auto_layout(sizes, edges, **tree_options) -> Layout:
    """Baum als Baum, sonst freie Anordnung.

    Args:
        sizes: `{knoten: (breite, höhe)}`.
        edges: Kanten `(a, b)`.
        **tree_options: Weitergabe an `tree_layout` (z. B. `gap_major`).
    """
    tree = tree_children(sizes, edges)
    if tree is not None and len(sizes) > 1:
        root, children = tree
        return tree_layout(sizes, children, root, **tree_options)
    return free_layout(sizes, edges)
