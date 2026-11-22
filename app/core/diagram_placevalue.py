"""`:::placevalue`: Stellenwerttafel wie im Schulbuch, als HTML-Tabelle (`diagram-table`).

Fest dabei: dicker Strich nach den Einern, Komma hinter jeder Einerziffer, getönter Kopf
(Tabellenköpfe bleiben laut `worksheet.css` immer getönt). Optionen (Konzept mit der
Lehrkraft, 2026-11-22):

* ``from``/``to`` Spaltenbereich (`diagram_placevalue_model`), ``rows`` Mindestzeilen --
  fehlende Zeilen bleiben leer, so entsteht auch eine leere Vorlage.
* ``values`` Stellenwertzeile im Kopf (``… 10 1 1/10 …``); ohne Angabe nur, wenn die Tafel
  Nachkommastellen hat.
* ``colors`` ``none`` | ``decimals`` (Standard, wie im Buch) | ``all``: Töne aus der
  Datenpalette des Farbprofils (im S/W-Profil Grau), Kopf kräftiger als die Zellen.
* ``comma`` (Standard ja): Komma auch in leeren Einerzellen vorgedruckt.
* ``labels`` ``none`` (Standard) | ``numbers`` | ``letters``: Zeilen 1) 2) bzw. a) b) links
  außerhalb der Tafel (Buchstaben gehören sonst eher zu Teilaufgaben).
* ``fraction`` ``mixed`` | ``improper``: Zusatzspalte mit dem Wert als Bruch mit
  Zehnerpotenz-Nenner. Sie ist im Arbeitsblatt offen, wenn die Zeile eine Lücke hat oder
  ``fraction_gap`` gesetzt ist (Tafel gegeben, Bruch gesucht).

GRENZE: Die Spaltenkürzel sind deutsche Schulbuch-Notation und bleiben auch bei
``Sprache: pt-BR`` stehen; nur der Kopf der Bruchspalte folgt der Dokumentsprache.
"""

from __future__ import annotations

from html import escape

from .diagram_placevalue_model import NAME_OF, Columns, Row, Table, fraction_tex, parse, resolve_columns, row_value
from .diagram_svg import width_style
from .diagram_text import Cell, make_cell, option_flag, render_cell
from .document_language import label, language_from_options

__all__ = ["check", "estimate_weight", "is_empty", "parse", "render"]

_TONE_COUNT = 8
_COLOR_MODES = ("none", "decimals", "all")
_LABEL_STYLES = ("none", "numbers", "letters")
_FRACTION_MODES = ("mixed", "improper")


def _choice(options, key: str, allowed: tuple[str, ...], default: str | None) -> str | None:
    """Enum-Option, klein geschrieben; unbekannt oder fehlend ergibt den Standard."""
    value = str((options or {}).get(key) or "").strip().lower()
    return value if value in allowed else default


def _min_rows(options) -> int | None:
    """`rows` als Zahl ab 0; ``None``, wenn die Angabe fehlt oder keine Zahl ist."""
    raw = str((options or {}).get("rows") or "").strip()
    return int(raw) if raw.isdigit() else None


def is_empty(options, table: Table) -> bool:
    """Leer ist die Tafel nur ohne Zeilen *und* ohne `rows` (leere Vorlage ist nicht leer)."""
    return not table and not (_min_rows(options) or 0)


def _tone(exponent: int, colors: str) -> str:
    """CSS-Klasse des Spaltentons; Nachkommastellen zuerst, damit sie wie im Buch je eine Farbe haben."""
    if exponent < 0 and colors != "none":
        return f" pv-tone-{(-exponent - 1) % _TONE_COUNT + 1}"
    if exponent >= 0 and colors == "all":
        return f" pv-tone-{(exponent + 5) % _TONE_COUNT + 1}"
    return ""


def _column_classes(exponent: int, colors: str) -> str:
    """Klassen einer Spalte: Ton und dicker Strich nach den Einern."""
    return f"pv-col{_tone(exponent, colors)}{' pv-ones' if exponent == 0 else ''}"


def _place_value_tex(exponent: int) -> str:
    """Stellenwert einer Spalte für die Kopfzeile: ``10``, ``1`` oder ``\\frac{1}{10}``."""
    return str(10**exponent) if exponent >= 0 else f"$\\frac{{1}}{{{10 ** -exponent}}}$"


def _row_label(index: int, style: str) -> str:
    """Zeilenbeschriftung ``1)`` oder ``a)`` (nach ``z)`` weiter mit ``aa)``)."""
    if style == "numbers":
        return f"{index + 1})"
    letters = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(ord("a") + rest) + letters
    return f"{letters})"


def _row_cells(row: Row | None, columns: Columns) -> list[tuple[int, Cell | None]]:
    """Zelleninhalt je Spalte (``None`` = leer) für eine Zahl-, Zellen- oder Leerzeile."""
    if row is None:
        return [(exponent, None) for exponent in columns.exponents]
    if row.cells is not None:
        texts = list(row.cells) + [""] * len(columns.exponents)
        return [(exponent, make_cell(text, row.show) if text else None) for exponent, text in zip(columns.exponents, texts)]
    by_place = {digit.exponent: digit for digit in row.digits}
    return [
        (exponent, Cell(({"text": by_place[exponent].numeral, "show": by_place[exponent].show},)) if exponent in by_place else None)
        for exponent in columns.exponents
    ]


