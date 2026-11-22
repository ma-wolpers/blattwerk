"""Modell der Stellenwerttafel (`:::placevalue`): Zeilen lesen, Spalten bestimmen, Werte rechnen.

Zwei Schreibweisen je Zeile (Nutzerentscheidung 2026-11-22):

* **Zahl** -- ``52,34`` oder ``52.34``; der Block verteilt die Ziffern auf die Stellen.
  Einzelne Ziffern als Lücke mit ``%{…}`` (``5%{2},3%{4}``), die ganze Zeile mit ``%``.
* **Zellen** -- ``| 1 | 8 | 13 | | |`` für Sonderfälle (13 Zehntel, bewusst leere Stellen);
  eine Zelle je Spalte von ``from`` bis ``to``, deshalb braucht diese Schreibweise beide.

Spaltenkürzel wie im Schulbuch, Groß-/Kleinschreibung zählt: Ganze ``HT ZT T H Z E``,
Nachkommastellen ``z h t zt ht``. Ohne ``from``/``to`` gilt der kleinste Bereich, der alle
Zahlen fasst, mindestens die Einer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction

from .answer_line_markers import parse_answer_line_visibility
from .diagram_text import ParseIssue, iter_source_lines

PLACES = (("HT", 5), ("ZT", 4), ("T", 3), ("H", 2), ("Z", 1), ("E", 0), ("z", -1), ("h", -2), ("t", -3), ("zt", -4), ("ht", -5))
"""Spaltenkürzel und Zehnerexponent ihres Stellenwerts, von groß nach klein."""

EXPONENT_OF = dict(PLACES)
NAME_OF = {exponent: name for name, exponent in PLACES}
_NUMBER_RE = re.compile(r"^(\d+)(?:[.,](\d+))?$")


@dataclass(frozen=True)
class Digit:
    """Eine Ziffer der Zahl-Schreibweise an ihrer Stelle; `show` aus Zeile oder `%{…}`."""

    exponent: int
    numeral: str
    show: str


@dataclass(frozen=True)
class Row:
    """Eine Zeile der Tafel: entweder Ziffern (Zahl) oder rohe Zellen (Zellen-Schreibweise)."""

    line: int
    show: str
    digits: tuple[Digit, ...] = ()
    cells: tuple[str, ...] | None = None


@dataclass(frozen=True)
class Table:
    """Alle Zeilen des Blockinhalts; falsy ohne Zeile (Leere entscheidet `is_empty`)."""

    rows: tuple[Row, ...]

    def __bool__(self) -> bool:
        """Wahr, sobald der Inhalt mindestens eine Zeile hat."""
        return bool(self.rows)


def _segments(text: str, show: str) -> list[tuple[str, str]]:
    """Zerlegt Text mit `%{…}`-Markern in Zeichen samt Sichtbarkeit (Leerraum fällt weg)."""
    parsed = parse_answer_line_visibility(text, default_show=show)
    return [(char, segment["show"]) for segment in parsed["segments"] for char in segment["text"] if not char.isspace()]


def plain_text(text: str) -> str:
    """Text einer Zelle ohne Marker (für Werte und Prüfungen)."""
    return "".join(char for char, _show in _segments(text, "both"))


def _parse_number(text: str, show: str) -> tuple[Digit, ...] | None:
    """Ziffern einer Zahl mit Stellen; ``None``, wenn es keine Zahl wie ``52,34`` ist."""
    chars = _segments(text, show)
    match = _NUMBER_RE.match("".join(char for char, _show in chars))
    if not match:
        return None
    integer_count = len(match.group(1))
    digits = [(char, char_show) for char, char_show in chars if char.isdigit()]
    return tuple(Digit(integer_count - 1 - index, char, char_show) for index, (char, char_show) in enumerate(digits))


def _split_cells(text: str) -> tuple[str, ...]:
    """Zellen einer `|`-Zeile; die äußeren Striche sind optional (`| 1 | 2 |` = `1 | 2`)."""
    inner = text.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") else inner
    return tuple(cell.strip() for cell in inner.split("|"))


def parse(content) -> tuple[Table, list[ParseIssue]]:
    """Liest die Zeilen fehlertolerant; eine Zeile, die keine Zahl ist, ergibt `PV002`."""
    rows: list[Row] = []
    issues: list[ParseIssue] = []
    for source in iter_source_lines(content):
        if source.text.startswith("|"):
            rows.append(Row(source.number, source.show, cells=_split_cells(source.text)))
            continue
        digits = _parse_number(source.text, source.show)
        if digits is None:
            issues.append(ParseIssue("PV002", "error", source.number, f"`{source.text}` ist keine Zahl wie `52,34` und keine Zellenzeile `| … |`."))
            continue
        rows.append(Row(source.number, source.show, digits=digits))
    return Table(tuple(rows)), issues


@dataclass(frozen=True)
class Columns:
    """Aufgelöster Spaltenbereich: Exponenten von groß nach klein, dazu Probleme für den Validator."""

    exponents: tuple[int, ...]
    problems: tuple[tuple[str, str], ...]


def resolve_columns(options, table: Table) -> Columns:
    """Bestimmt die Spalten aus `from`/`to` oder automatisch aus den Zahlen.

    Unbekannte Kürzel oder ``from`` kleiner als ``to`` ergeben `PV004`, Zellenzeilen ohne
    beide Grenzen `PV006`, Ziffern außerhalb fester Grenzen `PV005`.
    """
    options = options or {}
    problems: list[tuple[str, str]] = []
    digits = [digit.exponent for row in table.rows for digit in row.digits]
    high, low = max([0, *digits]), min([0, *digits])
    bounds = {}
    for key in ("from", "to"):
        raw = str(options.get(key) or "").strip()
        if raw and raw not in EXPONENT_OF:
            problems.append(("PV004", f"`{key}={raw}` ist kein Spaltenkürzel ({' '.join(NAME_OF[e] for _n, e in PLACES)})."))
        elif raw:
            bounds[key] = EXPONENT_OF[raw]
    high, low = bounds.get("from", high), bounds.get("to", low)
    if high < low:
        problems.append(("PV004", "`from` muss links von `to` liegen (z. B. `from=Z to=h`)."))
        high, low = low, high
    if any(row.cells is not None for row in table.rows) and len(bounds) < 2:
        problems.append(("PV006", "Zellenzeilen `| … |` brauchen `from` und `to`, damit klar ist, welche Zelle welche Stelle ist."))
    outside = sorted({NAME_OF.get(e, str(e)) for e in digits if not low <= e <= high})
    if outside:
        problems.append(("PV005", f"Ziffern an Stellen außerhalb der Tafel ({', '.join(outside)}) fallen weg."))
    return Columns(tuple(range(high, low - 1, -1)), tuple(problems))


def row_value(row: Row, exponents: tuple[int, ...]) -> tuple[Fraction, int] | None:
    """Wert der Zeile und Zahl ihrer Nachkommastellen; ``None`` ohne Ziffern oder mit Text in Zellen."""
    if row.cells is None:
        if not row.digits:
            return None
        value = sum(Fraction(int(d.numeral)) * Fraction(10) ** d.exponent for d in row.digits)
        return value, max(0, -min(d.exponent for d in row.digits))
    value, places, seen = Fraction(0), 0, False
    for text, exponent in zip(row.cells, exponents):
        plain = plain_text(text)
        if not plain:
            continue
        if not plain.isdigit():
            return None
        value += int(plain) * Fraction(10) ** exponent
        places, seen = max(places, -exponent), True
    return (value, places) if seen else None


def fraction_tex(value: Fraction, places: int, improper: bool) -> str:
    """Bruch mit Zehnerpotenz-Nenner als TeX: gemischt ``2\\frac{2}{100}`` oder unecht ``\\frac{202}{100}``.

    Example:
        >>> fraction_tex(Fraction(234, 1000), 3, False), fraction_tex(Fraction(202, 100), 2, True)
        ('\\\\frac{234}{1000}', '\\\\frac{202}{100}')
    """
    denominator = 10**places
    numerator = value * denominator
    if places == 0:
        return str(int(value))
    if improper:
        return f"\\frac{{{int(numerator)}}}{{{denominator}}}"
    whole = int(value)
    rest = int(numerator - whole * denominator)
    if rest == 0:
        return str(whole)
    fraction = f"\\frac{{{rest}}}{{{denominator}}}"
    return f"{whole}{fraction}" if whole else fraction
