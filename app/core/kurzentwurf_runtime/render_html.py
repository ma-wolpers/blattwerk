from __future__ import annotations

from html import escape

from .activity_cell import ANT_NOTE_CLASS, activity_cell_html
from .cell_html import CELL_GAP_CLASS, render_cell_text
from .math_support import MATHJAX_INLINE_HEAD_HTML
from .model import KurzentwurfDocument, KurzentwurfPhaseBlock, KurzentwurfSegment

PHASE_SEPARATOR_LINE = "line"
PHASE_SEPARATOR_SPACE = "space"
PAGE_ORIENTATION_VERTICAL = "vertical"
PAGE_ORIENTATION_HORIZONTAL = "horizontal"

DEFAULT_BODY_FONT_SIZE_PT = 10.5
DEFAULT_PAGE_MARGIN_CM = 1.15
DEFAULT_PAGE_ORIENTATION_MODE = PAGE_ORIENTATION_VERTICAL
DEFAULT_PHASE_ROW_SEPARATOR_MODE = PHASE_SEPARATOR_LINE
DEFAULT_PHASE_ROW_SPACING_PX = 10
DEFAULT_S_MARKER_LABEL = "S:innen"
DEFAULT_ANT_MARKER_LABEL = "Antizipiert:"


def render_document_html(
    document: KurzentwurfDocument,
    *,
    column_width_percentages: tuple[float, float, float, float] = (10.0, 20.0, 60.0, 10.0),
    show_document_header: bool = False,
    body_font_size_pt: float = DEFAULT_BODY_FONT_SIZE_PT,
    page_margin_cm: float = DEFAULT_PAGE_MARGIN_CM,
    page_orientation_mode: str = DEFAULT_PAGE_ORIENTATION_MODE,
    phase_row_separator_mode: str = DEFAULT_PHASE_ROW_SEPARATOR_MODE,
    phase_row_spacing_px: int = DEFAULT_PHASE_ROW_SPACING_PX,
    s_marker_label: str = DEFAULT_S_MARKER_LABEL,
    ant_marker_label: str = DEFAULT_ANT_MARKER_LABEL,
) -> str:
    """Render validated document model into printable HTML."""

    body_font_size_pt = _sanitize_float(
        body_font_size_pt,
        default=DEFAULT_BODY_FONT_SIZE_PT,
        min_value=8.0,
        max_value=16.0,
    )
    page_margin_cm = _sanitize_float(
        page_margin_cm,
        default=DEFAULT_PAGE_MARGIN_CM,
        min_value=0.4,
        max_value=4.0,
    )
    page_orientation_mode = _normalize_page_orientation_mode(page_orientation_mode)
    phase_row_separator_mode = _normalize_phase_separator_mode(phase_row_separator_mode)
    phase_row_spacing_px = _sanitize_int(
        phase_row_spacing_px,
        default=DEFAULT_PHASE_ROW_SPACING_PX,
        min_value=0,
        max_value=40,
    )
    s_marker_label = _sanitize_marker_label(s_marker_label, default=DEFAULT_S_MARKER_LABEL)
    ant_marker_label = _sanitize_marker_label(ant_marker_label, default=DEFAULT_ANT_MARKER_LABEL)

    th_font_size_pt = body_font_size_pt + 0.5
    subtitle_font_size_pt = body_font_size_pt
    phase_main_font_size_pt = body_font_size_pt + 0.4
    phase_time_font_size_pt = max(8.0, body_font_size_pt - 0.4)
    umgebung_font_size_pt = max(8.0, body_font_size_pt - 0.2)
    header_subline_font_size_pt = max(8.5, body_font_size_pt - 0.5)
    doc_title_font_size_pt = body_font_size_pt + 6.5

    if document.phases:
        rows_html = "\n".join(
            _render_phase_rows(
                phase,
                s_marker_label=s_marker_label,
                ant_marker_label=ant_marker_label,
            )
            for phase in document.phases
        )
    else:
        # Transitional fallback for legacy row-model callers.
        rows_html = "\n".join(_render_legacy_row(row) for row in document.rows)
    phase_width, schritte_width, aktivitaeten_width, umgebung_width = column_width_percentages

    header_html = ""
    if show_document_header:
        subtitle_html = (
            f"<div class=\"subtitle\">{escape(document.subtitle)}</div>"
            if document.subtitle
            else ""
        )
        header_html = (
            f"<h1 class=\"doc-title\">{escape(document.title)}</h1>"
            f"{subtitle_html}"
        )

    page_orientation_css = "landscape" if page_orientation_mode == PAGE_ORIENTATION_HORIZONTAL else "portrait"

    return f"""<!doctype html>
<html lang=\"de\">
<head>
  <meta charset=\"utf-8\" />
  <title>{escape(document.title)}</title>
  {MATHJAX_INLINE_HEAD_HTML}
  <style>
    :root {{
      --phase-row-gap-px: {phase_row_spacing_px:d}px;
    }}

    @page {{
            size: A4 {page_orientation_css};
      margin: {page_margin_cm:.3f}cm;
    }}

    .word-note-text {{
      display: none;
    }}

    body {{
      font-family: Arial, Helvetica, sans-serif;
      font-size: {body_font_size_pt:.2f}pt;
      color: #111;
      margin: 0;
      padding: 0;
      line-height: 1.24;
    }}

    .doc-title {{
      margin: 0 0 3.2mm 0;
      font-size: {doc_title_font_size_pt:.2f}pt;
      font-weight: 700;
      text-align: left;
    }}

    .subtitle {{
      margin: 0 0 4.6mm 0;
      font-size: {subtitle_font_size_pt:.2f}pt;
      color: #333;
    }}

    table.kurzentwurf {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      border: 2px solid #000;
    }}

    table.kurzentwurf col.phase {{ width: {phase_width:.4f}%; }}
    table.kurzentwurf col.schritte {{ width: {schritte_width:.4f}%; }}
    table.kurzentwurf col.aktivitaeten {{ width: {aktivitaeten_width:.4f}%; }}
    table.kurzentwurf col.umgebung {{ width: {umgebung_width:.4f}%; }}

    table.kurzentwurf th,
    table.kurzentwurf td {{
      border: 1px solid #222;
      padding: 6px 8px;
      vertical-align: top;
      hyphens: auto;
      overflow-wrap: anywhere;
    }}

    table.kurzentwurf th {{
      text-align: center;
      background: #fff;
      font-weight: 700;
      font-size: {th_font_size_pt:.2f}pt;
    }}

    table.kurzentwurf thead {{
      display: table-row-group;
    }}

        table.kurzentwurf tbody tr {{
            break-inside: auto;
            page-break-inside: auto;
        }}

        table.kurzentwurf tbody td {{
            break-inside: auto;
            page-break-inside: auto;
        }}

    th.lernumgebung-head {{
      line-height: 1.2;
    }}

    .header-subline {{
      display: inline-block;
      margin-top: 2px;
      font-weight: 400;
      font-size: {header_subline_font_size_pt:.2f}pt;
      line-height: 1.15;
    }}

    table.kurzentwurf.separator-space tr.phase-segment-row-nonlast td.segment-cell-single-row {{
      border-bottom: none;
    }}

    table.kurzentwurf.separator-space tr.phase-segment-row-followup td.segment-cell {{
      border-top: none;
      padding-top: calc(6px + var(--phase-row-gap-px));
    }}

    td.phase-cell {{
      background: #fff;
    }}

    .phase-main {{
      font-weight: 700;
      font-size: {phase_main_font_size_pt:.2f}pt;
      line-height: 1.2;
      margin-bottom: 2px;
      overflow-wrap: break-word;
    }}

    .phase-time {{
      font-size: {phase_time_font_size_pt:.2f}pt;
      font-style: normal;
      line-height: 1.2;
    }}

    td.umgebung-cell {{
      font-size: {umgebung_font_size_pt:.2f}pt;
    }}

    .cell-content {{
      line-height: 1.26;
    }}

    .cell-paragraph {{
      margin: 0 0 3px 0;
    }}

    .cell-paragraph:last-child {{
      margin-bottom: 0;
    }}

    /* Leerzeile in der Quelle = eine sichtbare Leerzeile (Zeilenhöhe von .cell-content). */
    .{CELL_GAP_CLASS} {{
      margin-top: 1.26em;
    }}

    .{ANT_NOTE_CLASS} {{
      color: #666;
    }}

    .cell-list {{
      margin: 0 0 4px 17px;
      padding: 0;
    }}

    .cell-list:last-child {{
      margin-bottom: 0;
    }}

    .cell-list li {{
      margin: 0 0 2px 0;
      padding: 0;
    }}

    td.full-row-cell {{
      font-style: italic;
      color: #444;
    }}

    mark {{
      background: #fff36d;
      padding: 0 0.06em;
    }}

    strong {{
      font-weight: 700;
    }}

    em {{
      font-style: italic;
    }}

    u {{
      text-decoration: underline;
    }}

    del {{
      text-decoration: line-through;
    }}

    sub {{
      vertical-align: sub;
      font-size: smaller;
    }}

    sup {{
      vertical-align: super;
      font-size: smaller;
    }}

    code {{
      font-family: "Consolas", "Courier New", monospace;
      background: #f0f0f0;
      padding: 0.05em 0.3em;
      border-radius: 3px;
    }}

    pre {{
      font-family: "Consolas", "Courier New", monospace;
      background: #f0f0f0;
      padding: 0.5em 0.7em;
      border-radius: 4px;
      overflow-x: auto;
    }}

    pre code {{
      background: none;
      padding: 0;
    }}

    .bw-spoiler {{
      color: inherit;
      background-color: currentColor;
      border-radius: 2px;
      padding: 0 0.15em;
    }}
  </style>
</head>
<body>
    {header_html}

    <table class="kurzentwurf separator-{phase_row_separator_mode}">
        <colgroup>
            <col class="phase" />
            <col class="schritte" />
            <col class="aktivitaeten" />
            <col class="umgebung" />
        </colgroup>
        <thead>
            <tr>
                <th rowspan="2">Phase</th>
                <th colspan="2">Lernweg</th>
                <th rowspan="2" class="lernumgebung-head">Lern&shy;umgebung<br><span class="header-subline">Sozialform<br>Medien<br>Materialien (in Referenz zum Anhang)</span></th>
            </tr>
            <tr>
                <th>Inhaltliche Lernschritte</th>
                <th>Lernaktivitäten<br><span class="header-subline">(Kompetenzförderung)</span></th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
</body>
</html>
"""


