"""Validierung der YAML-Payload-Einträge bei `geometry`/`numberline`-Antwortblöcken.

Aktuell (Phase 0/Refactor) nur die bestehende Marker-Sichtbarkeitsprüfung
(`show`-Werte in `points`/`pairs`/`functions`/...). Eine spätere Phase
ergänzt hier `_validate_geometry_entry_fields`, die zusätzlich unbekannte
Objekt-Keys sowie ungültige `line`/`color`/`thickness`-Werte erkennt — unter
Wiederverwendung derselben normativen Definitionen, die auch der Renderer
(`answer_grid_entries.py`) nutzt.
"""

from __future__ import annotations

from .blatt_validator_constants import (
    GRID_MARKER_SHOW_VALUES,
    MARKER_SHOW_SECTIONS_BY_ANSWER_TYPE,
    NUMBERLINE_ANSWER_TYPES,
)
from .blatt_validator_value_helpers import _append_invalid_yaml_show_diagnostic


def _canonical_yaml_answer_type(answer_type):
    """Bildet Alias-Antworttypen (z. B. `numberline`-Varianten) auf ihren kanonischen Namen ab."""
    if answer_type in NUMBERLINE_ANSWER_TYPES:
        return "numberline"
    return answer_type


def _validate_payload_show_markers(diagnostics, block_index, answer_type, parsed_payload):
    """Validiert Marker-only `show`-Werte in YAML-Antwort-Sektionen (`AN007`)."""
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
