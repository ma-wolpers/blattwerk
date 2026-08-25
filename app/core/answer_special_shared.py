"""Shared helpers for special answer renderers."""

from __future__ import annotations

import re

import markdown

from .math_span_protection import convert_markdown_with_math as _convert_markdown_with_math

MARKDOWN_EXTENSIONS = ["tables"]


def _new_markdown_converter():
    """Erzeugt eine frische Markdown-Instanz für einen einzelnen Renderlauf."""
    return markdown.Markdown(extensions=MARKDOWN_EXTENSIONS)


def convert_markdown_with_math(md, text):
    """Rendert `text` per `md.convert(normalize_markdown(...))`, mit Mathe-Schutz.

    Duenner Wrapper um `math_span_protection.convert_markdown_with_math`, der
    dieses Moduls eigenes `normalize_markdown` injiziert -- die
    Mathe-Schutz-Logik selbst lebt in einem eigenen, von beiden
    `_new_markdown_converter()`-Fabriken geteilten Modul (siehe dort), da sie
    unabhaengig davon ist, welche der beiden Fabriken den Konverter erzeugt
    hat; nur die Duplikation der Fabriken selbst ist eine bestehende,
    bewusste Entscheidung.
    """
    return _convert_markdown_with_math(md, text, normalize_markdown)


def _normalize_keyword(value, default=""):
    """Normalisiert optionale Schlüsselwörter für robuste Vergleiche."""
    return (value or default).strip().lower()


def _safe_int(value, default):
    """Konvertiert robust nach int und fällt bei Fehlern auf `default` zurück."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _option_is_enabled(value, default=True):
    """Interpretiert boolesche Optionen aus Text-/Zahlwerten."""
    if value is None:
        return default

    normalized = str(value).strip().lower()
    if normalized in {"0", "false", "no", "off", "none"}:
        return False
    if normalized in {"1", "true", "yes", "on"}:
        return True
    return default


def normalize_markdown(text):
    """Ergänzt Leerzeilen vor Listen für stabiles Markdown-Rendering."""
    lines = text.splitlines()
    normalized = []

    list_pattern = re.compile(r"^(\s*)([-*+]\s+|\d+\.\s+)")

    for line in lines:
        is_list_line = bool(list_pattern.match(line))
        if is_list_line and normalized:
            prev = normalized[-1]
            if prev.strip() and not list_pattern.match(prev):
                normalized.append("")
        normalized.append(line)

    return "\n".join(normalized)


def _parse_option_list(raw_value):
    """Parst Listenwerte aus `a|b|c` oder `a,b,c` in getrimmte Einträge."""
    if not raw_value:
        return []

    normalized = str(raw_value).replace(",", "|")
    return [item.strip() for item in normalized.split("|") if item.strip()]


_SVG_COLOR_MAX_LENGTH = 64

_SVG_COLOR_PATTERN = re.compile(
    r"#[0-9a-fA-F]{3}"
    r"|#[0-9a-fA-F]{4}"
    r"|#[0-9a-fA-F]{6}"
    r"|#[0-9a-fA-F]{8}"
    r"|(?:rgb|rgba|hsl|hsla)\(\s*[0-9.%,\s]+\)"
    r"|[a-zA-Z]+"
)
"""Whitelist-Muster für als SVG-`style`-Attribut sichere Farbwerte.

Deckt Hex (`#rgb`/`#rrggbb`/`#rrggbbaa`), die Funktionsschreibweisen
`rgb()`/`rgba()`/`hsl()`/`hsla()` (Innenleben nur Ziffern/Punkt/Prozent/
Komma/Whitespace) sowie reine CSS-Farbnamen ab — genau eine dieser Formen,
keine Wiederholung/Verkettung (kein `+`/`{n,m}` um die gesamte Alternation,
sonst liesse sich z. B. `"redred"` oder eine Aneinanderreihung mehrerer
Teilformen durchschleusen). Absichtlich **kein** `match()`+`$`, sondern
`fullmatch()` in `parse_svg_color` — `$` würde in Python-Regex ohne
`re.MULTILINE` auch direkt vor einem abschließenden `\n` matchen und
liesse z. B. `"red\n; javascript:..."` durch. Die Gesamtlänge wird separat
in `parse_svg_color` über `_SVG_COLOR_MAX_LENGTH` begrenzt (Defense-in-Depth
gegen überlange Payloads im generierten Markup) statt im Regex-Pattern
selbst, um die Alternation nicht versehentlich wiederholbar zu machen.
"""


def parse_svg_color(raw_value):
    """Validiert/sanitized einen rohen Farbwert für die Verwendung in einem SVG-`style`-Attribut.

    Liefert `None` bei leerem/fehlendem/zu langem Wert oder wenn der Wert
    nicht dem engen Whitelist-Pattern entspricht — Aufrufer (Renderer wie
    Validator) behandeln `None` einheitlich als "kein gültiger Farbwert
    gesetzt" und fallen auf den bisherigen Theme-Default zurück. Dies ist
    die **einzige** Stelle im Code, die entscheidet, was eine gültige Farbe
    ist; Renderer und Validator rufen exakt diese Funktion auf, damit beide
    Seiten nie auseinanderlaufen können. Sicherheitsrelevant: der
    zurückgegebene Wert wird roh in generiertes SVG-Markup interpoliert,
    daher `fullmatch` (kein `search`/`match`) gegen ein enges
    Zeichen-Whitelist-Pattern statt einer Blacklist gefährlicher Zeichen.
    """
    text = str(raw_value or "").strip()
    if not text or len(text) > _SVG_COLOR_MAX_LENGTH:
        return None
    if not _SVG_COLOR_PATTERN.fullmatch(text):
        return None
    return text


def parse_svg_thickness(raw_value):
    """Validiert einen rohen Dicke-Wert (SVG-`stroke-width`, unitless) für Geometrie-Objekte.

    Liefert `None` bei fehlendem, nicht als `float` parsebarem oder
    nicht-positivem Wert — Aufrufer fallen dann auf die bisherige,
    Theme-abhängige Standarddicke zurück. Einzige Quelle für "was ist eine
    gültige Dicke", von Renderer und Validator gemeinsam genutzt.
    """
    if raw_value is None:
        return None
    try:
        parsed = float(raw_value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def parse_bullet_list_lines(content):
    """Parses simple `- item`/`* item`/`+ item` (or bare) lines into a plain
    list of item strings, in source order. Shared by any block whose content
    is just a list of statements/items with no further structure (`ordering`,
    `selfcheck`) -- not `wordsearch`'s tokenizing variant, which additionally
    splits on `,;|` and normalizes to uppercase letters."""
    items = []
    for raw_line in (content or "").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        bullet_match = re.match(r"^[-*+]\s+(.*)$", stripped)
        text = bullet_match.group(1).strip() if bullet_match else stripped
        if text:
            items.append(text)
    return items


def _as_text_list(value):
    """Normalisiert Werte zu einer nicht-leeren Liste aus Strings."""
    if value is None:
        return []

    if isinstance(value, list):
        items = value
    else:
        items = _parse_option_list(str(value))

    normalized = []
    for item in items:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized
