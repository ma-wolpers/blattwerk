"""Einzige Schreibweise für Beziehungen: kurze Zeilen wie `A -> B: Text` oder `A - B - C`.

Eine Zeile besteht aus Namen, die durch Operatoren getrennt sind, optional gefolgt von
`: Beschriftung`. Welche Operatoren gelten, legt der Block fest. `-` braucht Leerzeichen
drumherum, weil Namen Bindestriche enthalten dürfen; Pfeile dürfen auch ohne stehen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class EdgeLine:
    """Eine zerlegte Beziehungszeile.

    Attributes:
        names: Namen in Schreibreihenfolge, mindestens zwei.
        operators: Operatoren zwischen den Namen (`len(names) - 1`).
        label: Text hinter dem ersten Doppelpunkt, sonst leer.
    """

    names: tuple[str, ...]
    operators: tuple[str, ...]
    label: str


def _operator_pattern(operators) -> re.Pattern:
    """Regex für die Trennung; längere Operatoren zuerst, `-` nur mit Leerraum."""
    alternatives = []
    for operator in sorted(operators, key=len, reverse=True):
        token = re.escape(operator)
        alternatives.append(rf"\s+({token})\s+" if operator == "-" else rf"\s*({token})\s*")
    return re.compile("|".join(alternatives))


def parse_edge_line(text: str, operators, labels: bool = True) -> EdgeLine | None:
    """Zerlegt eine Beziehungszeile.

    Der erste Doppelpunkt trennt die Beschriftung ab; Operatoren dahinter zählen nicht
    (`q0 -> q1: (#, a) : #`).

    Args:
        text: Zeile ohne Einrückung und Marker.
        operators: Erlaubte Operatoren des Blocks.
        labels: Ob der Block Beschriftungen kennt. Ohne bleibt ein Doppelpunkt Teil des
            Namens (ER-Diagramm: `Mitarbeiter:in`).

    Returns:
        `EdgeLine`, oder `None`, wenn die Zeile keine vollständige Beziehung ist.
    """
    head, _colon, label = str(text).partition(":") if labels else (str(text), "", "")
    names: list[str] = []
    found: list[str] = []
    position = 0
    for match in _operator_pattern(operators).finditer(head):
        names.append(head[position: match.start()].strip())
        found.append(next(group for group in match.groups() if group))
        position = match.end()
    if not found:
        return None
    names.append(head[position:].strip())
    if not all(names):
        return None
    return EdgeLine(tuple(names), tuple(found), label.strip())