def _with_comma(cell: Cell | None, comma: bool) -> Cell | None:
    """Hängt das Komma an die Einerzelle; ohne Vordruck nur mit der Sichtbarkeit der Ziffer."""
    if comma:
        return Cell(((cell.segments if cell else ()) + ({"text": ",", "show": "both"},)))
    if cell is None:
        return None
    return Cell(cell.segments + ({"text": ",", "show": cell.segments[-1]["show"]},))


def _has_gap(cells: list[tuple[int, Cell | None]]) -> bool:
    """Ob in der Zeile etwas nur in der Lösung steht (dann verriete der Bruch die Antwort)."""
    return any(segment["show"] == "solution" for _e, cell in cells if cell for segment in cell.segments)


def _fraction_cell(row: Row | None, columns: Columns, options, gap: bool, include_solutions: bool) -> str:
    """Zelle der Bruchspalte; offen, wenn die Zeile eine Lücke hat oder `fraction_gap` gilt."""
    value = row_value(row, columns.exponents) if row is not None else None
    if value is None:
        return ""
    tex = fraction_tex(value[0], value[1], _choice(options, "fraction", _FRACTION_MODES, None) == "improper")
    show = "solution" if gap or option_flag(options, "fraction_gap") else "both"
    return render_cell(Cell(({"text": f"${tex}$", "show": show},)), include_solutions)[0]


def _body_row(index, row, columns, options, include_solutions) -> str:
    """Eine Tabellenzeile mit Ziffern, Komma, optionaler Beschriftung und Bruch."""
    colors = _choice(options, "colors", _COLOR_MODES, "decimals")
    comma = option_flag(options, "comma") is not False
    style = _choice(options, "labels", _LABEL_STYLES, "none")
    cells = _row_cells(row, columns)
    parts = []
    for position, (exponent, cell) in enumerate(cells):
        cell = _with_comma(cell, comma) if exponent == 0 else cell
        html = render_cell(cell, include_solutions)[0] if cell else ""
        label_attr = f" data-label='{escape(_row_label(index, style))}'" if position == 0 and style != "none" else ""
        parts.append(f"<td class='{_column_classes(exponent, colors)}'{label_attr}>{html}</td>")
    if _choice(options, "fraction", _FRACTION_MODES, None):
        gap = _has_gap(cells) or (row is not None and row.show == "solution")
        parts.append(f"<td class='pv-fraction'>{_fraction_cell(row, columns, options, gap, include_solutions)}</td>")
    return f"<tr>{''.join(parts)}</tr>"


def _head(columns: Columns, options) -> str:
    """Kopf: Kürzel, optional die Stellenwertzeile und der Kopf der Bruchspalte."""
    colors = _choice(options, "colors", _COLOR_MODES, "decimals")
    values = option_flag(options, "values")
    if values is None:
        values = any(exponent < 0 for exponent in columns.exponents)
    span = " rowspan='2'" if values else ""
    names = "".join(f"<th class='{_column_classes(e, colors)}'>{escape(NAME_OF[e])}{',' if e == 0 else ''}</th>" for e in columns.exponents)
    if _choice(options, "fraction", _FRACTION_MODES, None):
        names += f"<th class='pv-fraction'{span}>{escape(label('placevalue_fraction', language_from_options(options)))}</th>"
    head = f"<tr>{names}</tr>"
    if values:
        cells = "".join(
            f"<th class='{_column_classes(e, colors)} pv-value'>{render_cell(make_cell(_place_value_tex(e)), True)[0]}</th>"
            for e in columns.exponents
        )
        head += f"<tr>{cells}</tr>"
    return f"<thead>{head}</thead>"


def render(options, content, include_solutions=False) -> str:
    """Rendert die Tafel; eine leere Tafel ohne `rows` ergibt nichts."""
    table, _issues = parse(content)
    options = options or {}
    if is_empty(options, table):
        return ""
    columns = resolve_columns(options, table)
    rows: list[Row | None] = list(table.rows)
    rows += [None] * max(0, (_min_rows(options) or 0) - len(rows))
    body = "".join(_body_row(index, row, columns, options, include_solutions) for index, row in enumerate(rows))
    labeled = " pv-labeled" if _choice(options, "labels", _LABEL_STYLES, "none") != "none" else ""
    style = width_style(options)
    style_attr = f" style='{style}'" if style else ""
    return (
        f"<div class='diagram diagram-placevalue'><table class='diagram-table pv-table{labeled}'{style_attr}>"
        f"{_head(columns, options)}<tbody>{body}</tbody></table></div>"
    )


def check(collect, options, table: Table) -> None:
    """Fachliche Prüfungen: Spaltenbereich (`PV004`-`PV006`), Zellenzahl (`PV003`), `rows` (`PV007`)."""
    columns = resolve_columns(options, table)
    for code, message in columns.problems:
        collect.add(code, message, "error" if code == "PV004" else "warning")
    for row in table.rows:
        if row.cells is not None and len(row.cells) != len(columns.exponents):
            collect.add(
                "PV003",
                f"Zeile {row.line} im Block: {len(row.cells)} Zellen, die Tafel hat {len(columns.exponents)} Spalten.",
                "error",
                f"PV003:{row.line}",
            )
    if str(options.get("rows") or "").strip() and _min_rows(options) is None:
        collect.add("PV007", "`rows` muss eine ganze Zahl ab 0 sein.")


def estimate_weight(options, content) -> float:
    """Layoutgewicht: wächst mit Spalten- und Zeilenzahl (auch für leere Vorlagen)."""
    table, _issues = parse(content)
    columns = resolve_columns(options or {}, table)
    rows = max(len(table.rows), _min_rows(options) or 0)
    return 0.6 + 0.12 * len(columns.exponents) + 0.18 * rows
