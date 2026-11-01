"""`:::venn`: Venn- und Mengendiagramm für 2–3 Mengen.

Syntax: eine Zeile pro Bereich, `A: 2, 4` und `A B: 6`, `rest: 9` außerhalb aller Mengen
(zeichnet dann die Grundmenge als Rechteck). Lücken: `%` am Zeilenanfang oder `%{6}`.

`variant=compare` macht daraus einen Schreibrahmen: größere Felder mit umbrochenem Text,
zum Beispiel `Hund: bellt`, `Hund Katze: Haustier`.
"""

from __future__ import annotations

from dataclasses import dataclass

from .diagram_svg import LINE_HEIGHT, Canvas, text_width
from .diagram_text import Cell, ParseIssue, iter_source_lines, make_cell, plain_cell

_REST = "rest"
_SIZES = {"plain": (86.0, 56.0), "compare": (130.0, 78.0)}
_AWAY_SHARE = {1: 0.22, 2: 0.3}
"""Wie weit ein Bereich aus 1 oder 2 Mengen von den übrigen Mengen wegrückt."""
"""Kreisradius und Abstand der Mittelpunkte je Variante."""
_MARGIN = 16.0
_TITLE = 22.0
_REST_ROW = 30.0


@dataclass(frozen=True)
class Region:
    """Ein Bereich: die Mengen, zu denen er gehört, und sein Text."""

    line: int
    sets: tuple[str, ...]
    text: Cell


def parse(content) -> tuple[list[Region], list[ParseIssue]]:
    """Parst die Bereiche fehlertolerant (`VN002`)."""
    regions: list[Region] = []
    issues: list[ParseIssue] = []
    for source in iter_source_lines(content):
        names, colon, text = source.text.partition(":")
        sets = tuple(names.split())
        if not colon or not sets:
            issues.append(ParseIssue("VN002", "error", source.number, "Erwartet `A: 2, 4`, `A B: 6` oder `rest: 9`."))
            continue
        regions.append(Region(source.number, sets, make_cell(text.strip(), source.show)))
    return regions, issues


def set_names(regions: list[Region]) -> list[str]:
    """Mengennamen in Reihenfolge des ersten Auftretens, ohne `rest`."""
    names: list[str] = []
    for region in regions:
        for name in region.sets:
            if name != _REST and name not in names:
                names.append(name)
    return names


def check(collect, options, regions: list[Region]) -> None:
    """Prüft Mengenzahl, doppelte Bereiche und doppelte Elemente (`VN003`-`VN005`)."""
    names = set_names(regions)
    if not 2 <= len(names) <= 3:
        collect.add("VN003", f"Ein Venn-Diagramm braucht 2 oder 3 Mengen, hier sind es {len(names)}.", severity="error")
    seen: set[frozenset] = set()
    for region in regions:
        key = frozenset(region.sets)
        if key in seen:
            collect.add("VN004", f"Der Bereich `{' '.join(region.sets)}` steht doppelt.", severity="error", anchor=f"VN004:{region.line}")
        seen.add(key)
    if str(options.get("variant") or "") == "compare":
        return
    owner: dict[str, Region] = {}
    for region in regions:
        for item in (part.strip() for part in region.text.text.split(",")):
            if item in owner and item:
                collect.add("VN005", f"`{item}` steht in zwei Bereichen; jedes Element gehört in genau einen.", anchor=f"VN005:{item}")
            owner.setdefault(item, region)


def _centers(count: int, distance: float, radius: float) -> list[tuple[float, float]]:
    """Kreismittelpunkte relativ zur linken oberen Ecke der Zeichnung."""
    if count == 2:
        return [(radius, radius), (radius + distance * 2, radius)]
    height = distance * 1.73
    return [(radius, radius), (radius + distance * 2, radius), (radius + distance, radius + height)]


def _region_spot(sets, names, centers) -> tuple[float, float]:
    """Mitte eines Bereichs: Schwerpunkt seiner Mengen, ein Stück weg von den übrigen."""
    inside = [centers[names.index(name)] for name in sets]
    x = sum(p[0] for p in inside) / len(inside)
    y = sum(p[1] for p in inside) / len(inside)
    if len(inside) == len(names):
        return x, y
    outside = [centers[i] for i, name in enumerate(names) if name not in sets]
    away_x = sum(p[0] for p in outside) / len(outside)
    away_y = sum(p[1] for p in outside) / len(outside)
    share = _AWAY_SHARE[len(inside)]
    return x + (x - away_x) * share, y + (y - away_y) * share


def _field_width(sets, count: int, radius: float, distance: float) -> float:
    """Breite, die in einem Bereich für Text frei ist; die Schnittlinse ist schmal."""
    if len(sets) == 1:
        return radius * (1.0 if count == 2 else 0.9)
    return max(radius * 0.5, 2 * (radius - distance) * 0.9)


def render(options, content, include_solutions=False) -> str:
    """Rendert das Diagramm; außerhalb von 2–3 Mengen nichts (der Validator meldet es)."""
    regions, _issues = parse(content)
    names = set_names(regions)
    if not 2 <= len(names) <= 3:
        return ""
    compare = str((options or {}).get("variant") or "") == "compare"
    radius, distance = _SIZES["compare" if compare else "plain"]
    centers = _centers(len(names), distance, radius)
    canvas = Canvas(include_solutions)
    left, top = _MARGIN, _MARGIN + _TITLE
    width = max(c[0] for c in centers) + radius + 2 * _MARGIN
    height = max(c[1] for c in centers) + radius + _TITLE + 2 * _MARGIN
    rest = next((region for region in regions if region.sets == (_REST,)), None)
    if rest is not None:
        height += _REST_ROW
        canvas.rect(width / 2, height / 2, width - 4, height - 4)
    for name, (x, y) in zip(names, centers):
        canvas.ellipse(left + x, top + y, radius, radius, "diagram-line")
        title_y = top + y - radius - _TITLE / 2 + 2 if y == radius else top + y + radius + _TITLE / 2 - 2
        canvas.label(plain_cell(name), left + x, title_y, text_width(name) + 12, weight="bold")
    for region in regions:
        if region.sets == (_REST,):
            canvas.label(region.text, width / 2, height - _REST_ROW / 2 - 2, width - 16)
            continue
        if not set(region.sets) <= set(names):
            continue
        x, y = _region_spot(region.sets, names, centers)
        field = _field_width(region.sets, len(names), radius, distance)
        lines = max(1, int(text_width(region.text.text) // field) + 1)
        canvas.label(region.text, left + x, top + y, field, lines * LINE_HEIGHT, wrap=True)
    return canvas.finish("venn", options, width, height)
