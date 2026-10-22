"""Inline-Stile `-<SPEC> Text -<>`: Schrift, Größe und Farbe für einen Textbereich.

Einzige Quelle der Syntax für Parser, Validator (`IM004`), Renderer, Editor-
Hervorhebung und VS-Code-Grammatik (`STYLE_MARKER_REGEX`, vom Guardrail
abgeglichen).

Grammatik:
- `-<SPEC>` öffnet, `-<>` schließt; `\\-<` ist ein wörtliches `-<`.
- SPEC = Tokens, getrennt durch `-`: Zahl = Größe in pt (`12`, `10.5`, `10,5`),
  `#name`/`#rgb`/`#rrggbb` = Farbe, sonst Schriftname (Leerzeichen erlaubt, mit
  `-` im Namen in Anführungszeichen: `"Name-mit-Strich"`).
- Je Art höchstens eine Angabe; Verschachtelung erbt pro Eigenschaft.
- Ein Bereich endet spätestens an einer Leerzeile, vor einem Listenpunkt und an
  einer Tabellenzelle (`|` in einer Tabellenzeile); bleibt er dort offen, ist das
  ein Fehler und der Bereich wird an der Grenze geschlossen.
- In Code, Formeln und Kommentaren ist `-<…>` wörtlicher Text (die Stufe läuft
  nach deren Schutz, siehe `spans.protect_all`).

Ablauf: `protect_style_markers` ersetzt gültige Marker durch unsichtbare
Platzhalter (Private-Use U+E004..U+E006), die alle Hervorhebungs-Durchläufe
unverändert passieren; `apply_inline_styles` verteilt danach als letzter
Parser-Schritt den effektiven Stil auf jeden `Run` (auch Formel und Code).
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace

from ...styles.blatt_styles import FONT_PROFILE_PRESETS
from ...styles.bundled_fonts import BUNDLED_FONTS_BY_KEY
from .inline_style import InlineStyle
from .runs import IM004_INVALID_INLINE_STYLE, ParseDiagnostic, Run

STYLE_MARKER_REGEX = r"(?<!\\)-<([^<>\n]*)>"
"""Erkennt `-<SPEC>` und `-<>` (gleiche Regex in Editor und VS-Code-Grammatik)."""

_OPEN_START, _OPEN_END, _CLOSE = "", "", ""
LITERAL_LT_PLACEHOLDER = ""
"""Platzhalter für ein wörtliches `<` aus `\\-<`; aufgelöst in `escaping.py`."""

_MARKER_PATTERN = re.compile(STYLE_MARKER_REGEX)
_TOKEN_PATTERN = re.compile(f"{_OPEN_START}(\\d+){_OPEN_END}|{_CLOSE}")
_BOUNDARY_PATTERN = re.compile(r"\n[ \t]*\n|\n(?=[ \t]*(?:[-*+]|\d+[.)])[ \t])")
_TABLE_LINE_PATTERN = re.compile(r"(?m)^[ \t]*\|.*$")
_NUMBER_PATTERN = re.compile(r"\d+(?:[.,]\d+)?")
_HEX_PATTERN = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})")

STYLE_COLORS = {
    "rot": "#c62828", "red": "#c62828", "blau": "#1565c0", "blue": "#1565c0",
    "gruen": "#2e7d32", "grün": "#2e7d32", "green": "#2e7d32", "gelb": "#f9a825", "yellow": "#f9a825",
    "orange": "#ef6c00", "lila": "#6a1b9a", "violett": "#6a1b9a", "purple": "#6a1b9a",
    "rosa": "#d81b60", "pink": "#d81b60", "braun": "#6d4c41", "brown": "#6d4c41",
    "grau": "#616161", "gray": "#616161", "grey": "#616161", "schwarz": "#000000", "black": "#000000",
    "weiss": "#ffffff", "weiß": "#ffffff", "white": "#ffffff", "tuerkis": "#00897b", "türkis": "#00897b",
    "teal": "#00897b",
}
"""Kuratierte deutsch/englische Farbnamen (`#rot`, `#red`, …); sonst nur Hex."""


def _font_lookup() -> dict[str, tuple[str, str]]:
    """Schriftname (klein) -> (Profilschlüssel, echter Familienname): Schlüssel, Label, Familie."""
    lookup: dict[str, tuple[str, str]] = {}
    for key, preset in FONT_PROFILE_PRESETS.items():
        bundled = BUNDLED_FONTS_BY_KEY.get(key)
        family = bundled.family if bundled else preset["label"]
        for name in (key, preset["label"], family, key.replace("_", " ")):
            lookup.setdefault(name.strip().lower(), (key, family))
    return lookup


def _split_tokens(spec: str) -> list[str] | None:
    """Trennt SPEC an `-` außerhalb von Anführungszeichen; `None` bei offenem Anführungszeichen."""
    tokens, current, quoted = [], "", False
    for char in spec:
        if char == '"':
            quoted = not quoted
            current += char
        elif char == "-" and not quoted:
            tokens.append(current)
            current = ""
        else:
            current += char
    if quoted:
        return None
    tokens.append(current)
    return [token.strip() for token in tokens]


def parse_style_spec(spec: str) -> tuple[InlineStyle | None, str | None]:
    """Liest einen SPEC (Text zwischen `-<` und `>`) in einen `InlineStyle`.

    Returns:
        ``(style, None)`` oder ``(None, Fehlermeldung)``.

    Example:
        >>> parse_style_spec("Arial-#red-12")[0].size_pt
        12.0
    """
    tokens = _split_tokens(spec)
    if tokens is None:
        return None, f"`-<{spec}>`: Anführungszeichen nicht geschlossen."
    values: dict[str, object] = {}
    for token in tokens:
        if not token:
            return None, f"`-<{spec}>`: leere Angabe zwischen zwei `-`."
        if _NUMBER_PATTERN.fullmatch(token):
            kind, value = "size", float(token.replace(",", "."))
            if not 4 <= value <= 120:
                return None, f"`-<{spec}>`: Schriftgröße {token} pt liegt nicht zwischen 4 und 120."
        elif token.startswith("#"):
            kind = "color"
            value = token.lower() if _HEX_PATTERN.fullmatch(token) else STYLE_COLORS.get(token[1:].lower())
            if value is None:
                names = ", ".join(sorted({f"#{name}" for name in STYLE_COLORS}))
                return None, f"`-<{spec}>`: unbekannte Farbe `{token}`. Erlaubt: #rgb, #rrggbb oder {names}."
        else:
            kind = "font"
            value = _font_lookup().get(token.strip('"').strip().lower())
            if value is None:
                return None, f"`-<{spec}>`: unbekannte Schrift `{token}` (Namen wie im Schriftmenü)."
        if kind in values:
            return None, f"`-<{spec}>`: mehr als eine Angabe für {'Schrift' if kind == 'font' else 'Größe' if kind == 'size' else 'Farbe'}."
        values[kind] = value
    font = values.get("font")
    return InlineStyle(
        font_css=FONT_PROFILE_PRESETS[font[0]]["css_family"] if font else None,
        font_key=font[0] if font else None,
        font_family=font[1] if font else None,
        size_pt=values.get("size"),
        color=values.get("color"),
    ), None


def _table_cell_boundaries(text: str) -> list[int]:
    """Positionen der `|` in Markdown-Tabellenzeilen (Zeilen, die mit `|` beginnen).

    Nur dort ist `|` eine Zellgrenze; Spoiler `||…||` im Fließtext bleiben unberührt.
    """
    positions = []
    for line in _TABLE_LINE_PATTERN.finditer(text):
        positions += [line.start() + index for index, char in enumerate(line.group(0)) if char == "|"]
    return positions


def protect_style_markers(text: str) -> tuple[str, list[InlineStyle], list[ParseDiagnostic]]:
    """Ersetzt gültige `-<SPEC>`/`-<>` durch Platzhalter und meldet Fehler als `IM004`.

    Ungültige Marker bleiben als Text stehen (der Fehler blockiert den Build).
    Offene Bereiche werden an jeder Grenze (Leerzeile, Listenpunkt, Tabellenzelle)
    und am Textende geschlossen und als Fehler gemeldet.
    """
    if "-<" not in text:
        return text, [], []
    styles: list[InlineStyle] = []
    diagnostics: list[ParseDiagnostic] = []
    events = [(m.start(), m.end(), "marker", m) for m in _MARKER_PATTERN.finditer(text)]
    events += [(m.start(), m.start(), "boundary", m) for m in _BOUNDARY_PATTERN.finditer(text)]
    events += [(pos, pos, "boundary", None) for pos in _table_cell_boundaries(text)]
    events.sort(key=lambda event: (event[0], event[2] != "boundary"))
    pieces, last = [], 0
    open_valid: list[bool] = []
    """Offene Bereiche von außen nach innen; `False` = ungültiger Öffner (schon gemeldet,
    sein `-<>` bleibt ohne Folgefehler als Text stehen)."""

    def error(message: str, position: int) -> None:
        diagnostics.append(ParseDiagnostic(IM004_INVALID_INLINE_STYLE, "error", message, position))

    def close_all(message: str, position: int) -> None:
        if any(open_valid):
            error(message, position)
        pieces.append(_CLOSE * sum(open_valid))
        open_valid.clear()

    for start, end, kind, match in events:
        if start < last:
            continue
        pieces.append(text[last:start])
        last = start
        if kind == "boundary":
            close_all("Stilbereich `-<…>` vor einer Absatz-, Listen- oder Tabellengrenze nicht mit `-<>` geschlossen.", start)
            continue
        spec = match.group(1)
        if spec == "":
            if not open_valid:
                error("`-<>` schließt keinen offenen Stilbereich.", start)
                pieces.append(match.group(0))
            else:
                pieces.append(_CLOSE if open_valid.pop() else match.group(0))
        else:
            style, message = parse_style_spec(spec)
            if style is None:
                error(message or "", start)
                pieces.append(match.group(0))
            else:
                pieces.append(f"{_OPEN_START}{len(styles)}{_OPEN_END}")
                styles.append(style)
            open_valid.append(style is not None)
        last = end
    pieces.append(text[last:])
    close_all("Stilbereich `-<…>` am Ende nicht mit `-<>` geschlossen.", len(text))
    return "".join(pieces).replace("\\-<", "-" + LITERAL_LT_PLACEHOLDER), styles, diagnostics


def apply_inline_styles(runs: list[Run], styles: list[InlineStyle]) -> list[Run]:
    """Letzter Parser-Schritt: entfernt die Platzhalter und setzt `Run.style` (geerbt).

    Text-Runs werden an den Platzhaltern geteilt; Formel-, Code- und
    Worterklärungs-Runs bekommen den an ihrer Stelle gültigen Stil.
    """
    if not styles and not any(_CLOSE in run.text or _OPEN_START in run.text for run in runs):
        return runs
    stack: list[InlineStyle] = []
    result: list[Run] = []
    for run in runs:
        if run.kind != "text":
            result.append(replace(run, style=stack[-1]) if stack else run)
            continue
        position = 0
        for token in _TOKEN_PATTERN.finditer(run.text):
            if token.start() > position:
                result.append(replace(run, text=run.text[position:token.start()], style=stack[-1] if stack else None))
            if token.group(1) is not None:
                stack.append(styles[int(token.group(1))].inherit_from(stack[-1] if stack else None))
            elif stack:
                stack.pop()
            position = token.end()
        if position < len(run.text):
            result.append(replace(run, text=run.text[position:], style=stack[-1] if stack else None))
    return result


_active_font_collector: ContextVar[set[str] | None] = ContextVar("inline_style_fonts", default=None)


@contextmanager
def collect_inline_style_fonts():
    """Sammelt die Schriftprofil-Schlüssel aller im Kontext gerenderten Inline-Stile."""
    keys: set[str] = set()
    token = _active_font_collector.set(keys)
    try:
        yield keys
    finally:
        _active_font_collector.reset(token)


def record_inline_style_font(style: InlineStyle | None) -> None:
    """Meldet die Schrift eines gerenderten Stils (No-Op ohne Sammler oder ohne Schrift)."""
    collector = _active_font_collector.get()
    if collector is not None and style is not None and style.font_key:
        collector.add(style.font_key)
