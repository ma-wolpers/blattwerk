"""Shared parsing and metadata helpers for worksheet generation."""

from __future__ import annotations

import re
import shlex
from datetime import datetime
from pathlib import Path

import markdown
import yaml

MARKDOWN_EXTENSIONS = ["tables", "nl2br"]

WORK_MODE_MAP = {
    "single": ("👤", "Einzelarbeit", "single"),
    "ea": ("👤", "Einzelarbeit", "single"),
    "einzel": ("👤", "Einzelarbeit", "single"),
    "einzelarbeit": ("👤", "Einzelarbeit", "single"),
    "partner": ("👥", "Partnerarbeit", "partner"),
    "pa": ("👥", "Partnerarbeit", "partner"),
    "partnerarbeit": ("👥", "Partnerarbeit", "partner"),
    "group": ("👪", "Gruppenarbeit", "group"),
    "ga": ("👪", "Gruppenarbeit", "group"),
    "gruppe": ("👪", "Gruppenarbeit", "group"),
    "gruppenarbeit": ("👪", "Gruppenarbeit", "group"),
}

TASK_ACTION_MAP = {
    "exchange": ("💬", "austauschen", "action"),
    "austauschen": ("💬", "austauschen", "action"),
    "decide": ("⚖️", "entscheiden", "action"),
    "entscheiden": ("⚖️", "entscheiden", "action"),
    "experiment": ("🧪", "experimentieren", "action"),
    "experimentieren": ("🧪", "experimentieren", "action"),
    "reflect": ("🤔", "reflektieren", "action"),
    "reflektieren": ("🤔", "reflektieren", "action"),
    "read": ("📖", "lesen", "action"),
    "lesen": ("📖", "lesen", "action"),
    "calculate": ("🔢", "rechnen", "action"),
    "rechnen": ("🔢", "rechnen", "action"),
    "match": ("↔️", "zuordnen", "action"),
    "zuordnen": ("↔️", "zuordnen", "action"),
    "write": ("✍️", "schreiben", "action"),
    "schreiben": ("✍️", "schreiben", "action"),
    "draw": ("📐", "zeichnen", "action"),
    "zeichnen": ("📐", "zeichnen", "action"),
}

TASK_HINT_MAP = {
    "tip": ("💡", "Tipp", "hint"),
    "hint": ("💡", "Tipp", "hint"),
    "tipp": ("💡", "Tipp", "hint"),
    "definition": ("📘", "Definition", "hint"),
    "def": ("📘", "Definition", "hint"),
    "remember": ("💭", "Erinnerung", "hint"),
    "reminder": ("💭", "Erinnerung", "hint"),
    "erinnerung": ("💭", "Erinnerung", "hint"),
    "term": ("📖", "Fachwort", "hint"),
    "fachwort": ("📖", "Fachwort", "hint"),
    "expert": ("🚀", "Expertenaufgabe", "hint"),
    "expertenaufgabe": ("🚀", "Expertenaufgabe", "hint"),
}

HELP_BLOCK_TYPES = {"help", "hilfe"}
DOCUMENT_MODES = {"ws", "test"}


def _normalize_keyword(value, default=""):
    """Normalisiert Optionswerte für Lookup-Tabellen."""
    return (value or default).strip().lower()


def normalize_document_mode(mode_raw, default="ws"):
    """Normalize document output mode from frontmatter metadata."""
    mode = _normalize_keyword(mode_raw, default=default)
    if mode in DOCUMENT_MODES:
        return mode
    return default


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
    """Interpretiert Meta-Felder robust als bool inkl. `ja`/`nein`."""
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on", "ja", "j"}:
        return True
    if normalized in {"0", "false", "no", "off", "nein", "n"}:
        return False
    return default


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


def _new_markdown_converter():
    """Erzeugt eine frische Markdown-Instanz für einen Render-Schritt."""
    return markdown.Markdown(extensions=MARKDOWN_EXTENSIONS)


def split_front_matter(text):
    """Liest YAML-Front-Matter und liefert (Meta-Dict, Resttext).

    Fällt auf leere Metadaten zurück, wenn kein vollständiger Front-Matter
    vorhanden ist oder YAML leer ist.
    """
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            _, fm, rest = parts
            return yaml.safe_load(fm) or {}, rest.strip()
    return {}, text


def parse_options(options_raw):
    """Parst Block-Optionen im Format key=value mit Shell-Quoting-Unterstützung."""
    if not options_raw:
        return {}

    options = {}
    for part in shlex.split(options_raw):
        if "=" in part:
            key, value = part.split("=", 1)
            options[key] = value
    return options


