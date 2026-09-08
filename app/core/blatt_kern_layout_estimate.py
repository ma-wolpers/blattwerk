"""Schaetzt den Platzbedarf von Bloecken fuer automatische Spaltenbreiten.

Unterste Schicht der `blatt_kern_layout_*`-Modulfamilie (siehe
`blatt_kern_layout_render.py`s Modul-Docstring fuer die Gesamtuebersicht) --
kennt keinen der anderen drei Module, wird nur von
`blatt_kern_layout_columns.py::auto_columns_template` importiert.
"""

from __future__ import annotations

import re

from .answer_special import (
    estimate_checkgrid_weight,
    estimate_crossword_weight,
    estimate_matching_weight,
    estimate_ordering_weight,
    estimate_wordsearch_weight,
)
from .answer_special_mindmap import estimate_mindmap_weight
from .answer_special_writebox import estimate_writebox_weight
from .blatt_kern_shared import _safe_int, should_render_block


def parse_height_cm(height_value, default_cm=4.0):
    """Extrahiert Zentimeterwerte aus Strings wie `4cm`."""
    if not height_value:
        return default_cm

    match = re.fullmatch(
        r"\s*(\d+(?:\.\d+)?)\s*cm\s*", str(height_value), flags=re.IGNORECASE
    )
    if match:
        return float(match.group(1))
    return default_cm


def estimate_block_weight(
    block_type,
    options,
    content,
    include_solutions,
    document_mode="worksheet",
):
    """Schätzt den Platzbedarf eines Blocks für automatische Spaltenbreiten."""
    if not should_render_block(
        block_type,
        options,
        include_solutions,
        document_mode=document_mode,
    ):
        return 0.0

    cleaned = re.sub(r"[`*_#>\-\|\[\]\(\)]", " ", content or "")
    text_length = max(0, len(cleaned.strip()))
    if block_type == "raw" and text_length == 0:
        return 0.0

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    longest_line = max((len(line) for line in lines), default=0)
    text_complexity = (text_length / 120.0) + (longest_line / 55.0)

    if block_type in {"material", "task", "info", "raw", "solution"}:
        type_factor = {
            "material": 1.45,
            "info": 1.35,
            "raw": 1.10,
            "solution": 1.05,
            "task": 0.45,
        }.get(block_type, 1.0)
        base = 0.55
        if block_type == "task":
            base = 0.25
        return base + (text_complexity * type_factor)

    if block_type == "qrcode":
        size_hint = (
            options.get("h")
            or options.get("height")
            or options.get("w")
            or options.get("width")
            or "3cm"
        )
        return max(1.0, parse_height_cm(size_hint, default_cm=3.0) * 0.85)

    if block_type == "mindmap":
        return estimate_mindmap_weight(options, content)

    if block_type == "writebox":
        return estimate_writebox_weight(options, content)

    if block_type in {
        "lines",
        "grid",
        "geometry",
        "dots",
        "space",
        "table",
        "numberline",
        "mc",
        "cloze",
        "matching",
        "wordsearch",
        "crossword",
        "ordering",
        "checkgrid",
    }:
        if block_type == "mc":
            base = 1.0 + (text_length / 140.0)
            return min(4.2, max(1.0, base))

        if block_type == "cloze":
            gap_count = len(re.findall(r"\{\{\s*[^{}]+\s*\}\}", content or ""))
            base = 1.0 + (gap_count * 0.45) + (text_length / 240.0)
            return min(4.8, max(1.0, base))

        if block_type == "matching":
            return estimate_matching_weight(text_length, include_solutions)

        if block_type == "wordsearch":
            return estimate_wordsearch_weight(options, content)

        if block_type == "crossword":
            return estimate_crossword_weight(options, content)

        if block_type == "ordering":
            return estimate_ordering_weight(options, content)

        if block_type == "checkgrid":
            return estimate_checkgrid_weight(options, content)

        if include_solutions:
            if text_length == 0:
                return 0.0

            if block_type == "lines":
                rows = max(1, _safe_int(options.get("rows", 3), 3))
                return max(1.0, rows * 0.7)
            if block_type == "grid":
                rows = max(1, _safe_int(options.get("rows", 5), 5))
                return max(1.4, rows * 0.85 + (text_length / 260.0))
            if block_type == "geometry":
                rows = max(1, _safe_int(options.get("rows", 5), 5))
                cols = _safe_int(options.get("cols", 20), 20) if options.get("cols") else 20
                return max(1.6, (rows * cols) / 52.0 + (text_length / 320.0))
            if block_type == "dots":
                return max(
                    1.2,
                    parse_height_cm(options.get("height", "4cm")) * 0.9
                    + (text_length / 240.0),
                )
            if block_type == "space":
                return max(
                    1.2,
                    parse_height_cm(options.get("height", "3cm")) * 0.85
                    + (text_length / 240.0),
                )
            if block_type == "numberline":
                return max(
                    1.0,
                    parse_height_cm(options.get("height", "2.7cm")) * 0.9
                    + (text_length / 260.0),
                )

            return max(1.0, text_length / 180.0)

        if block_type == "lines":
            return max(0.8, _safe_int(options.get("rows", 3), 3) * 0.7)
        if block_type == "grid":
            rows = _safe_int(options.get("rows", 5), 5)
            cols = _safe_int(options.get("cols", 20), 20) if options.get("cols") else 20
            return max(1.2, (rows * cols) / 55.0)
        if block_type == "geometry":
            rows = _safe_int(options.get("rows", 5), 5)
            cols = _safe_int(options.get("cols", 20), 20) if options.get("cols") else 20
            return max(1.4, (rows * cols) / 48.0)
        if block_type == "dots":
            return max(1.0, parse_height_cm(options.get("height", "4cm")) * 1.1)
        if block_type == "space":
            return max(1.0, parse_height_cm(options.get("height", "3cm")) * 1.0)
        if block_type == "numberline":
            return max(0.9, parse_height_cm(options.get("height", "2.7cm")) * 0.85)

    return max(0.6, text_length / 180.0)


def auto_columns_template(columns_blocks, include_solutions, document_mode="worksheet"):
    """Erzeugt ein Verhältnis-Template basierend auf geschätzten Spaltengewichten."""
    weights = []
    for column_blocks in columns_blocks:
        column_weight = 0.0
        for block_type, options, content in column_blocks:
            column_weight += estimate_block_weight(
                block_type,
                options,
                content,
                include_solutions,
                document_mode=document_mode,
            )
        weights.append(max(0.8, min(column_weight, 7.0)))

    if not weights:
        return None

    return " ".join(f"{weight:.2f}fr" for weight in weights)
