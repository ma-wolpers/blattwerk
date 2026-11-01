"""Inhaltliche Prüfungen offener Blöcke und der Blockfolge im Dokument.

Zuständig für `selfcheck`, `mindmap`, `help`, Aufgabentitel und dokumentweite Regeln wie
„eine Teilaufgabe braucht eine Aufgabe davor“.
"""

from __future__ import annotations

import re

from .answer_special_mindmap import BRANCH_LIMITS, SUBBRANCH_LIMITS
from .answer_special_shared import _safe_int, parse_bullet_list_lines
from .answer_table_layout import width_tokens
from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic

_TITLE_NUMBER_RE = re.compile(r"^\s*(?:Aufgabe|Teilaufgabe|Nr\.?)\s*\d+", re.IGNORECASE)
_HELP_LEVELS = (1, 99)


def check_selfcheck(collect, options, content) -> None:
    """Selbsteinschätzung: Aussagen vorhanden, Spaltennamen nur mit `dual` (`AN050`, `AN051`)."""
    if not parse_bullet_list_lines(content):
        collect.add("AN050", "Der Block enthält keine Aussagen.")
    dual = str(options.get("dual") or "").strip().lower() in {"1", "true", "yes", "on"}
    if (options.get("label1") or options.get("label2")) and not dual:
        collect.add("AN051", "`label1`/`label2` wirken nur zusammen mit `dual=true`.")


def check_mindmap(collect, options, content) -> None:
    """Mindmap: Thema vorhanden, Zweigzahl im darstellbaren Bereich (`AN052`, `AN053`)."""
    if not (content or "").strip():
        collect.add("AN052", "Es fehlt das Thema in der Mitte.")
    for key, (low, high) in (("branches", BRANCH_LIMITS), ("subbranches", SUBBRANCH_LIMITS)):
        if key in options and not low <= _safe_int(options.get(key), low) <= high:
            collect.add("AN053", f"`{key}={options[key]}` liegt außerhalb von {low} bis {high} und wird angepasst.", anchor=f"AN053:{key}")


def check_help(collect, options, _content) -> None:
    """Lernhilfe: `level` liegt im dokumentierten Bereich (`AN054`)."""
    low, high = _HELP_LEVELS
    if "level" in options and not low <= _safe_int(options.get("level"), low - 1) <= high:
        collect.add("AN054", f"`level={options['level']}` liegt außerhalb von {low} bis {high}.")


def check_task_title(collect, options, _content) -> None:
    """Aufgabentitel ohne Nummer: Der Renderer nummeriert selbst (`BL016`)."""
    title = str(options.get("title") or "")
    if _TITLE_NUMBER_RE.match(title):
        collect.add("BL016", f"`title=\"{title}\"` enthält eine Nummer. Aufgaben werden automatisch nummeriert, sonst steht sie doppelt.")


def _diagnostic(code: str, message: str, index: int, block_type: str, options) -> BuildDiagnostic:
    """Warnung an einem Block."""
    return BuildDiagnostic(
        code=code,
        message=message,
        block_index=index,
        block_type=block_type,
        region_id=compute_block_region_id(block_type, options or {}),
        anchor=code,
    )


def check_document_structure(blocks) -> list[BuildDiagnostic]:
    """Regeln über mehrere Blöcke: Teilaufgabe nach Aufgabe, Spaltenbreiten passend (`BL014`, `BL015`)."""
    diagnostics: list[BuildDiagnostic] = []
    seen_task = False
    for index, (block_type, options, _content) in enumerate(blocks):
        if block_type == "task":
            seen_task = True
        elif block_type == "subtask" and not seen_task:
            diagnostics.append(_diagnostic("BL015", "Vor dieser Teilaufgabe steht keine Aufgabe.", index, block_type, options))
        elif block_type == "columns":
            raw = (options or {}).get("widths") or (options or {}).get("ratio")
            cols = _safe_int((options or {}).get("cols"), 2)
            if raw and len(width_tokens(raw)) != cols:
                diagnostics.append(_diagnostic("BL014", f"`widths` hat {len(width_tokens(raw))} Werte bei `cols={cols}`.", index, block_type, options))
    return diagnostics
