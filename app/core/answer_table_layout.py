"""Geometrie der `:::table`-Antworttabelle (ohne HTML): Zeilen/Spalten, Kopfzeilen,
Zellmatrix und Spaltenbreiten.

Einzige Quelle fuer diese Regeln: der Renderer (`blatt_kern_answer_table`) und der
Validator (`blatt_validator_tables`, AN020/AN021) rechnen beide hiermit, damit eine
Warnung nie von dem abweicht, was tatsaechlich gesetzt wird.

Breitenregel (`widths=`), gilt fuer die Datenspalten (``cols``):

- genau ``cols`` Werte: Datenspalten. Mit `row_headers` bekommt die Kopfspalte bei
  relativen Gewichten das *mittlere* Gewicht der Datenspalten (frueher erhielt sie
  nichts und wurde auf Wortbreite zusammengedrueckt); bei festen CSS-Laengen bleibt sie
  automatisch breit.
- ``cols + 1`` Werte mit `row_headers`: der erste Wert gilt fuer die Kopfspalte.
- jede andere Anzahl: wie bisher ignoriert bzw. abgeschnitten -- AN020 warnt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .answer_table_content import parse_table_content_payload
from .blatt_kern_shared import _safe_int

_RATIO_RE = re.compile(r"(\d+(?:\.\d+)?)(?:fr)?")
_EXPLICIT_RE = re.compile(r"\d+(?:\.\d+)?(%|px|cm|mm|in|pt|em|rem|vh|vw)")


@dataclass
class TableLayout:
    """Aufgeloeste Tabellenform: Groesse, Kopfzeilen und Zellmatrix."""

    rows: int
    cols: int
    column_headers: list[str] = field(default_factory=list)
    row_headers: list[str] = field(default_factory=list)
    cells: list = field(default_factory=list)
    extra_solution_text: str = ""

    @property
    def has_row_header_column(self) -> bool:
        """True, wenn `row_headers` eine zusaetzliche erste Spalte erzeugt."""
        return bool(self.row_headers)


def parse_positional_option_list(raw_value) -> list[str]:
    """Parst Listenwerte aus `a|b|c` oder `a,b,c` positionsgetreu.

    Leere Eintraege (z. B. durch `||`) bleiben als eigene Position erhalten, damit
    Header-Optionen gezielt einzelne Zellen leer lassen koennen.
    """
    if not raw_value:
        return []
    normalized = str(raw_value).replace(",", "|")
    return [item.strip() for item in normalized.split("|")]


def resolve_table_layout(options, content) -> TableLayout:
    """Zeilen/Spalten aus `rows`/`cols`, Kopfzeilen und `cells:` (das Groesste gewinnt)."""
    cols = max(1, _safe_int(options.get("cols", 2), 2))
    rows = max(1, _safe_int(options.get("rows", 4), 4))
    column_headers = parse_positional_option_list(options.get("column_headers"))
    row_headers = parse_positional_option_list(options.get("row_headers"))
    cells, extra_solution_text = parse_table_content_payload(content)
    cols = max(cols, len(column_headers), max((len(row) for row in cells), default=0))
    rows = max(rows, len(row_headers), len(cells))
    return TableLayout(rows, cols, column_headers, row_headers, cells, extra_solution_text)


def width_tokens(widths_raw) -> list[str]:
    """Zerlegt `widths=` in Einzelwerte (Trenner: Leerzeichen, Komma, Doppelpunkt)."""
    normalized = str(widths_raw or "").replace(":", " ").replace(",", " ")
    return [part.strip().lower() for part in normalized.split() if part.strip()]


def parse_table_widths(widths_raw, expected_cols) -> list[str]:
    """CSS-Breiten fuer ``expected_cols`` Spalten aus `widths=` (``[]`` = ungueltig/keine).

    Relative Gewichte (``2``, ``2fr``) werden zu Prozent normiert, feste CSS-Laengen
    unveraendert uebernommen; gemischte Angaben oder zu wenige Werte ergeben ``[]``.

    Example:
        >>> parse_table_widths("1 3", 2)
        ['25.0000%', '75.0000%']
    """
    parts = width_tokens(widths_raw)
    if expected_cols < 1 or len(parts) < expected_cols:
        return []
    ratios, explicit = [], []
    for part in parts[:expected_cols]:
        ratio = _ratio_value(part)
        if ratio is not None:
            if ratio <= 0:
                return []
            ratios.append(ratio)
        elif _EXPLICIT_RE.fullmatch(part):
            explicit.append(part)
        else:
            return []
    if ratios and explicit:
        return []
    if explicit:
        return explicit
    total = sum(ratios)
    return [f"{(value / total) * 100:.4f}%" for value in ratios]


def resolve_table_column_widths(widths_raw, data_cols, has_row_header) -> tuple[str | None, list[str]]:
    """Breiten nach der Modulregel: ``(kopfspalte_oder_None, datenspalten)``.

    Example:
        >>> resolve_table_column_widths("1 3", 2, True)[0]
        '33.3333%'
    """
    tokens = width_tokens(widths_raw)
    if has_row_header and len(tokens) == data_cols + 1:
        widths = parse_table_widths(widths_raw, data_cols + 1)
        return (widths[0], widths[1:]) if widths else (None, [])
    data_widths = parse_table_widths(widths_raw, data_cols)
    if not (has_row_header and data_widths):
        return None, data_widths
    ratios = [_ratio_value(token) for token in tokens[:data_cols]]
    if any(value is None for value in ratios):
        return None, data_widths  # feste Laengen: Kopfspalte bleibt automatisch
    mean = sum(ratios) / len(ratios)
    widths = parse_table_widths(" ".join(str(v) for v in [mean, *ratios]), data_cols + 1)
    return widths[0], widths[1:]


def widths_count_mismatch(widths_raw, data_cols, has_row_header) -> tuple[int, tuple[int, ...]] | None:
    """``(angegeben, erlaubt)`` wenn die Anzahl der `widths`-Werte nicht passt, sonst None."""
    count = len(width_tokens(widths_raw))
    if not count:
        return None
    allowed = (data_cols, data_cols + 1) if has_row_header else (data_cols,)
    return None if count in allowed else (count, allowed)


def _ratio_value(token: str) -> float | None:
    """Zahlenwert eines relativen Gewichts (``2`` oder ``2fr``), sonst None."""
    match = _RATIO_RE.fullmatch(token)
    return float(match.group(1)) if match else None
