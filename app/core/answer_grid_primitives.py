"""Rendert die optionalen Geometrie-Objekte (Achsen, Punkte, Strecken, Funktionsgraphen, Polygone) als SVG-Overlay.

Konsumiert die geparsten Einträge aus `answer_grid_entries.py`/
`answer_grid_shapes.py` sowie die Achsen-Rendering-Bausteine aus
`answer_grid_axis.py`/`answer_grid_axis_names.py` und setzt sie zu einem
einzigen SVG-Overlay zusammen, das über dem Hintergrund-Raster
(`answer_grid_svg_frame.py`) liegt.

Jeder Section-Renderer liefert `(shapes, label_specs, obstacles)`: SVG der
Objekte, Beschreibungen ihrer Labels (`LabelSpec`, Standardposition = bisheriger
fester Versatz) und die Hindernisse fürs Label-Layout
(`answer_grid_label_model`). `layout_geometry_scene` ist der eine Szenenaufbau
samt Label-Layout für Renderer, Validator (AN019) und Tests. Alle Maße kommen aus
dem `GeometryFrame` (`answer_grid_frame.py`): gezeichnet wird bis an den Rand
des Randbereichs, Ticks gibt es nur auf der Hauptfläche.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .answer_grid_axis import (
    _clamp_axis_origin,
    _render_axis_ticks_and_labels,
    _resolve_axis_name,
)
from .answer_grid_axis_names import _render_axis_arrowheads_and_names
from .answer_grid_coords import to_svg
from .answer_grid_entries import (
    _parse_functions,
    _parse_pairs,
    _parse_points,
    _parse_sequence,
)
from .answer_grid_frame import resolve_coordinate_system
from .answer_grid_function_eval import _sample_function_points
from .answer_grid_label_layout import LabelPlacement, layout_labels
from .answer_grid_label_model import (
    TIER_AXIS,
    TIER_LINE,
    LabelSpec,
    Obstacle,
    emit_label,
    point_cross_obstacles,
    polyline_obstacles,
    stroke_pad,
)
from .answer_grid_circles import _render_circles_section
from .answer_grid_shapes import _render_polygons_section
from .answer_grid_svg_style import _svg_fill_style_attr, _svg_stroke_style_attr

_CROSS_HALF = 0.18


def _point_cross_svg(px, py, mode, stroke_style):
    """Die beiden Linien eines Punktkreuzes (unverändertes Markup)."""
    h = _CROSS_HALF
    return [
        f"<line class='grid-point grid-mode-{mode}'{stroke_style} x1='{px - h:.4f}' y1='{py - h:.4f}' x2='{px + h:.4f}' y2='{py + h:.4f}' />",
        f"<line class='grid-point grid-mode-{mode}'{stroke_style} x1='{px - h:.4f}' y1='{py + h:.4f}' x2='{px + h:.4f}' y2='{py - h:.4f}' />",
    ]


def _point_label(label, color, mode, px, py):
    """LabelSpec eines Punktlabels (Standard: rechts oberhalb des Kreuzes)."""
    return LabelSpec(
        text=label, css_class=f"grid-point-label grid-mode-{mode}", x=px + 0.24, y=py - 0.24,
        kind="point", anchor=(px, py), style_attr=_svg_fill_style_attr(color),
    )


def _render_points_section(raw_entries, coord_system, frame, include_solutions):
    """Section-Renderer für `points`: liefert `(shapes, label_specs, obstacles)`; Punkte im Randbereich werden gezeichnet."""
    entries = _parse_points(raw_entries, coord_system, include_solutions)
    shapes, labels, obstacles = [], [], []
    for math_x, math_y, label, color, thickness, mode in entries:
        if not frame.is_visible(math_x, math_y):
            continue
        px, py = to_svg(math_x, math_y, frame.height_units)
        shapes.extend(_point_cross_svg(px, py, mode, _svg_stroke_style_attr(color, thickness)))
        obstacles.extend(point_cross_obstacles(px, py, thickness or 1.15))
        if label:
            labels.append(_point_label(label, color, mode, px, py))
    return shapes, labels, obstacles


def _render_sequence_section(raw_entries, coord_system, frame, include_solutions):
    """Section-Renderer für `sequence`: Verbindungs-Polylinie und Punkt-Kreuze sind beide "Shapes" dieser Sektion."""
    entries = _parse_sequence(raw_entries, coord_system, include_solutions)
    rows = frame.height_units
    visible = [(*to_svg(x, y, rows), *rest) for x, y, *rest in entries if frame.is_visible(x, y)]

    shapes, labels, obstacles = [], [], []
    if len(visible) >= 2:
        seq_color, seq_thickness, seq_mode = visible[0][3], visible[0][4], visible[0][5]
        ordered = sorted(visible, key=lambda item: item[0])
        points_attr = " ".join(f"{x:.4f},{y:.4f}" for x, y, _label, _color, _thickness, _mode in ordered)
        stroke_style = _svg_stroke_style_attr(seq_color, seq_thickness)
        shapes.append(
            f"<polyline class='grid-sequence-line grid-mode-{seq_mode}'{stroke_style} points='{points_attr}' />"
        )
        obstacles.extend(polyline_obstacles([(x, y) for x, y, *_rest in ordered], TIER_LINE, stroke_pad(seq_thickness or 1.5)))

    for px, py, label, color, thickness, mode in visible:
        shapes.extend(_point_cross_svg(px, py, mode, _svg_stroke_style_attr(color, thickness)))
        obstacles.extend(point_cross_obstacles(px, py, thickness or 1.15))
        if label:
            labels.append(_point_label(label, color, mode, px, py))
    return shapes, labels, obstacles


def _render_pairs_section(raw_entries, coord_system, frame, include_solutions):
    """Section-Renderer für `pairs` (Standard-Label: rechts oberhalb der Streckenmitte)."""
    entries = _parse_pairs(raw_entries, coord_system, include_solutions)
    rows = frame.height_units
    shapes, labels, obstacles = [], [], []
    for math_x1, math_y1, math_x2, math_y2, label, color, thickness, mode, line_style in entries:
        gx1, gy1 = to_svg(math_x1, math_y1, rows)
        gx2, gy2 = to_svg(math_x2, math_y2, rows)
        stroke_style = _svg_stroke_style_attr(color, thickness)
        shapes.append(
            f"<line class='grid-segment grid-segment-{line_style} grid-mode-{mode}'{stroke_style} x1='{gx1:.4f}' y1='{gy1:.4f}' x2='{gx2:.4f}' y2='{gy2:.4f}' />"
        )
        mid_x, mid_y = (gx1 + gx2) / 2, (gy1 + gy2) / 2
        obstacles.append(Obstacle(TIER_LINE, "segment", (gx1, gy1, gx2, gy2), stroke_pad(thickness or 2.5), ("segment", (mid_x, mid_y))))
        if label:
            labels.append(LabelSpec(
                text=label, css_class=f"grid-segment-label grid-mode-{mode}", x=mid_x + 0.16, y=mid_y - 0.16,
                kind="segment", anchor=(mid_x, mid_y), style_attr=_svg_fill_style_attr(color),
            ))
    return shapes, labels, obstacles


def _render_functions_section(raw_entries, coord_system, frame, include_solutions):
    """Section-Renderer für `functions`; der Graph läuft bis in den Randbereich, Hindernisse nutzen exakt die gezeichneten Samples."""
    entries = _parse_functions(raw_entries, coord_system.axis_active, include_solutions)
    shapes, labels, obstacles = [], [], []
    for expr, x_min, x_max, label, color, thickness, mode in entries:
        samples = _sample_function_points(expr, x_min, x_max, coord_system, frame)
        if len(samples) < 2:
            continue
        poly_points = [to_svg(x, y, frame.height_units) for x, y in samples]
        points_attr = " ".join(f"{x:.4f},{y:.4f}" for x, y in poly_points)
        stroke_style = _svg_stroke_style_attr(color, thickness)
        shapes.append(
            f"<polyline class='grid-function-line grid-mode-{mode}'{stroke_style} points='{points_attr}' />"
        )
        obstacles.extend(polyline_obstacles(poly_points, TIER_LINE, stroke_pad(thickness or 1.1), owner=("function", poly_points[-1])))
        if label:
            end_x, end_y = poly_points[-1]
            labels.append(LabelSpec(
                text=label, css_class=f"grid-function-label grid-mode-{mode}", x=end_x + 0.16, y=end_y - 0.16,
                kind="function", anchor=(end_x, end_y), style_attr=_svg_fill_style_attr(color),
            ))
    return shapes, labels, obstacles


_SECTION_RENDERERS = {
    "points": _render_points_section,
    "sequence": _render_sequence_section,
    "pairs": _render_pairs_section,
    "polygons": _render_polygons_section,
    "circles": _render_circles_section,
    "functions": _render_functions_section,
}
"""Dispatch-Tabelle Sektionsname -> `(raw_entries, coord_system, frame, include_solutions) -> (shapes, label_specs, obstacles)`.