def _render_phase_rows(
    phase: KurzentwurfPhaseBlock,
    *,
    s_marker_label: str,
    ant_marker_label: str,
) -> str:
    segments = list(phase.segments)
    if not segments:
        return ""

    phase_rowspan = len(segments)
    phase_time_html = ""
    time_label = _format_phase_time(phase.start_minutes, phase.end_minutes)
    if time_label:
        phase_time_html = f"<div class=\"phase-time\">({escape(time_label)})</div>"

    full_row_indices = {i for i, s in enumerate(segments) if s.full_row}

    # Jede Map liefert pro Gruppenanfang (rowspan, fertiges Zellen-HTML).
    schritte_map = _build_group_map(
        segments,
        text_getter=lambda item: render_cell_text(item.schritte),
        inherit_getter=lambda item: item.inherit_schritte,
        full_row_indices=full_row_indices,
    )
    aktivitaeten_map = _build_group_map(
        segments,
        text_getter=lambda item: activity_cell_html(
            item.activities,
            s_marker_label=s_marker_label,
            ant_marker_label=ant_marker_label,
        ),
        inherit_getter=lambda item: item.inherit_aktivitaeten,
        full_row_indices=full_row_indices,
    )
    umgebung_map = _build_group_map(
        segments,
        text_getter=lambda item: render_cell_text(item.umgebung),
        inherit_getter=lambda item: item.inherit_umgebung,
        full_row_indices=full_row_indices,
    )

    rows: list[str] = []
    for index in range(len(segments)):
        row_classes = ["phase-segment-row"]
        if index > 0:
            row_classes.append("phase-segment-row-followup")
        if index < len(segments) - 1:
            row_classes.append("phase-segment-row-nonlast")

        if index in full_row_indices:
            text = render_cell_text(segments[index].schritte or "")
            rows.append(
                f"<tr class=\"{' '.join(row_classes)} full-row-segment\">"
                "<td colspan=\"3\" class=\"full-row-cell\"><div class=\"cell-content\">"
                f"{text}"
                "</div></td>"
                "</tr>"
            )
            continue

        cells: list[str] = []
        if index == 0:
            cells.append(
                "<td class=\"phase-cell\" rowspan=\""
                f"{phase_rowspan}"
                "\"><div class=\"phase-main\">"
                f"{escape(phase.display_phase)}"
                "</div>"
                f"{phase_time_html}</td>"
            )

        schritte_group = schritte_map.get(index)
        if schritte_group is not None:
            rowspan, text = schritte_group
            cells.append(
                "<td class=\""
                f"{_segment_cell_classes(rowspan, 'schritte-cell')}"
                "\" rowspan=\""
                f"{rowspan}"
                "\"><div class=\"cell-content\">"
                f"{text}"
                "</div></td>"
            )

        aktivitaeten_group = aktivitaeten_map.get(index)
        if aktivitaeten_group is not None:
            rowspan, text = aktivitaeten_group
            cells.append(
                "<td class=\""
                f"{_segment_cell_classes(rowspan, 'aktivitaeten-cell')}"
                "\" rowspan=\""
                f"{rowspan}"
                "\"><div class=\"cell-content\">"
                f"{text}"
                "</div></td>"
            )

        umgebung_group = umgebung_map.get(index)
        if umgebung_group is not None:
            rowspan, text = umgebung_group
            cells.append(
                "<td class=\""
                f"{_segment_cell_classes(rowspan, 'umgebung-cell')}"
                "\" rowspan=\""
                f"{rowspan}"
                "\"><div class=\"cell-content\">"
                f"{text}"
                "</div></td>"
            )

        rows.append(f"<tr class=\"{' '.join(row_classes)}\">" + "".join(cells) + "</tr>")

    return "\n".join(rows)


