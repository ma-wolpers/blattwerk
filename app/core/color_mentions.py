"""Erkennung von Farbbegriffen in Markdown-Texten."""

from __future__ import annotations

from pathlib import Path
import re


COLOR_TERM_PATTERN = re.compile(
    r"\b("
    r"farbe(?:n|m|r|s)?|farbig(?:e|en|er|es)?|bunt(?:e|en|er|es)?|"
    r"rot(?:e|en|er|es)?|blau(?:e|en|er|es)?|grün(?:e|en|er|es)?|"
    r"gelb(?:e|en|er|es)?|orange(?:n)?|lila|violett(?:e|en|er|es)?|"
    r"pink(?:e|en|er|es)?|magenta|türkis(?:e|en|er|es)?|cyan|"
    r"schwarz(?:e|en|er|es)?|weiß(?:e|en|er|es)?|grau(?:e|en|er|es)?|"
    r"braun(?:e|en|er|es)?"
    r")\b",
    re.IGNORECASE,
)


def read_markdown_text(input_path: Path):
    """Liest Markdown robust (UTF-8) und ersetzt fehlerhafte Bytes bei Bedarf."""
    try:
        return input_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return input_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def find_color_mentions(markdown_text: str, max_hits: int = 6):
    """Extrahiert eindeutige Farbbegriffe bis zu `max_hits` Treffern."""
    if not markdown_text:
        return []

    mentions = []
    seen = set()
    for match in COLOR_TERM_PATTERN.finditer(markdown_text):
        term = match.group(0)
        normalized = term.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        mentions.append(term)
        if len(mentions) >= max_hits:
            break

    return mentions


def find_color_mentions_in_file(input_path: Path, max_hits: int = 6):
    """Liest eine Datei und liefert gefundene Farbbegriffe zurück."""
    markdown_text = read_markdown_text(input_path)
    return find_color_mentions(markdown_text, max_hits=max_hits)


def detect_bw_mode_color_warning_mentions(
    input_path: Path | None,
    current_profile: str | None,
    previous_profile: str | None = None,
    bw_profiles: set[str] | None = None,
    max_hits: int = 6,
):
    """Ermittelt Farbhinweis-Treffer, wenn in einen S/W-Modus gewechselt wurde."""

    if input_path is None:
        return []

    path = Path(input_path)
    if not path.exists():
        return []

    allowed_bw_profiles = bw_profiles or {"bw"}
    current = (current_profile or "").strip().lower()
    previous = (previous_profile or "").strip().lower()

    if current not in allowed_bw_profiles:
        return []

    if previous and previous in allowed_bw_profiles:
        return []

    return find_color_mentions_in_file(path, max_hits=max_hits)
