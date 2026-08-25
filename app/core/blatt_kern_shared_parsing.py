"""Der eigentliche Blattwerk-Markdown-Parser: Frontmatter, `:::`-Blöcke, Kontrollmarker.

Reiner Parsing-Kern, ausgelagert aus `blatt_kern_shared.py` (300-Zeilen-
Konvention). Enthält keine Render- oder Meta-Logik — nur "Text rein,
strukturierte Tupel raus". `_parse_inline_control_marker` liest seine
Mustererkennung generisch aus `CONTROL_MARKERS`
(`blatt_kern_shared_data.py`) statt fest verdrahteter `if`/`elif`-Zweige,
damit dieselbe Quelle auch vom Validator (`blatt_validator_patterns.py`)
und vom Doku-Collector (`app/core/markdown_conventions.py`) gelesen
werden kann, ohne dass drei Stellen synchron gehalten werden müssen.
"""

from __future__ import annotations

import re
import shlex

import markdown
import yaml

from .blatt_kern_shared_data import CONTROL_MARKERS, MARKDOWN_EXTENSIONS
from .math_span_protection import convert_markdown_with_math as _convert_markdown_with_math

_BLOCK_START_PATTERN = re.compile(r"^:::(\w+)(.*)$")
_SELF_CLOSING_BLOCK_PATTERN = re.compile(r"^:::(\w+)(.*?):::$")
_LIST_LINE_PATTERN = re.compile(r"^(\s*)([-*+]\s+|\d+\.\s+)")

_SOFT_SECTION_BREAK_LITERAL = next(
    marker.literal_or_regex
    for marker in CONTROL_MARKERS
    if marker.name == "soft_section_break"
)


def _parse_inline_control_marker(stripped_line):
    """Erkennt eine Kontrollmarker-Zeile (`--!`, `-+`, `--hf`, `--# ...`, `-=...`) und liefert ihr Block-Tupel.

    Iteriert `CONTROL_MARKERS` in Definitionsreihenfolge; der erste
    Treffer gewinnt. Marker ohne `block_type` (aktuell nur der weiche
    Abschnittswechsel `--`) werden hier übersprungen, da sie kein
    `(block_type, options, content)`-Tupel erzeugen, sondern in
    `parse_blocks()` separat als Roh-Marker in den Text eingefügt
    werden. Liefert `None`, wenn keine Kontrollsyntax erkannt wurde.
    """
    for marker in CONTROL_MARKERS:
        if marker.block_type is None:
            continue

        if marker.kind == "literal":
            if stripped_line == marker.literal_or_regex:
                return (marker.block_type, {}, "")
            continue

        match = marker.literal_or_regex.match(stripped_line)
        if not match:
            continue

        options = {}
        for capture_name, group_value in zip(marker.option_capture, match.groups()):
            options[capture_name] = (group_value or "").strip()
        return (marker.block_type, options, "")

    return None


def _new_markdown_converter():
    """Erzeugt eine frische Markdown-Instanz für einen Render-Schritt."""
    return markdown.Markdown(extensions=MARKDOWN_EXTENSIONS)


def convert_markdown_with_math(md, text):
    """Rendert `text` per `md.convert(normalize_markdown(...))`, mit Mathe-Schutz.

    Duenner Wrapper um `math_span_protection.convert_markdown_with_math`,
    der dieses Moduls eigenes `normalize_markdown` injiziert -- die
    Mathe-Schutz-Logik selbst lebt bewusst in einem eigenen, von beiden
    `_new_markdown_converter()`-Fabriken geteilten Modul (siehe dort), da sie
    unabhaengig davon ist, welche der beiden Fabriken den Konverter erzeugt
    hat; nur die Duplikation der Fabriken selbst ist eine bestehende,
    bewusste Entscheidung.
    """
    return _convert_markdown_with_math(md, text, normalize_markdown)


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

    block_start_pattern = _BLOCK_START_PATTERN
    self_closing_pattern = _SELF_CLOSING_BLOCK_PATTERN

    raw_buffer = []
    block_type = None
    block_options = {}
    block_buffer = []

    for line in lines:
        if block_type is None:
            stripped_line = line.strip()
            inline_marker_block = _parse_inline_control_marker(stripped_line)
            if inline_marker_block is not None:
                if raw_buffer:
                    blocks.append(("raw", {}, "".join(raw_buffer)))
                    raw_buffer = []
                blocks.append(inline_marker_block)
                continue

            # Selbstschließende Kurzform wie :::space::: direkt übernehmen.
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
                if stripped_line == _SOFT_SECTION_BREAK_LITERAL:
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

    block_start_pattern = _BLOCK_START_PATTERN
    self_closing_pattern = _SELF_CLOSING_BLOCK_PATTERN

    block_index = 0
    block_open_line = None
    raw_buffer_start_line = None
    in_block = False

    for line_no, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not in_block:
            if _parse_inline_control_marker(stripped) is not None:
                if raw_buffer_start_line is not None:
                    index_to_line[block_index] = raw_buffer_start_line
                    block_index += 1
                    raw_buffer_start_line = None
                index_to_line[block_index] = line_no
                block_index += 1
                continue

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

    list_pattern = _LIST_LINE_PATTERN

    for line in collapsed_lines:
        is_list_line = bool(list_pattern.match(line))
        if is_list_line and normalized:
            prev = normalized[-1]
            if prev.strip() and not list_pattern.match(prev):
                normalized.append("")
        normalized.append(line)

    return "\n".join(normalized)
