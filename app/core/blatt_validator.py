"""Validation and diagnostics for Blattwerk markdown documents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import yaml

from .answer_line_markers import (
    collect_answer_marker_conflict_lines,
    is_effectively_empty_answer_content,
)
from .blatt_kern_shared import parse_blocks, split_front_matter


@dataclass(frozen=True)
class BuildDiagnostic:
    """Non-blocking or blocking diagnostic from parsing/validation."""

    code: str
    message: str
    severity: str = "warning"
    block_index: int | None = None
    block_type: str | None = None
    line_number: int | None = None


@dataclass(frozen=True)
class InspectedDocument:
    """Parsed markdown plus diagnostics."""

    meta: dict
    blocks: list[tuple[str, dict, str]]
    diagnostics: list[BuildDiagnostic]


REQUIRED_FRONTMATTER_FIELDS = ("Titel", "Fach", "Thema")
KNOWN_BLOCK_TYPES = {
    "raw",
    "material",
    "info",
    "task",
    "subtask",
    "lines",
    "grid",
    "dots",
    "space",
    "table",
    "numberline",
    "mc",
    "cloze",
    "matching",
    "wordsearch",
    "solution",
    "columns",
    "nextcol",
    "endcolumns",
    "help",
    "hilfe",
}
KNOWN_SHOW_VALUES = {"worksheet", "solution", "both"}
KNOWN_DOCUMENT_MODES = {"ws", "test"}
GRID_MARKER_SHOW_VALUES = {"&", "§", "%"}
NUMBERLINE_ANSWER_TYPES = {"numberline"}
MARKER_SHOW_SECTIONS_BY_ANSWER_TYPE = {
    "grid": ("points", "pairs", "functions"),
    "numberline": ("labels", "answers", "arcs", "jumps", "arrows", "boxes", "blanks"),
}
KNOWN_WORK_VALUES = {
    "single",
    "ea",
    "einzel",
    "einzelarbeit",
    "partner",
    "pa",
    "partnerarbeit",
    "group",
    "ga",
    "gruppe",
    "gruppenarbeit",
}
KNOWN_ACTION_VALUES = {
    "exchange",
    "austauschen",
    "decide",
    "entscheiden",
    "experiment",
    "experimentieren",
    "reflect",
    "reflektieren",
    "read",
    "lesen",
    "calculate",
    "rechnen",
    "match",
    "zuordnen",
    "write",
    "schreiben",
    "draw",
    "zeichnen",
}
KNOWN_HINT_VALUES = {
    "tip",
    "tipp",
    "hint",
    "definition",
    "def",
    "remember",
    "reminder",
    "erinnerung",
    "term",
    "fachwort",
    "expert",
    "expertenaufgabe",
}
ANSWER_BLOCK_TYPES = {
    "lines",
    "grid",
    "dots",
    "space",
    "table",
    "numberline",
    "mc",
    "cloze",
    "matching",
    "wordsearch",
}
KNOWN_ANSWER_TYPES = ANSWER_BLOCK_TYPES
YAML_ANSWER_TYPES = {
    "grid",
    "numberline",
    "table",
    "matching",
}

BLOCK_ALLOWED_OPTIONS = {
    "material": {"title", "show"},
    "info": {"type", "show"},
    "task": {"points", "work", "action", "hint", "show"},
    "subtask": {"work", "action", "show"},
    "lines": {
        "show",
        "rows",
    },
    "grid": {
        "show",
        "rows",
        "cols",
        "scale",
        "axis",
        "axis_label_x",
        "axis_label_y",
        "origin",
        "step_x",
        "step_y",
    },
    "dots": {
        "show",
        "height",
    },
    "space": {
        "show",
        "height",
    },
    "table": {
        "show",
        "rows",
        "cols",
        "width",
        "widths",
        "alignment",
        "row_height",
        "headers",
        "header_columns",
        "header_cols",
        "row_labels",
    },
    "numberline": {
        "show",
        "height",
        "min",
        "max",
        "minimum",
        "maximum",
        "tick_step",
        "ticks",
        "tick_spacing_mm",
        "tick_spacing_cm",
        "tick_spacing",
        "major_every",
        "max_width_mm",
        "max_width_cm",
        "full_width",
        "positive_sign",
        "signed_positive",
    },
    "mc": {
        "show",
        "inline",
        "tf",
        "true_false",
        "correct",
        "options",
        "widths",
    },
    "cloze": {
        "show",
        "gap",
        "gap_length",
        "words",
        "words_multi",
        "layout",
    },
    "matching": {
        "show",
        "scale",
        "layout",
        "orientation",
        "left",
        "right",
        "top",
        "bottom",
        "matches",
        "links",
        "worksheet_matches",
        "height_mode",
        "align",
        "show_guides",
        "lane_align",
    },
    "wordsearch": {
        "show",
        "min_size",
        "min_rows",
        "min_cols",
        "diagonal",
        "horizontal",
        "vertical",
        "words",
    },
    "solution": {"label", "show"},
    "columns": {"cols", "widths", "ratio", "gap"},
    "nextcol": set(),
    "endcolumns": set(),
    "help": {"title", "level", "show"},
    "hilfe": {"title", "level", "show"},
}

CRITICAL_DIAGNOSTIC_CODES = {
    "AN003",  # Invalid YAML in schema-driven answer blocks.
}

_MARKDOWN_IMAGE_PATH_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
_HTML_IMAGE_SRC_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.IGNORECASE)
_WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")
_UNC_ABSOLUTE_PATH_RE = re.compile(r"^[\\/]{2}[^\\/]+[\\/][^\\/]+")
_POSIX_ABSOLUTE_PATH_RE = re.compile(r"^/")
_BLOCK_START_PATTERN = re.compile(r"^:::(\w+)(.*)$")
_SELF_CLOSING_BLOCK_PATTERN = re.compile(r"^:::(\w+)(.*?):::$")
_BLOCK_WHITESPACE_AFTER_MARKER_PATTERN = re.compile(r"^:::\s+")


def _normalize_value(value):
    return (value or "").strip().lower()


def _as_matching_list(value):
    if isinstance(value, list):
        return [entry for entry in value if str(entry).strip()]
    if isinstance(value, str):
        normalized = value.replace("\n", "|").replace(",", "|")
        return [entry.strip() for entry in normalized.split("|") if entry.strip()]
    return []


def _get_matching_item_counts(options, content):
    payload = {}
    try:
        parsed = yaml.safe_load(content or "")
        if isinstance(parsed, dict):
            payload = parsed
    except yaml.YAMLError:
        payload = {}

    layout_raw = _normalize_value(
        (options or {}).get("layout") or (options or {}).get("orientation")
    )
    if not layout_raw and (payload.get("top") or payload.get("bottom")):
        layout_raw = "vertical"

    if layout_raw in {"vertical", "topbottom", "tb", "obenunten", "oben_unten"}:
        first_items = _as_matching_list(
            payload.get("top") or payload.get("oben") or payload.get("first")
        )
        second_items = _as_matching_list(
            payload.get("bottom") or payload.get("unten") or payload.get("second")
        )
    else:
        first_items = _as_matching_list(
            payload.get("left") or payload.get("links") or payload.get("first")
        )
        second_items = _as_matching_list(
            payload.get("right") or payload.get("rechts") or payload.get("second")
        )

    if not first_items:
        first_items = _as_matching_list(
            (options or {}).get("left") or (options or {}).get("top")
        )
    if not second_items:
        second_items = _as_matching_list(
            (options or {}).get("right") or (options or {}).get("bottom")
        )

    return len(first_items), len(second_items)


def _option_items(options):
    for key, value in (options or {}).items():
        if str(key).startswith("_"):
            continue
        yield key, value


def _is_local_absolute_path(path_text):
    normalized = str(path_text or "").strip().strip("\"").strip("'")
    if not normalized:
        return False

    if normalized.startswith(("http://", "https://", "data:", "mailto:")):
        return False

    return bool(
        _WINDOWS_ABSOLUTE_PATH_RE.match(normalized)
        or _UNC_ABSOLUTE_PATH_RE.match(normalized)
        or _POSIX_ABSOLUTE_PATH_RE.match(normalized)
    )


def _collect_absolute_image_paths(block_content):
    paths = []
    content = str(block_content or "")

    for match in _MARKDOWN_IMAGE_PATH_RE.finditer(content):
        candidate = match.group(1).strip()
        if _is_local_absolute_path(candidate):
            paths.append(candidate)

    for match in _HTML_IMAGE_SRC_RE.finditer(content):
        candidate = match.group(1).strip()
        if _is_local_absolute_path(candidate):
            paths.append(candidate)

    return paths


def _extract_validation_content_and_base_line(markdown_text):
    """Return validator content and its 1-based base line in the full document."""
    lines = (markdown_text or "").splitlines(keepends=True)
    content_start_line = 1
    content_raw = markdown_text or ""

    if lines and lines[0].strip() == "---":
        for line_index in range(1, len(lines)):
            if lines[line_index].strip() == "---":
                content_start_line = line_index + 2
                content_raw = "".join(lines[line_index + 1 :])
                break

    content_for_validation = content_raw.strip()
    if not content_for_validation:
        return "", max(1, content_start_line)

    leading_removed_text = content_raw[: content_raw.find(content_for_validation)]
    leading_removed_lines = leading_removed_text.count("\n")
    base_line = content_start_line + leading_removed_lines
    return content_for_validation, max(1, base_line)


def _collect_block_marker_syntax_diagnostics(content_text, base_line=1):
    """Validate ::: marker syntax directly on source lines."""
    diagnostics = []
    block_depth = 0

    for line_no, raw_line in enumerate((content_text or "").splitlines(), start=1):
        absolute_line_no = max(1, int(base_line) + line_no - 1)
        stripped_line = raw_line.strip()
        if not stripped_line.startswith(":::"):
            continue

        if _BLOCK_WHITESPACE_AFTER_MARKER_PATTERN.match(stripped_line):
            diagnostics.append(
                BuildDiagnostic(
                    code="BL002",
                    message=(
                        "Ungueltige Blocksyntax in Zeile "
                        f"{absolute_line_no}: Nach `:::` darf kein Leerzeichen folgen. "
                        "Erlaubt sind nur `:::blocktyp` oder `:::`."
                    ),
                    severity="error",
                    line_number=absolute_line_no,
                )
            )
            continue

        if stripped_line == ":::":
            if block_depth == 0:
                diagnostics.append(
                    BuildDiagnostic(
                        code="BL003",
                        message=(
                            "Ungueltiger Blockabschluss in Zeile "
                            f"{absolute_line_no}: `:::` ohne passenden geoeffneten Block."
                        ),
                        severity="error",
                        line_number=absolute_line_no,
                    )
                )
            else:
                block_depth -= 1
            continue

        self_closing_match = _SELF_CLOSING_BLOCK_PATTERN.match(stripped_line)
        if self_closing_match:
            if block_depth > 0:
                nested_type = self_closing_match.group(1)
                diagnostics.append(
                    BuildDiagnostic(
                        code="BL004",
                        message=(
                            "Verschachtelter Block in Zeile "
                            f"{absolute_line_no}: `:::{nested_type} ... :::` innerhalb "
                            "eines bereits geoeffneten Blocks ist unzulaessig. "
                            "`:::`-Marker muessen strikt abwechseln (oeffnen, schliessen, ...)."
                        ),
                        severity="error",
                        line_number=absolute_line_no,
                    )
                )
            continue

        start_match = _BLOCK_START_PATTERN.match(stripped_line)
        if start_match:
            if block_depth > 0:
                nested_type = start_match.group(1)
                diagnostics.append(
                    BuildDiagnostic(
                        code="BL004",
                        message=(
                            "Verschachtelter Block in Zeile "
                            f"{absolute_line_no}: `:::{nested_type}` innerhalb eines "
                            "bereits geoeffneten Blocks ist unzulaessig. "
                            "`:::`-Marker muessen strikt abwechseln (oeffnen, schliessen, ...)."
                        ),
                        severity="error",
                        line_number=absolute_line_no,
                    )
                )
                continue
            block_depth += 1

    return diagnostics


def _append_invalid_option_value(
    diagnostics, block_index, block_type, option, value, allowed
):
    diagnostics.append(
        BuildDiagnostic(
            code="OP002",
            message=(
                f"Ungueltiger Wert fuer `{option}` in Block `{block_type}`: `{value}`. "
                f"Erlaubt: {', '.join(sorted(allowed))}."
            ),
            block_index=block_index,
            block_type=block_type,
        )
    )


def _append_invalid_yaml_show_diagnostic(
    diagnostics,
    block_index,
    answer_type,
    section,
    position,
    value,
):
    diagnostics.append(
        BuildDiagnostic(
            code="AN007",
            message=(
                "YAML nutzt ungueltigen Sichtbarkeitswert "
                f"`{value}` in answer `{answer_type}` bei `{section}[{position}].show`. "
                "Erlaubt sind nur `&`, `§` oder `%`."
            ),
            severity="error",
            block_index=block_index,
            block_type=answer_type,
        )
    )


def _canonical_yaml_answer_type(answer_type):
    if answer_type in NUMBERLINE_ANSWER_TYPES:
        return "numberline"
    return answer_type


def _validate_payload_show_markers(diagnostics, block_index, answer_type, parsed_payload):
    """Validate marker-only show values in YAML answer sections."""
    if not isinstance(parsed_payload, dict):
        return

    canonical_answer_type = _canonical_yaml_answer_type(answer_type)
    sections = MARKER_SHOW_SECTIONS_BY_ANSWER_TYPE.get(canonical_answer_type)
    if not sections:
        return

    for section in sections:
        entries = parsed_payload.get(section)
        if not isinstance(entries, list):
            continue

        for idx, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                continue
            raw_show = entry.get("show")
            if raw_show is None:
                continue
            normalized = str(raw_show).strip()
            if normalized not in GRID_MARKER_SHOW_VALUES:
                _append_invalid_yaml_show_diagnostic(
                    diagnostics,
                    block_index,
                    canonical_answer_type,
                    section,
                    idx,
                    raw_show,
                )


def _collect_document_diagnostics(meta, blocks, content_text, content_base_line=1):
    diagnostics = _collect_block_marker_syntax_diagnostics(
        content_text, base_line=content_base_line
    )

    for required_key in REQUIRED_FRONTMATTER_FIELDS:
        value = str((meta or {}).get(required_key, "")).strip()
        if not value:
            diagnostics.append(
                BuildDiagnostic(
                    code="FM001",
                    message=f"Pflichtfeld im Frontmatter fehlt oder ist leer: `{required_key}`.",
                )
            )

    if isinstance(meta, dict) and "mode" in meta:
        mode_raw = str(meta.get("mode", "")).strip().lower()
        if mode_raw not in KNOWN_DOCUMENT_MODES:
            diagnostics.append(
                BuildDiagnostic(
                    code="FM002",
                    message=(
                        "Ungueltiger Frontmatter-Wert fuer `mode`: "
                        f"`{meta.get('mode')}`. Erlaubt: ws, test."
                    ),
                )
            )

    for index, (block_type, options, content) in enumerate(blocks):
        if block_type == "answer":
            diagnostics.append(
                BuildDiagnostic(
                    code="AN008",
                    message=(
                        "Legacy-Syntax `:::answer type=...` ist nicht mehr erlaubt. "
                        "Bitte dedizierten Blocktyp nutzen, z. B. `:::grid` oder `:::lines`."
                    ),
                    severity="error",
                    block_index=index,
                    block_type=block_type,
                )
            )
            continue

        absolute_image_paths = _collect_absolute_image_paths(content)
        if absolute_image_paths:
            preview = ", ".join(absolute_image_paths[:2])
            remainder = len(absolute_image_paths) - 2
            remainder_text = f" (+{remainder} weitere)" if remainder > 0 else ""
            diagnostics.append(
                BuildDiagnostic(
                    code="PT001",
                    message=(
                        "Absolute lokale Bildpfade gefunden. "
                        "Bitte relative Projektpfade verwenden: "
                        f"{preview}{remainder_text}"
                    ),
                    block_index=index,
                    block_type=block_type,
                )
            )

        if block_type not in KNOWN_BLOCK_TYPES:
            diagnostics.append(
                BuildDiagnostic(
                    code="BL001",
                    message=f"Unbekannter Blocktyp `{block_type}` wird ignoriert.",
                    block_index=index,
                    block_type=block_type,
                )
            )
            continue

        allowed_options = BLOCK_ALLOWED_OPTIONS.get(block_type, set())
        for option_key, option_value in _option_items(options):
            if option_key == "type" and block_type in ANSWER_BLOCK_TYPES:
                diagnostics.append(
                    BuildDiagnostic(
                        code="AN009",
                        message=(
                            f"Option `type` ist in Block `{block_type}` unzulaessig. "
                            "Der Blocktyp selbst definiert bereits den Antworttyp."
                        ),
                        severity="error",
                        block_index=index,
                        block_type=block_type,
                    )
                )
                continue

            if option_key not in allowed_options:
                diagnostics.append(
                    BuildDiagnostic(
                        code="OP001",
                        message=f"Unbekannte Option `{option_key}` in Block `{block_type}`.",
                        block_index=index,
                        block_type=block_type,
                    )
                )
                continue

            normalized_value = _normalize_value(option_value)
            if option_key == "show" and normalized_value not in KNOWN_SHOW_VALUES:
                _append_invalid_option_value(
                    diagnostics,
                    index,
                    block_type,
                    option_key,
                    option_value,
                    KNOWN_SHOW_VALUES,
                )
            elif option_key == "work" and normalized_value not in KNOWN_WORK_VALUES:
                _append_invalid_option_value(
                    diagnostics,
                    index,
                    block_type,
                    option_key,
                    option_value,
                    KNOWN_WORK_VALUES,
                )
            elif (
                option_key == "action"
                and normalized_value not in KNOWN_ACTION_VALUES
            ):
                _append_invalid_option_value(
                    diagnostics,
                    index,
                    block_type,
                    option_key,
                    option_value,
                    KNOWN_ACTION_VALUES,
                )
            elif option_key == "hint" and normalized_value not in KNOWN_HINT_VALUES:
                _append_invalid_option_value(
                    diagnostics,
                    index,
                    block_type,
                    option_key,
                    option_value,
                    KNOWN_HINT_VALUES,
                )
        if block_type not in ANSWER_BLOCK_TYPES:
            continue

        answer_type = block_type

        if is_effectively_empty_answer_content(content):
            diagnostics.append(
                BuildDiagnostic(
                    code="AN005",
                    message=(
                        "Answer-Block ist leer. Best Practice: Antwortfelder mit "
                        "Startimpulsen oder Strukturierung vorfuellen."
                    ),
                    block_index=index,
                    block_type=block_type,
                )
            )

        marker_conflicts = collect_answer_marker_conflict_lines(content)
        if marker_conflicts:
            preview = ", ".join(str(value) for value in marker_conflicts[:5])
            remainder = len(marker_conflicts) - 5
            remainder_text = (
                f" (+{remainder} weitere)" if remainder > 0 else ""
            )
            diagnostics.append(
                BuildDiagnostic(
                    code="AN006",
                    message=(
                        "Answer-Zeilen mit ungueltiger §/%/&-Token-Syntax gefunden "
                        f"(Zeilen: {preview}{remainder_text}). "
                        "Bitte Marker als §{...}, %{...} oder &{...} schliessen."
                    ),
                    block_index=index,
                    block_type=block_type,
                )
            )

        if answer_type in YAML_ANSWER_TYPES and (content or "").strip():
            try:
                parsed = yaml.safe_load(content)
            except yaml.YAMLError as error:
                diagnostics.append(
                    BuildDiagnostic(
                        code="AN003",
                        message=f"YAML-Fehler in answer `{answer_type}`: {error}",
                        severity="error",
                        block_index=index,
                        block_type=block_type,
                    )
                )
                continue

            if parsed is not None and not isinstance(parsed, dict):
                diagnostics.append(
                    BuildDiagnostic(
                        code="AN004",
                        message=(
                            f"Answer `{answer_type}` erwartet YAML-Mapping (Key-Value), "
                            "kein Skalar oder Listen-Root."
                        ),
                        block_index=index,
                        block_type=block_type,
                    )
                )

            if isinstance(parsed, dict):
                _validate_payload_show_markers(diagnostics, index, answer_type, parsed)

        if answer_type == "matching":
            first_count, second_count = _get_matching_item_counts(options, content)
            if first_count == 1 or second_count == 1:
                diagnostics.append(
                    BuildDiagnostic(
                        code="MA001",
                        message=(
                            "Matching mit nur einem Element auf einer Seite ist "
                            "didaktisch nicht sinnvoll (1↔N)."
                        ),
                        block_index=index,
                        block_type=block_type,
                    )
                )

    return diagnostics


def has_blocking_diagnostics(diagnostics):
    """Return true when diagnostics contain critical errors."""
    for diagnostic in diagnostics or []:
        if diagnostic.severity == "error":
            return True
        if diagnostic.code in CRITICAL_DIAGNOSTIC_CODES:
            return True
    return False


def summarize_blocking_diagnostics(diagnostics):
    """Create compact error summary text for blocking diagnostics."""
    blocking = [
        diagnostic
        for diagnostic in (diagnostics or [])
        if diagnostic.severity == "error"
        or diagnostic.code in CRITICAL_DIAGNOSTIC_CODES
    ]
    if not blocking:
        return ""

    lines = []
    for diagnostic in blocking[:5]:
        location = (
            f" [Block {diagnostic.block_index}]"
            if diagnostic.block_index is not None
            else ""
        )
        lines.append(f"- {diagnostic.code}{location}: {diagnostic.message}")

    remaining = len(blocking) - len(lines)
    if remaining > 0:
        lines.append(f"- ... und {remaining} weitere kritische Fehler")

    return "\n".join(lines)


def inspect_markdown_text(markdown_text):
    """Parse markdown text and return parsed document plus diagnostics."""
    meta, _content_unused = split_front_matter(markdown_text)
    content, content_base_line = _extract_validation_content_and_base_line(markdown_text)
    blocks = parse_blocks(content)
    diagnostics = _collect_document_diagnostics(
        meta,
        blocks,
        content,
        content_base_line=content_base_line,
    )
    return InspectedDocument(meta=meta, blocks=blocks, diagnostics=diagnostics)


def inspect_markdown_document(md_path):
    """Read markdown file and return parsed document plus diagnostics."""
    md_file = Path(md_path)
    text = md_file.read_text(encoding="utf-8")
    return inspect_markdown_text(text)