`build_geometry_scene` iteriert `payload.items()` in YAML-Dokumentreihenfolge
und schlägt hier nach, statt die Sektionen in einer im Code fest verdrahteten
Reihenfolge zu rendern -- die Zeichen-Reihenfolge im Ergebnis-SVG folgt
dadurch der Reihenfolge, in der die Sektionen im `:::geometry`-Payload
tatsächlich stehen. Dieselbe Reihenfolge bestimmt die Label- und
Hindernisreihenfolge des (deterministischen) Layouts.
"""


@dataclass
class GeometryScene:
    """Alle Bestandteile eines Geometry-Overlays vor dem Label-Layout."""

    bottom: list[str] = field(default_factory=list)
    shapes: list[str] = field(default_factory=list)
    labels: list[LabelSpec] = field(default_factory=list)
    obstacles: list[Obstacle] = field(default_factory=list)


def _add_axes(scene, options, coord_system, frame):
    """Achsenkreuz, Pfeilspitzen, Achsennamen und Ticks in die Szene legen.

    Die Achsen laufen über den sichtbaren Bereich (`frame.visible_extent`,
    inklusive Randbereich); ihre Lage klemmt `_clamp_axis_origin` auf die
    Hauptfläche, und Ticks samt Tick-Zahlen gibt es nur dort.
    """
    cols, rows = frame.width_units, frame.height_units
    axis_ox, axis_oy = _clamp_axis_origin(coord_system.origin[0], coord_system.origin[1], cols, rows)
    logical_ox, logical_oy = coord_system.origin
    axis_label_x = _resolve_axis_name(options, "axis_label_x", aliases=("x_label", "axis_x_label"), default="x")
    axis_label_y = _resolve_axis_name(options, "axis_label_y", aliases=("y_label", "axis_y_label"), default="y")
    left, bottom, right, top = frame.visible_extent
    _x, svg_axis_y = to_svg(axis_ox, axis_oy, rows)
    _x, svg_top = to_svg(axis_ox, top, rows)
    _x, svg_bottom = to_svg(axis_ox, bottom, rows)
    scene.bottom.append(f"<line class='grid-axis' x1='{left:.4f}' y1='{svg_axis_y:.4f}' x2='{right:.4f}' y2='{svg_axis_y:.4f}' />")
    scene.bottom.append(f"<line class='grid-axis' x1='{axis_ox:.4f}' y1='{svg_top:.4f}' x2='{axis_ox:.4f}' y2='{svg_bottom:.4f}' />")
    axis_pad = stroke_pad(0.9)
    scene.obstacles.append(Obstacle(TIER_AXIS, "segment", (left, svg_axis_y, right, svg_axis_y), axis_pad))
    scene.obstacles.append(Obstacle(TIER_AXIS, "segment", (axis_ox, svg_top, axis_ox, svg_bottom), axis_pad))
    for part_shapes, part_labels, part_obstacles in (
        _render_axis_arrowheads_and_names(axis_ox, axis_oy, frame, axis_label_x, axis_label_y),
        _render_axis_ticks_and_labels(
            logical_ox, logical_oy, axis_ox, axis_oy, cols, rows, coord_system.step_x, coord_system.step_y
        ),
    ):
        scene.bottom.extend(part_shapes)
        scene.labels.extend(part_labels)
        scene.obstacles.extend(part_obstacles)


def build_geometry_scene(options, payload, frame, include_solutions):
    """Baut Achse, Objekte, Label-Beschreibungen und Hindernisse; ``None`` im Achsenzustand `"broken"`.

    Im Achsenzustand `"broken"` (`axis=true` mit ungültigem/fehlendem
    `origin`) wird **sofort** ``None`` geliefert, bevor irgendein
    `_parse_*`/Section-Dispatch läuft -- kein stiller Rückfall auf
    Rasterkoordinaten; der Validator meldet diesen Zustand separat (`OP005`).
    Label-Reihenfolge: Achsennamen, Tick-Zahlen, dann die Sektionen in
    YAML-Reihenfolge (wie bisher die Ausgabereihenfolge).
    """
    coord_system = resolve_coordinate_system(options)
    if coord_system is None:
        return None

    scene = GeometryScene()
    if coord_system.axis_active:
        _add_axes(scene, options, coord_system, frame)

    if isinstance(payload, dict):
        for section, raw_entries in payload.items():
            renderer = _SECTION_RENDERERS.get(section)
            if renderer is None:
                continue
            section_shapes, section_labels, section_obstacles = renderer(raw_entries, coord_system, frame, include_solutions)
            scene.shapes.extend(section_shapes)
            scene.labels.extend(section_labels)
            scene.obstacles.extend(section_obstacles)
    return scene


def layout_geometry_scene(options, payload, frame, include_solutions) -> tuple[GeometryScene, LabelPlacement] | None:
    """Szene bauen und ihre Labels platzieren -- der eine Weg für Renderer, Validator (AN019) und Tests.

    Die Label-Zone ist die Hauptfläche plus `frame.zone_units` (Randbereich und
    Bleed); `labels=fixed` lässt alle Labels an ihrer Standardposition.
    ``None`` im Achsenzustand `"broken"` (siehe `build_geometry_scene`).
    """
    scene = build_geometry_scene(options, payload, frame, include_solutions)
    if scene is None:
        return None
    placement = layout_labels(
        scene.labels, scene.obstacles, frame.width_units, frame.height_units, frame.zone_units, options.get("labels")
    )
    return scene, placement


def _render_grid_primitives_svg(options, payload, frame, include_solutions):
    """Rendert optionale geometrische Primitive innerhalb des Rasters als SVG.

    Z-Reihenfolge: (1) Achse ganz unten (nur im Achsenzustand `"active"`,
    siehe `_resolve_axis_state`), (2) alle übrigen Geometry-Objekte in
    exakt der Reihenfolge ihres Auftretens im YAML-Payload, (3) alle Labels
    (inkl. Achsennamen und Tick-Zahlenwerte) ganz oben, sektionsübergreifend
    zusammengefasst. Die Label-Positionen bestimmt `layout_labels` (Block-Option
    `labels=auto|fixed`). Gibt einen leeren String zurück, wenn kein einziges
    sichtbares Element übrig bleibt, und ebenso im Achsenzustand `"broken"`.
    """
    laid_out = layout_geometry_scene(options, payload, frame, include_solutions)
    if laid_out is None:
        return ""
    scene, placement = laid_out
    label_markup = [emit_label(spec, x, y) for spec, (x, y) in zip(scene.labels, placement.positions)]

    all_markup = scene.bottom + scene.shapes + label_markup
    if not all_markup:
        return ""

    view_box, frame_style = frame.viewport()

    return (
        f"<svg class='grid-overlay' viewBox='{view_box}' preserveAspectRatio='none' aria-hidden='true' style='{frame_style}'>"
        f"{''.join(all_markup)}"
        "</svg>"
    )