def parse_blocks(text):
    """Parst den Dokumenttext in Block-Tupel (typ, optionen, inhalt)."""
    blocks = []
    lines = text.splitlines(keepends=True)

    block_start_pattern = re.compile(r"^:::(\w+)(.*)$")
    self_closing_pattern = re.compile(r"^:::(\w+)(.*?):::$")

    raw_buffer = []
    block_type = None
    block_options = {}
    block_buffer = []

    for line in lines:
        if block_type is None:
            stripped_line = line.strip()
            # Selbstschließende Kurzform wie :::answer type=space::: direkt übernehmen.
            self_closing_match = self_closing_pattern.match(stripped_line)
            if self_closing_match:
                if raw_buffer:
                    blocks.append(("raw", {}, "".join(raw_buffer)))
                    raw_buffer = []

                inline_type = self_closing_match.group(1)
                inline_options = parse_options(self_closing_match.group(2).strip())
                blocks.append((inline_type, inline_options, ""))
                continue

            start_match = block_start_pattern.match(stripped_line)
            if start_match:
                # Beim Start eines neuen Blocks zuerst eventuell gesammelten Rohtext flushen.
                if raw_buffer:
                    blocks.append(("raw", {}, "".join(raw_buffer)))
                    raw_buffer = []

                block_type = start_match.group(1)
                options_raw = start_match.group(2).strip()
                block_options = parse_options(options_raw)
                block_buffer = []
            else:
                if stripped_line == "--":
                    # `--` ist ein weicher Abschnittswechsel (Solltrennstelle ohne Zusatzabstand).
                    line_break = "\n" if line.endswith("\n") else ""
                    raw_buffer.append(f"<!--BLATTWERK_SECTION_BREAK-->{line_break}")
                    continue
                raw_buffer.append(line)
        else:
            # Ein einzelnes ::: beendet den aktuellen Block.
            if line.strip() == ":::":
                blocks.append(
                    (block_type, block_options, "".join(block_buffer).rstrip("\r\n"))
                )
                block_type = None
                block_options = {}
                block_buffer = []
            else:
                block_buffer.append(line)

    if block_type is not None:
        raw_buffer.append(f":::{block_type}")
        if block_options:
            raw_buffer.append(
                " " + " ".join(f"{k}={v}" for k, v in block_options.items())
            )
        raw_buffer.append("\n")
        raw_buffer.extend(block_buffer)

    if raw_buffer:
        blocks.append(("raw", {}, "".join(raw_buffer)))

    return blocks


def build_block_index_line_map(text):
    """Liefert 1-basierte Startzeilen pro Blockindex im parse_blocks-Reihenfolge."""

    index_to_line = {}
    lines = text.splitlines(keepends=True)

    block_start_pattern = re.compile(r"^:::(\w+)(.*)$")
    self_closing_pattern = re.compile(r"^:::(\w+)(.*?):::$")

    block_index = 0
    block_open_line = None
    raw_buffer_start_line = None
    in_block = False

    for line_no, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not in_block:
            if self_closing_pattern.match(stripped):
                if raw_buffer_start_line is not None:
                    index_to_line[block_index] = raw_buffer_start_line
                    block_index += 1
                    raw_buffer_start_line = None
                index_to_line[block_index] = line_no
                block_index += 1
                continue

            start_match = block_start_pattern.match(stripped)
            if start_match:
                if raw_buffer_start_line is not None:
                    index_to_line[block_index] = raw_buffer_start_line
                    block_index += 1
                    raw_buffer_start_line = None
                in_block = True
                block_open_line = line_no
                continue

            if raw_buffer_start_line is None:
                raw_buffer_start_line = line_no
            continue

        if stripped == ":::":
            index_to_line[block_index] = block_open_line or line_no
            block_index += 1
            in_block = False
            block_open_line = None

    if in_block:
        index_to_line[block_index] = block_open_line or max(1, len(lines))
        block_index += 1

    if raw_buffer_start_line is not None:
        index_to_line[block_index] = raw_buffer_start_line

    return index_to_line


def normalize_markdown(text):
    """Normalisiert Markdown für stabile Umbruch- und Listen-Semantik."""
    if text is None:
        return ""

    lines = str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n")

    # Mehr als ein aufeinanderfolgender Leerzeilenlauf wird auf genau
    # einen Absatzwechsel begrenzt.
    collapsed_lines = []
    previous_was_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank:
            if previous_was_blank:
                continue
            collapsed_lines.append("")
            previous_was_blank = True
            continue

        collapsed_lines.append(line)
        previous_was_blank = False

    normalized = []

    list_pattern = re.compile(r"^(\s*)([-*+]\s+|\d+\.\s+)")

    for line in collapsed_lines:
        is_list_line = bool(list_pattern.match(line))
        if is_list_line and normalized:
            prev = normalized[-1]
            if prev.strip() and not list_pattern.match(prev):
                normalized.append("")
        normalized.append(line)

    return "\n".join(normalized)


