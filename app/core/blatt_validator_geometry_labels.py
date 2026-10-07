"""Diagnose AN019: Geometry-Beschriftung ohne kollisionsfreien Platz.

Rechnet das Label-Layout mit genau denselben Bausteinen nach wie der Renderer
(`resolve_geometry_frame`, `build_geometry_scene`, `layout_labels`), für die
Arbeitsblatt- und die Lösungsfassung. Meldet jedes Label, das nach
Kandidatenwahl, Relaxation und erweiterter Ringsuche noch ein Punktkreuz oder
eine andere Beschriftung überdeckt -- einmal je Text und Block. Nur bei
`labels=auto`; mit `labels=fixed` wird bewusst nichts verschoben und nichts
gemeldet.
"""

from __future__ import annotations

from .answer_grid_frame import resolve_geometry_frame
from .answer_grid_label_layout import LABELS_FIXED, layout_labels, resolve_labels_mode
from .answer_grid_primitives import build_geometry_scene
from .answer_yaml_payload import parse_yaml_answer_payload_with_solution
from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic


def unresolved_geometry_labels(options, content) -> list[str]:
    """Texte der Labels, die in keiner Fassung kollisionsfrei platzierbar sind (sortiert nach Auftreten)."""
    if resolve_labels_mode(options.get("labels")) == LABELS_FIXED:
        return []
    try:
        payload, _solution = parse_yaml_answer_payload_with_solution(content)
    except Exception:  # YAML-Fehler meldet bereits AN003
        return []
    frame = resolve_geometry_frame(options)
    result: list[str] = []
    for include_solutions in (False, True):
        scene = build_geometry_scene(options, payload, frame.height_units, frame.width_units, include_solutions)
        if scene is None:
            return []
        placement = layout_labels(scene.labels, scene.obstacles, frame.width_units, frame.height_units, frame.bleed_units)
        result.extend(text for text in placement.unresolved if text not in result)
    return result


def validate_geometry_labels(blocks) -> list[BuildDiagnostic]:
    """AN019 (Warnung) für jeden `geometry`-Block mit nicht kollisionsfrei platzierbaren Beschriftungen."""
    diagnostics = []
    for index, (block_type, options, content) in enumerate(blocks):
        if block_type != "geometry":
            continue
        unresolved = unresolved_geometry_labels(options, content)
        if not unresolved:
            continue
        names = ", ".join(f"„{text}“" for text in unresolved)
        diagnostics.append(BuildDiagnostic(
            code="AN019",
            message=(
                f"Geometry: Beschriftung {names} findet keinen Platz, an dem sie keinen Punkt bzw. keine andere "
                "Beschriftung überdeckt -- Zeichnung größer machen, Punkte weiter auseinander legen oder Text kürzen."
            ),
            block_index=index,
            block_type=block_type,
            region_id=compute_block_region_id(block_type, options),
            anchor="AN019",
        ))
    return diagnostics
