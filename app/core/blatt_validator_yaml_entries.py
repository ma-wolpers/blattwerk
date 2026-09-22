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

from .answer_grid_axis import _resolve_axis_state
from .answer_grid_entries import GEOMETRY_ENTRY_ALLOWED_KEYS
from .answer_grid_validity import (
    _circle_center_and_radius_are_valid,
    _describe_circle_angle_problem,
    _polygon_vertices_are_valid,
)
from .answer_special_shared import parse_svg_color, parse_svg_thickness
from .blatt_validator_constants import (
    GRID_MARKER_SHOW_VALUES,
    MARKER_SHOW_SECTIONS_BY_ANSWER_TYPE,
    NUMBERLINE_ANSWER_TYPES,
)
from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic
from .blatt_validator_value_helpers import _append_invalid_yaml_show_diagnostic


def _canonical_yaml_answer_type(answer_type):
    """Bildet Alias-Antworttypen (z. B. `numberline`-Varianten) auf ihren kanonischen Namen ab."""
    if answer_type in NUMBERLINE_ANSWER_TYPES:
        return "numberline"
    return answer_type


def _validate_payload_show_markers(diagnostics, block_index, answer_type, parsed_payload, options=None):
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
                    options,
                )


def _validate_geometry_entry_fields(diagnostics, block_index, answer_type, parsed_payload, options=None):
    """Validiert Objekt-Felder in `geometry`-YAML-Sektionen: unbekannte Keys, ungültige `line`/`color`/`thickness`.

    Iteriert über alle vier Sektionen aus `GEOMETRY_ENTRY_ALLOWED_KEYS`
    (`points`/`sequence`/`pairs`/`functions`) und meldet je Eintrag:
    - jeden Key außerhalb der für die Sektion erlaubten Menge (`AN011`);
    - bei `pairs` einen vorhandenen, aber ungültigen `line`-Wert (`AN012`)
      — eine eigene Diagnose-Ebene, getrennt von der Block-Option
      `line=solid|dashed` bei `:::grid`/`:::geometry` (`OP002`), die einen
      anderen DSL-Konzept mit demselben Namen prüft;
    - einen vorhandenen, aber ungültigen `color`- ODER `fill`-Wert (`AN013`
      für beide -- dieselbe `parse_svg_color`-Validierung, nur ein anderer
      Feldname), erkannt über dieselbe Funktion, die auch der Renderer nutzt;
    - einen vorhandenen, aber ungültigen `thickness`-Wert (`AN014`), analog
      über `parse_svg_thickness`.

    Ein fehlender oder `None`-Wert für `line`/`color`/`fill`/`thickness`
    wird nicht gemeldet (konsistent mit der `show`-Feld-Behandlung in
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

            region_id = compute_block_region_id(answer_type, options or {})

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
                            region_id=region_id,
                            anchor=f"{section}[{idx}].{key}",
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
                            region_id=region_id,
                            anchor=f"{section}[{idx}].line",
                        )
                    )

            for color_field in ("color", "fill"):
                raw_color = entry.get(color_field)
                if raw_color is not None and parse_svg_color(raw_color) is None:
                    diagnostics.append(
                        BuildDiagnostic(
                            code="AN013",
                            message=(
                                f"Ungueltiger Farbwert fuer `{color_field}` in `{section}[{idx}]`: "
                                f"`{raw_color}`."
                            ),
                            block_index=block_index,
                            block_type=answer_type,
                            region_id=region_id,
                            anchor=f"{section}[{idx}].{color_field}",
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
                        region_id=region_id,
                        anchor=f"{section}[{idx}].thickness",
                    )
                )


def _validate_geometry_axis_dependent_sections(diagnostics, block_index, answer_type, parsed_payload, options=None):
    """Warnt, wenn `functions` gesetzt ist, aber kein aktiver Achsenmodus vorliegt (`AN015`).

    `functions` bleibt bewusst axis-only (ein Funktionsgraph ohne
    mathematisches Koordinatensystem ist nicht definiert) -- anders als
    `pairs`/`sequence`, die inzwischen auch ohne Achse rendern (impliziter
    Ursprung unten links), bleibt `functions` ohne aktive Achse ein reiner,
    stiller Ausfall. Nutzt `_resolve_axis_state` (`answer_grid_axis.py`),
    dieselbe Funktion wie Renderer und `OP005`-Prüfung, damit diese
    Diagnose nicht unabhängig von der tatsächlichen Achsenlogik abweicht.
    """
    if answer_type != "geometry" or not isinstance(parsed_payload, dict):
        return

    functions_entries = parsed_payload.get("functions")
    if not isinstance(functions_entries, list) or not functions_entries:
        return

    axis_state, _origin = _resolve_axis_state(options or {})
    if axis_state == "active":
        return

    diagnostics.append(
        BuildDiagnostic(
            code="AN015",
            message=(
                "`functions` wird nur im Achsenmodus gerendert (`axis=true` mit gueltigem "
                "`origin`). Ohne aktiven Achsenmodus bleiben alle Eintraege dieser Sektion "
                "unsichtbar."
            ),
            block_index=block_index,
            block_type=answer_type,
            region_id=compute_block_region_id(answer_type, options or {}),
            anchor="functions",
        )
    )


def _validate_geometry_shape_entries(diagnostics, block_index, answer_type, parsed_payload, options=None):
    """Validiert `polygons[]`/`circles[]`-Ganz-Eintrag-Gültigkeit (`AN017`/`AN018`).

    Nutzt exakt dieselben Prädikate wie die jeweiligen Parser
    (`_parse_polygons`/`_parse_circles`, `answer_grid_shapes.py`) --
    importiert aus dem neutralen `answer_grid_validity.py`, nicht aus dem
    Renderer-Modul selbst, damit der Validator nie von Renderer-Code
    abhängen muss. `AN018` deckt beide Fehlerklassen eines `circles`-
    Eintrags ab (ungültiges `cx`/`cy`/`r` UND unvollständiges/teilweise
    unparsebares Winkelpaar) -- beide sind konzeptionell "dieser Eintrag
    ist als Ganzes fehlerhaft, wird komplett übersprungen"; die Meldung
    selbst unterscheidet über `_describe_circle_angle_problem()` die genaue
    Ursache.
    """
    if answer_type != "geometry" or not isinstance(parsed_payload, dict):
        return
    region_id = compute_block_region_id(answer_type, options or {})

    polygon_entries = parsed_payload.get("polygons")
    if isinstance(polygon_entries, list):
        for idx, entry in enumerate(polygon_entries, start=1):
            if not isinstance(entry, dict):
                continue
            if not _polygon_vertices_are_valid(entry.get("vertices")):
                diagnostics.append(
                    BuildDiagnostic(
                        code="AN017",
                        message=(
                            f"Ungueltiges Polygon in `polygons[{idx}]`: `vertices` braucht "
                            "mindestens 3 Eintraege, jeweils mit numerischem `x`/`y`. Das "
                            "gesamte Polygon wird nicht gerendert (kein Teil-Repair einzelner "
                            "Eckpunkte)."
                        ),
                        block_index=block_index,
                        block_type=answer_type,
                        region_id=region_id,
                        anchor=f"polygons[{idx}].vertices",
                    )
                )

    circle_entries = parsed_payload.get("circles")
    if isinstance(circle_entries, list):
        for idx, entry in enumerate(circle_entries, start=1):
            if not isinstance(entry, dict):
                continue
            if not _circle_center_and_radius_are_valid(entry):
                diagnostics.append(
                    BuildDiagnostic(
                        code="AN018",
                        message=(
                            f"Ungueltiger Kreis/Bogen in `circles[{idx}]`: `cx`/`cy`/`r` "
                            "muessen numerisch gesetzt sein und `r` muss positiv sein. Der "
                            "Eintrag wird nicht gerendert."
                        ),
                        block_index=block_index,
                        block_type=answer_type,
                        region_id=region_id,
                        anchor=f"circles[{idx}]",
                    )
                )
                continue
            angle_problem = _describe_circle_angle_problem(entry)
            if angle_problem is not None:
                diagnostics.append(
                    BuildDiagnostic(
                        code="AN018",
                        message=(
                            f"Ungueltiger Kreis/Bogen in `circles[{idx}]`: {angle_problem}. Der "
                            "Eintrag wird nicht gerendert."
                        ),
                        block_index=block_index,
                        block_type=answer_type,
                        region_id=region_id,
                        anchor=f"circles[{idx}]",
                    )
                )
