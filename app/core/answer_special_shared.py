"""Shared helpers for special answer renderers."""

from __future__ import annotations

import re

import markdown

MARKDOWN_EXTENSIONS = ["tables"]


def _new_markdown_converter():
    """Erzeugt eine frische Markdown-Instanz für einen einzelnen Renderlauf."""
    return markdown.Markdown(extensions=MARKDOWN_EXTENSIONS)


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