def _build_group_map(
    segments: list[KurzentwurfSegment],
    *,
    text_getter,
    inherit_getter,
    full_row_indices: set[int] | None = None,
) -> dict[int, tuple[int, str]]:
    if not segments:
        return {}

    breaks = full_row_indices or set()
    groups: dict[int, tuple[int, str]] = {}
    start_index = 0
    for index in range(1, len(segments)):
        if not inherit_getter(segments[index]) or index in breaks or (index - 1) in breaks:
            groups[start_index] = (index - start_index, text_getter(segments[start_index]))
            start_index = index

    groups[start_index] = (len(segments) - start_index, text_getter(segments[start_index]))
    return groups


def _segment_cell_classes(rowspan: int, *extra_classes: str) -> str:
    classes = ["segment-cell", *extra_classes]
    if int(rowspan) <= 1:
        classes.append("segment-cell-single-row")
    return " ".join(classes)


def _sanitize_float(
    value: object,
    *,
    default: float,
    min_value: float,
    max_value: float,
) -> float:
    try:
        numeric = float(value)
    except Exception:
        numeric = float(default)
    return max(min_value, min(max_value, numeric))


def _sanitize_int(
    value: object,
    *,
    default: int,
    min_value: int,
    max_value: int,
) -> int:
    try:
        numeric = int(round(float(value)))
    except Exception:
        numeric = int(default)
    return max(min_value, min(max_value, numeric))


