"""Automatisches Layout für Diagramme: Ebenen, Reihenfolge, Koordinaten (Sugiyama-Verfahren).

Rein und deterministisch: Knoten behalten ihre Schreibreihenfolge als Vorgabe, nirgends
ist Zufall im Spiel. Die Größen kommen als Schätzung von außen.

GRENZE: Eine Kante, die mehrere Ebenen überspringt, läuft gerade und kann einen Knoten
dazwischen schneiden. Dummy-Knoten wären genauer, lohnen sich für die kleinen
Schuldiagramme aber nicht.
"""

from __future__ import annotations

from dataclasses import dataclass

_SWEEPS = 6
_ALIGN_ROUNDS = 8


@dataclass(frozen=True)
class Layout:
    """Ergebnis eines Layouts.

    Attributes:
        centers: Mittelpunkt je Knoten.
        width: Benötigte Breite inklusive Rand.
        height: Benötigte Höhe inklusive Rand.
    """

    centers: dict[str, tuple[float, float]]
    width: float
    height: float


def _acyclic(nodes, edges) -> list[tuple[str, str]]:
    """Lässt Kanten weg, die einen Kreis schließen (Tiefensuche in Schreibreihenfolge)."""
    successors: dict[str, list[str]] = {node: [] for node in nodes}
    for source, target in edges:
        if source != target:
            successors[source].append(target)
    kept: list[tuple[str, str]] = []
    state: dict[str, int] = {}

    def visit(node: str) -> None:
        state[node] = 1
        for target in successors[node]:
            if state.get(target) == 1:
                continue
            kept.append((node, target))
            if target not in state:
                visit(target)
        state[node] = 2

    for node in nodes:
        if node not in state:
            visit(node)
    return kept


def _ranks(nodes, rank_edges, order_edges) -> dict[str, int]:
    """Ebene je Knoten: längster Weg über `rank_edges`.

    Knoten ohne solche Kante kommen auf die Ebene ihres ersten Nachbarn über
    `order_edges` (Assoziationen liegen nebeneinander), sonst auf Ebene 0.
    """
    ranked = {node: 0 for node in nodes}
    acyclic = _acyclic(nodes, rank_edges)
    for _ in nodes:
        for source, target in acyclic:
            ranked[target] = max(ranked[target], ranked[source] + 1)
    constrained = {node for edge in acyclic for node in edge}
    for _ in nodes:
        for first, second in order_edges:
            for node, other in ((first, second), (second, first)):
                if node not in constrained and (other in constrained or other == first):
                    if other in constrained:
                        ranked[node] = ranked[other]
                        constrained.add(node)
    return ranked


def _neighbours(nodes, edges) -> dict[str, list[str]]:
    """Ungerichtete Nachbarn je Knoten, ohne Selbstkanten."""
    result: dict[str, list[str]] = {node: [] for node in nodes}
    for first, second in edges:
        if first != second:
            result[first].append(second)
            result[second].append(first)
    return result


def _ordered_rows(nodes, ranked, neighbours) -> list[list[str]]:
    """Reihenfolge je Ebene: Baryzentrum-Sortierung über mehrere Durchläufe.

    Die Sortierung ist stabil, also entscheidet bei Gleichstand die Schreibreihenfolge.
    """
    rows: list[list[str]] = [[] for _ in range(max(ranked.values()) + 1)]
    for node in nodes:
        rows[ranked[node]].append(node)
    for sweep in range(_SWEEPS):
        indices = range(len(rows)) if sweep % 2 == 0 else range(len(rows) - 1, -1, -1)
        for index in indices:
            position = {node: i for row in rows for i, node in enumerate(row)}

            def barycentre(node: str) -> float:
                others = [position[other] for other in neighbours[node] if ranked[other] != ranked[node]]
                return sum(others) / len(others) if others else position[node]

            rows[index] = sorted(rows[index], key=barycentre)
    return rows


def _separate(values: list[float], extents: list[float], gap: float) -> list[float]:
    """Schiebt Mittelpunkte auseinander, bis Abstände stimmen, möglichst wenig verschoben."""
    forward = list(values)
    for i in range(1, len(forward)):
        forward[i] = max(forward[i], forward[i - 1] + (extents[i - 1] + extents[i]) / 2 + gap)
    backward = list(values)
    for i in range(len(backward) - 2, -1, -1):
        backward[i] = min(backward[i], backward[i + 1] - (extents[i + 1] + extents[i]) / 2 - gap)
    return [(a + b) / 2 for a, b in zip(forward, backward)]


def layered_layout(sizes, rank_edges, order_edges=(), *, direction="TB", gap_major=48.0, gap_minor=32.0, margin=12.0) -> Layout:
    """Berechnet ein Ebenen-Layout.

    Args:
        sizes: `{knoten: (breite, höhe)}` in Schreibreihenfolge.
        rank_edges: Gerichtete Kanten `(oben, unten)`, die die Ebenen bestimmen.
        order_edges: Weitere Kanten, die nur Reihenfolge und Lage beeinflussen.
        direction: `TB` (von oben nach unten) oder `LR` (von links nach rechts).
        gap_major: Abstand zwischen Ebenen.
        gap_minor: Abstand innerhalb einer Ebene.
        margin: Rand um das ganze Diagramm.

    Returns:
        Das `Layout`; ohne Knoten ein leeres.
    """
    nodes = list(sizes)
    if not nodes:
        return Layout({}, 0.0, 0.0)
    horizontal = direction == "LR"
    major = {node: sizes[node][0 if horizontal else 1] for node in nodes}
    minor = {node: sizes[node][1 if horizontal else 0] for node in nodes}
    all_edges = list(rank_edges) + list(order_edges)
    ranked = _ranks(nodes, rank_edges, order_edges)
    neighbours = _neighbours(nodes, all_edges)
    rows = _ordered_rows(nodes, ranked, neighbours)

    place: dict[str, float] = {}
    for row in rows:
        cursor = 0.0
        for node in row:
            place[node] = cursor + minor[node] / 2
            cursor += minor[node] + gap_minor
    for _ in range(_ALIGN_ROUNDS):
        for row in rows:
            desired = []
            for node in row:
                others = [place[other] for other in neighbours[node] if ranked[other] != ranked[node]]
                desired.append(sum(others) / len(others) if others else place[node])
            for node, value in zip(row, _separate(desired, [minor[n] for n in row], gap_minor)):
                place[node] = value

    lowest = min(place[node] - minor[node] / 2 for node in nodes)
    cross = {node: place[node] - lowest + margin for node in nodes}
    along: dict[str, float] = {}
    cursor = margin
    for row in rows:
        depth = max((major[node] for node in row), default=0.0)
        for node in row:
            along[node] = cursor + depth / 2
        cursor += depth + gap_major
    total_along = cursor - gap_major + margin
    total_cross = max(cross[node] + minor[node] / 2 for node in nodes) + margin
    if horizontal:
        return Layout({node: (along[node], cross[node]) for node in nodes}, total_along, total_cross)
    return Layout({node: (cross[node], along[node]) for node in nodes}, total_cross, total_along)