def assign_task_numbers(blocks):
    """Fügt `task`-Blöcken optional fortlaufende Aufgabennummern hinzu."""
    numbered_blocks = []
    task_total = sum(1 for block_type, _, _ in blocks if block_type == "task")
    task_counter = 1

    for block_type, options, content in blocks:
        if block_type == "task":
            updated_options = dict(options)
            updated_options["_show_task_label"] = "1"
            if task_total > 1:
                updated_options["_auto_number"] = str(task_counter)
            task_counter += 1
            numbered_blocks.append((block_type, updated_options, content))
        else:
            numbered_blocks.append((block_type, options, content))

    return numbered_blocks


def annotate_standalone_subtasks(blocks):
    """Reichert Top-Level-`subtask`-Blöcke mit Elternkontext und Zählung an."""
    task_contexts = {}
    current_task_key = None
    task_key_counter = 0
    subtask_total_by_task = {}
    subtask_seen_by_task = {}

    for block_type, options, _ in blocks:
        if block_type == "task":
            task_key_counter += 1
            current_task_key = task_key_counter
            task_contexts[current_task_key] = dict(options)
            continue

        if block_type == "subtask" and current_task_key is not None:
            subtask_total_by_task[current_task_key] = (
                subtask_total_by_task.get(current_task_key, 0) + 1
            )

    annotated_blocks = []
    current_task_key = None

    for block_type, options, content in blocks:
        if block_type == "task":
            current_task_key = (
                current_task_key + 1 if current_task_key is not None else 1
            )
            annotated_blocks.append((block_type, options, content))
            continue

        if block_type == "subtask" and current_task_key is not None:
            parent_options = task_contexts.get(current_task_key, {})
            updated_options = dict(options)
            updated_options["_parent_work"] = parent_options.get("work", "single")
            if parent_options.get("action") is not None:
                updated_options["_parent_action"] = parent_options.get("action")

            total = subtask_total_by_task.get(current_task_key, 0)
            seen = subtask_seen_by_task.get(current_task_key, 0)
            updated_options["_subtask_total"] = str(total)
            updated_options["_subtask_index"] = str(seen)
            subtask_seen_by_task[current_task_key] = seen + 1

            if total > 1:
                updated_options["_subtask_letter"] = chr(ord("a") + seen)

            annotated_blocks.append((block_type, updated_options, content))
            continue

        annotated_blocks.append((block_type, options, content))

    return annotated_blocks


def should_render_block(block_type, options, include_solutions):
    """Entscheidet, ob ein Block in der aktuellen Ausgabe sichtbar sein soll."""
    show_mode_raw = (options.get("show") or "").strip().lower()
    if show_mode_raw in {"worksheet", "solution", "both"}:
        show_mode = show_mode_raw
    else:
        show_mode = "both"

    if show_mode == "worksheet" and include_solutions:
        return False
    if show_mode == "solution" and not include_solutions:
        return False

    if block_type == "solution":
        return include_solutions

    return True


def split_sections(body_html):
    """Teilt den Body an Solltrennstellen in druckstabile Abschnittscontainer.

    Regeln:
    - `---` (Markdown-HR) trennt Abschnitte und fuegt zusaetzlich 1cm Vertikalabstand ein.
    - `--` wird vorher als `<!--BLATTWERK_SECTION_BREAK-->` markiert und trennt ohne Zusatzabstand.
    """
    split_pattern = re.compile(
        r"(<hr\s*/?>|<!--BLATTWERK_SECTION_BREAK-->)", flags=re.IGNORECASE
    )
    tokens = split_pattern.split(body_html)
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

        is_hard_break = bool(re.fullmatch(r"<hr\s*/?>", stripped, flags=re.IGNORECASE))
        is_soft_break = stripped.lower() == "<!--blattwerk_section_break-->"

        if is_hard_break or is_soft_break:
            part = "".join(current).strip()
            current = []
            if part:
                section_parts.append(("section", part))
                pending_breaks.append("hard" if is_hard_break else "soft")
            continue

        current.append(token)

    tail = "".join(current).strip()
    if tail:
        if section_parts and pending_breaks:
            for break_kind in pending_breaks:
                if break_kind == "hard":
                    section_parts.append(("gap", ""))
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
