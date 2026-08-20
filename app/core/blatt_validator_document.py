"""Kern-Validierungsschritte für ein geparstes Blattwerk-Dokument.

Zerlegt die eigentliche Dokumentprüfung in fokussierte Schritte, die vom
schlanken Orchestrator in `blatt_validator.py` in fester Reihenfolge pro
Block aufgerufen werden: Frontmatter (`_validate_frontmatter`),
block-typ-spezifische Checks (`_validate_block_type_specifics`) und
YAML-Antwort-Payloads (`_validate_yaml_answer_payload`). Die
Options-Validierung selbst lebt in `blatt_validator_block_options.py`
(ausgelagert, da sie allein bereits ein Drittel dieser Datei ausmachte).
Die Aufteilung folgt exakt der ursprünglichen, in einer einzigen
~400-Zeilen-Funktion verschachtelten Logik — bewusst ohne
Verhaltensänderung, siehe Test-Parität nach dem Split.
"""

from __future__ import annotations

import yaml

from .answer_line_markers import (
    collect_answer_marker_conflict_lines,
    is_effectively_empty_answer_content,
)
from .blatt_validator_constants import (
    ANSWER_BLOCK_TYPES,
    KNOWN_DOCUMENT_MODES,
    KNOWN_PRESENTATION_LAYOUTS,
    REQUIRED_FRONTMATTER_FIELDS,
    YAML_ANSWER_TYPES,
)
from .blatt_validator_marker_syntax import _has_explicit_worksheet_marker_without_solution
from .blatt_validator_types import BuildDiagnostic
from .blatt_validator_value_helpers import _get_matching_item_counts, _is_truthy_meta_bool
from .blatt_validator_yaml_entries import _validate_payload_show_markers


def _validate_frontmatter(meta):
    """Validiert Frontmatter-Felder (`FM001`-`FM005`) und liefert die gefundenen Diagnosen."""
    diagnostics = []

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
                        f"`{meta.get('mode')}`. Erlaubt: worksheet, solution, presentation, ws, test."
                    ),
                )
            )

    if isinstance(meta, dict) and "tag" in meta:
        tag_value = meta.get("tag")
        if isinstance(tag_value, (dict, list)):
            diagnostics.append(
                BuildDiagnostic(
                    code="FM003",
                    message=(
                        "Ungueltiger Frontmatter-Wert fuer `tag`: "
                        "Erlaubt ist ein einfacher Textwert (z. B. `1`, `A`, `TAG`)."
                    ),
                    severity="error",
                )
            )
        elif not str(tag_value).strip():
            diagnostics.append(
                BuildDiagnostic(
                    code="FM003",
                    message=(
                        "Ungueltiger Frontmatter-Wert fuer `tag`: leerer Wert ist nicht erlaubt."
                    ),
                    severity="error",
                )
            )

    if isinstance(meta, dict):
        if "presentation_layout" in meta:
            layout_value = str(meta.get("presentation_layout") or "").strip()
            if layout_value and layout_value not in KNOWN_PRESENTATION_LAYOUTS:
                diagnostics.append(
                    BuildDiagnostic(
                        code="FM004",
                        message=(
                            "Ungueltiger Frontmatter-Wert fuer `presentation_layout`: "
                            f"`{layout_value}`. Erlaubt: "
                            f"{', '.join(sorted(KNOWN_PRESENTATION_LAYOUTS))}."
                        ),
                        severity="error",
                    )
                )

        for bool_key in (
            "presentation_show_mini_header",
            "presentation_show_section_footer",
        ):
            if bool_key in meta and not _is_truthy_meta_bool(meta.get(bool_key)):
                diagnostics.append(
                    BuildDiagnostic(
                        code="FM005",
                        message=(
                            f"Ungueltiger Frontmatter-Wert fuer `{bool_key}`. "
                            "Erlaubt sind boolesche Werte (z. B. true/false, ja/nein, 1/0)."
                        ),
                        severity="error",
                    )
                )

    return diagnostics


def _validate_block_type_specifics(diagnostics, index, block_type, content, qrcode_url_value):
    """Prüft block-typ-spezifische Invarianten nach der Options-Validierung.

    Liefert `True`, wenn `block_type` ein Antwort-Blocktyp ist (dann folgt
    im Orchestrator noch `_validate_yaml_answer_payload`), sonst `False`.
    """
    if block_type == "qrcode" and not qrcode_url_value:
        diagnostics.append(
            BuildDiagnostic(
                code="QR001",
                message="Block `qrcode` benoetigt die Pflichtoption `url=...`.",
                severity="error",
                block_index=index,
                block_type=block_type,
            )
        )

    if block_type in {"task", "subtask"} and _has_explicit_worksheet_marker_without_solution(
        content
    ):
        diagnostics.append(
            BuildDiagnostic(
                code="AN010",
                message=(
                    f"Block `{block_type}` nutzt `§`-Marker ohne sichtbares "
                    "Loesungs-Gegenstueck. Pruefe, ob zu jedem nur im "
                    "Arbeitsblatt sichtbaren Aufgabenteil auch eine explizite "
                    "Loesung vorhanden ist (z. B. mit `%`-Marker)."
                ),
                block_index=index,
                block_type=block_type,
            )
        )

    if block_type not in ANSWER_BLOCK_TYPES:
        return False

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
        remainder_text = f" (+{remainder} weitere)" if remainder > 0 else ""
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

    if _has_explicit_worksheet_marker_without_solution(content):
        diagnostics.append(
            BuildDiagnostic(
                code="AN010",
                message=(
                    f"Block `{block_type}` nutzt `§`-Marker ohne sichtbares "
                    "Loesungs-Gegenstueck. Pruefe, ob zu jedem nur im "
                    "Arbeitsblatt sichtbaren Aufgabenteil auch eine explizite "
                    "Loesung vorhanden ist (z. B. mit `%`-Marker)."
                ),
                block_index=index,
                block_type=block_type,
            )
        )

    return True


def _validate_yaml_answer_payload(diagnostics, index, block_type, options, content):
    """Parst und validiert den YAML-Payload eines Antwortblocks (`AN003`/`AN004`/`AN007`/`MA001`).

    Bricht (per `return`) vor der `matching`-Elementzahlprüfung ab, wenn
    das YAML nicht parsebar war — analog zum ursprünglichen `continue` in
    der monolithischen Schleife, das denselben Effekt hatte.
    """
    answer_type = block_type

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
            return

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
