"""Validierung der YAML-Payload-Einträge bei `geometry`/`numberline`-Antwortblöcken.

Zwei unabhängige Prüfschritte: die bestehende Marker-Sichtbarkeitsprüfung
(`show`-Werte, `_validate_payload_show_markers`) sowie die neue
Objekt-Feld-Prüfung (`_validate_geometry_entry_fields`), die unbekannte
YAML-Keys sowie ungültige `line`/`color`/`thickness`-Werte in
`geometry`-Sektionen erkennt. Letztere nutzt bewusst dieselben normativen
Definitionen wie der Renderer — `GEOMETRY_ENTRY_ALLOWED_KEYS` aus
`answer_grid_entries.py` sowie `parse_svg_color`/`parse_svg_thickness` aus
`answer_special_shared.py` — statt eigene, potenziell abweichende Kopien zu
pflegen.
"""

from __future__ import annotations

from .answer_grid_entries import GEOMETRY_ENTRY_ALLOWED_KEYS
from .answer_special_shared import parse_svg_color, parse_svg_thickness
from .blatt_validator_constants import (
    GRID_MARKER_SHOW_VALUES,
    MARKER_SHOW_SECTIONS_BY_ANSWER_TYPE,
    NUMBERLINE_ANSWER_TYPES,
)
from .blatt_validator_types import BuildDiagnostic
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


def _validate_geometry_entry_fields(diagnostics, block_index, answer_type, parsed_payload):
    """Validiert Objekt-Felder in `geometry`-YAML-Sektionen: unbekannte Keys, ungültige `line`/`color`/`thickness`.

    Iteriert über alle vier Sektionen aus `GEOMETRY_ENTRY_ALLOWED_KEYS`
    (`points`/`sequence`/`pairs`/`functions`) und meldet je Eintrag:
    - jeden Key außerhalb der für die Sektion erlaubten Menge (`AN011`);
    - bei `pairs` einen vorhandenen, aber ungültigen `line`-Wert (`AN012`)
      — eine eigene Diagnose-Ebene, getrennt von der Block-Option
      `line=solid|dashed` bei `:::grid`/`:::geometry` (`OP002`), die einen
      anderen DSL-Konzept mit demselben Namen prüft;
    - einen vorhandenen, aber ungültigen `color`-Wert (`AN013`), erkannt
      über dieselbe `parse_svg_color`-Funktion, die auch der Renderer nutzt;
    - einen vorhandenen, aber ungültigen `thickness`-Wert (`AN014`), analog
      über `parse_svg_thickness`.

    Ein fehlender oder `None`-Wert für `line`/`color`/`thickness` wird
    nicht gemeldet (konsistent mit der `show`-Feld-Behandlung in
    `_validate_payload_show_markers`) — nur ein *vorhandener, aber
    ungültiger* Wert ist eine Diagnose wert.
    """
    if answer_type != "geometry" or not isinstance(parsed_payload, dict):
        return

    for section, allowed_keys in GEOMETRY_ENTRY_ALLOWED_KEYS.items():
        entries = parsed_payload.get(section)
        if not isinstance(entries, list):
            continue

        for idx, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                continue

            for key in entry:
                if key not in allowed_keys:
                    diagnostics.append(
                        BuildDiagnostic(
                            code="AN011",
                            message=(
                                f"Unbekannter Key `{key}` in `{section}[{idx}]` bei answer `geometry`. "
                                f"Erlaubt: {', '.join(sorted(allowed_keys))}."
                            ),
                            block_index=block_index,
                            block_type=answer_type,
                        )
                    )

            raw_line = entry.get("line")
            if section == "pairs" and raw_line is not None:
                normalized_line = str(raw_line).strip().lower()
                if normalized_line not in ("solid", "dashed"):
                    diagnostics.append(
                        BuildDiagnostic(
                            code="AN012",
                            message=(
                                f"Ungueltiger Wert fuer `line` in `pairs[{idx}]`: `{raw_line}`. "
                                "Erlaubt: solid, dashed."
                            ),
                            severity="error",
                            block_index=block_index,
                            block_type=answer_type,
                        )
                    )

            raw_color = entry.get("color")
            if raw_color is not None and parse_svg_color(raw_color) is None:
                diagnostics.append(
                    BuildDiagnostic(
                        code="AN013",
                        message=(
                            f"Ungueltiger Farbwert fuer `color` in `{section}[{idx}]`: `{raw_color}`."
                        ),
                        block_index=block_index,
                        block_type=answer_type,
                    )
                )

            raw_thickness = entry.get("thickness")
            if raw_thickness is not None and parse_svg_thickness(raw_thickness) is None:
                diagnostics.append(
                    BuildDiagnostic(
                        code="AN014",
                        message=(
                            f"Ungueltiger Wert fuer `thickness` in `{section}[{idx}]`: `{raw_thickness}`. "
                            "Erwartet: positive Zahl."
                        ),
                        block_index=block_index,
                        block_type=answer_type,
                    )
                )
