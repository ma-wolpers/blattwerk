"""Kleine Meta-/Formatierungs-Helfer: Dokumentmodus, Bool-Normalisierung, Copyright, Schuljahr, Abschnitts-HTML.

Eigenständige Funktionen ohne Abhängigkeit auf den Parser oder die
Block-Nachbearbeitung — bewusst getrennt gehalten, damit z. B.
`get_copyright_text`/`normalize_document_mode` ohne den restlichen
Kernparser importiert werden können.
"""

from __future__ import annotations

import re
from datetime import datetime

from .blatt_kern_shared_data import (
    DOCUMENT_MODE_ALIASES,
    JA_NEIN_TRUE_TOKENS,
    JA_NEIN_BOOLEAN_TOKENS,
    TASK_ACTION_MAP,
    TASK_HINT_MAP,
    WORK_MODE_MAP,
)

_SECTION_BREAK_SPLIT_PATTERN = re.compile(
    r"(<!--BLATTWERK_SECTION_BREAK-->)", flags=re.IGNORECASE
)


def _normalize_keyword(value, default=""):
    """Normalisiert Optionswerte für Lookup-Tabellen."""
    return (value or default).strip().lower()


def normalize_document_mode(mode_raw, default="ws"):
    """Normalize document output mode from frontmatter metadata."""
    normalized_default = DOCUMENT_MODE_ALIASES.get(
        _normalize_keyword(default, default="worksheet"),
        "worksheet",
    )
    mode = _normalize_keyword(mode_raw, default=normalized_default)
    return DOCUMENT_MODE_ALIASES.get(mode, normalized_default)


def _safe_int(value, default):
    """Konvertiert robust nach int und fällt bei Fehlern auf default zurück."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _option_is_enabled(value, default=True):
    """Interpretiert optionale true/false-ähnliche Blockoptionen."""
    if value is None:
        return default

    normalized = str(value).strip().lower()
    if normalized in {"0", "false", "no", "off", "none"}:
        return False
    if normalized in {"1", "true", "yes", "on"}:
        return True
    return default


def _meta_bool_ja_nein(value, default=False):
    """Interpretiert Meta-Felder robust als bool inkl. `ja`/`nein`.

    Akzeptiertes Vokabular ist `JA_NEIN_BOOLEAN_TOKENS`
    (`blatt_kern_shared_data.py`) — dieselbe Konstante, gegen die
    `FM006` (`blatt_validator_document.py`) `show_student_header`/
    `show_document_header` validiert, damit Lese- und Prüf-Seite nicht
    auseinanderlaufen können.
    """
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized not in JA_NEIN_BOOLEAN_TOKENS:
        return default
    return normalized in JA_NEIN_TRUE_TOKENS


def is_hole_punch_layout_enabled(meta):
    """Liest aus Front-Matter, ob ein vergrößerter linker Lochrand aktiv ist."""
    if not isinstance(meta, dict):
        return False

    if "lochen" in meta:
        return _meta_bool_ja_nein(meta.get("lochen"), default=False)

    return False


def _resolve_help_level(options):
    """Liest optionale Hilfestufe aus Blockoptionen (`level`)."""

    if not isinstance(options, dict):
        return None

    if "level" in options:
        level_value = _safe_int(options.get("level"), default=None)
        if level_value is not None:
            return max(1, min(level_value, 99))

    return None


def format_meta_line(meta):
    """Formatiert die Meta-Zeile aus Fach und Thema."""
    fach = meta.get("Fach", "").strip()
    thema = meta.get("Thema", "").strip()

    if fach and thema:
        return f"{fach} – {thema}"
    if fach:
        return fach
    return thema


def get_current_school_year_label(reference_date=None):
    """Liefert das aktuelle Schuljahr in Niedersachsen als Label.

    Regel: Bis einschließlich Juli läuft das Schuljahr vom Vorjahr ins aktuelle Jahr,
    ab August vom aktuellen ins nächste Jahr.
    """

    date_value = reference_date or datetime.now()
    year = date_value.year

    if date_value.month <= 7:
        start_year = year - 1
        end_year = year
    else:
        start_year = year
        end_year = year + 1

    return f"Schuljahr {start_year}/{end_year}"


def get_copyright_text(meta=None):
    """Liefert Footer-Copyright aus YAML oder Standard-Lizenztext."""

    if isinstance(meta, dict):
        value = meta.get("copyright")
        if value is not None:
            text = str(value).strip()
            if text:
                return text

    generation_year = datetime.now().year
    return f"OER (CC BY-SA 4.0) · Alex Wolpers · {generation_year}"


def get_work_info(work_mode_raw):
    """Liefert Symbol, Label und CSS-Klasse für Arbeitsformen."""
    work_mode = _normalize_keyword(work_mode_raw, default="single")
    return WORK_MODE_MAP.get(work_mode, WORK_MODE_MAP["single"])


def get_task_action_info(action_raw):
    """Liefert Symbolinformationen für Aktionshinweise bei Aufgaben."""
    action = _normalize_keyword(action_raw)

    if not action:
        return None
    return TASK_ACTION_MAP.get(action)


def get_task_hint_info(hint_raw):
    """Liefert Symbolinformationen für Hinweis-/Hilfemarkierungen."""
    hint = _normalize_keyword(hint_raw)

    if not hint:
        return None
    return TASK_HINT_MAP.get(hint)


def split_sections(body_html):
    """Teilt den Body an Solltrennstellen in druckstabile Abschnittscontainer.

    Regeln:
    - `---` bleibt normale Markdown-HR und wird hier nicht als Layoutsteuerung behandelt.
    - `--` wird vorher als `<!--BLATTWERK_SECTION_BREAK-->` markiert und trennt ohne Zusatzabstand.
    """
    tokens = _SECTION_BREAK_SPLIT_PATTERN.split(body_html)
    section_parts = []
    pending_breaks = []
    current = []

    for token in tokens:
        if token is None:
            continue

        stripped = token.strip()
        if not stripped:
            current.append(token)
            continue

        is_soft_break = stripped.lower() == "<!--blattwerk_section_break-->"

        if is_soft_break:
            part = "".join(current).strip()
            current = []
            if part:
                section_parts.append(("section", part))
                pending_breaks.append("soft")
            continue

        current.append(token)

    tail = "".join(current).strip()
    if tail:
        section_parts.append(("section", tail))

    if not section_parts and body_html.strip():
        section_parts.append(("section", body_html.strip()))

    html_parts = []
    for part_kind, part_html in section_parts:
        if part_kind == "gap":
            html_parts.append("<div class='ab-section-gap' aria-hidden='true'></div>")
        else:
            html_parts.append(f"<section class='ab-section'>{part_html}</section>")

    return "".join(html_parts)
