"""Zahlen in Diagrammblöcken: lesen, anzeigen, Achsen und Quartile.

Einzige Quelle für die Schreibweisen `3,5`, `3.5`, `1/3` und `50%`. Gerechnet wird mit
`Fraction`, damit Lösungen exakt bleiben und `1/3 + 2/3` wirklich 1 ist.
"""

from __future__ import annotations

import math
import re
from fractions import Fraction

_NUMBER_RE = re.compile(r"^[-+]?\d+(?:[.,]\d+)?$")
_FRACTION_RE = re.compile(r"^([-+]?\d+)\s*/\s*(\d+)$")
_LIST_SPLIT_RE = re.compile(r";|,\s+")
_MAX_DECIMALS = 4
_NICE_STEPS = (1, 2, 5, 10)


def parse_number(text: str) -> Fraction | None:
    """Liest eine Zahl; `None`, wenn es keine ist.

    Args:
        text: `3`, `3,5`, `3.5`, `1/3` oder `50%`.
    """
    value = str(text).strip()
    percent = value.endswith("%")
    if percent:
        value = value[:-1].strip()
    fraction = _FRACTION_RE.match(value)
    if fraction:
        if not int(fraction.group(2)):
            return None
        result = Fraction(int(fraction.group(1)), int(fraction.group(2)))
    elif _NUMBER_RE.match(value):
        result = Fraction(value.replace(",", "."))
    else:
        return None
    return result / 100 if percent else result


def split_numbers(text: str) -> list[str]:
    """Trennt eine Liste an `;` oder `, `; ein Komma ohne Leerzeichen bleibt Dezimalkomma."""
    return [part.strip() for part in _LIST_SPLIT_RE.split(str(text)) if part.strip()]


def format_number(value: Fraction) -> str:
    """Anzeige mit Dezimalkomma; was nicht endlich aufgeht, bleibt ein Bruch."""
    if value.denominator == 1:
        return str(value.numerator)
    denominator = value.denominator
    for factor in (2, 5):
        while denominator % factor == 0:
            denominator //= factor
    if denominator == 1:
        text = f"{float(value):.{_MAX_DECIMALS}f}".rstrip("0").rstrip(".")
        return text.replace(".", ",")
    return f"{value.numerator}/{value.denominator}"


def nice_ticks(low: float, high: float, target: int = 5) -> list[float]:
    """Achsenmarken in runden Schritten (1, 2, 5 mal Zehnerpotenz), die `low` bis `high` abdecken."""
    if high <= low:
        high = low + 1.0
    raw = (high - low) / max(1, target)
    power = 10 ** math.floor(math.log10(raw))
    step = next(multiple * power for multiple in _NICE_STEPS if multiple * power >= raw)
    first = math.floor(low / step)
    last = math.ceil(high / step)
    return [round(index * step, 10) for index in range(first, last + 1)]


def median(values: list[Fraction]) -> Fraction:
    """Median einer sortierten, nicht leeren Liste."""
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) / 2


def five_numbers(values: list[Fraction]) -> tuple[Fraction, Fraction, Fraction, Fraction, Fraction]:
    """Fünf-Punkte-Zusammenfassung für den Boxplot.

    Quartile sind die Mediane der unteren und oberen Hälfte ohne den Median selbst
    (Schulmethode). Die Rechenregel steht in der Blockdoku, andere Werkzeuge können
    abweichen.

    Returns:
        `(minimum, q1, median, q3, maximum)`.
    """
    data = sorted(values)
    half = len(data) // 2
    lower, upper = data[:half], data[-half:] if half else data
    if not lower:
        lower = data
    return data[0], median(lower), median(data), median(upper), data[-1]