def _normalize_phase_separator_mode(value: object) -> str:
    text = str(value or "").strip().lower()
    if text == PHASE_SEPARATOR_SPACE:
        return PHASE_SEPARATOR_SPACE
    return PHASE_SEPARATOR_LINE


def _normalize_page_orientation_mode(value: object) -> str:
    text = str(value or "").strip().lower()
    if text == PAGE_ORIENTATION_HORIZONTAL:
        return PAGE_ORIENTATION_HORIZONTAL
    return PAGE_ORIENTATION_VERTICAL


def _sanitize_marker_label(value: object, *, default: str) -> str:
        text = str(value or "").strip()
        return text if text else default


def _format_phase_time(start_minutes: int | None, end_minutes: int | None) -> str:
    if start_minutes is None and end_minutes is None:
        return ""
    if start_minutes is not None and end_minutes is not None:
        return f"{_minutes_to_hhmm(start_minutes)}-{_minutes_to_hhmm(end_minutes)}"
    if start_minutes is not None:
        return _minutes_to_hhmm(start_minutes)
    return _minutes_to_hhmm(end_minutes or 0)


def _minutes_to_hhmm(total_minutes: int) -> str:
    minutes = int(total_minutes) % (24 * 60)
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def _render_legacy_row(row) -> str:
    phase_time_html = ""
    if getattr(row, "time", ""):
        phase_time_html = f"<div class=\"phase-time\">({escape(row.time)})</div>"

    return f"""
<tr>
  <td class=\"phase-cell\"><div class=\"phase-main\">{escape(row.display_phase)}</div>{phase_time_html}</td>
  <td><div class=\"cell-content\">{render_cell_text(row.schritte)}</div></td>
  <td><div class=\"cell-content\">{render_cell_text(row.aktivitaeten)}</div></td>
  <td class=\"umgebung-cell\"><div class=\"cell-content\">{render_cell_text(row.umgebung)}</div></td>
</tr>
""".strip()


