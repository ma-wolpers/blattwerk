"""Erwartungshorizont einer Klausur als HTML/PDF (Plan Phase 6).

Datenquellen ausschließlich: `solution_items` (Erwartungen und `(xP)`),
`points_model` (Punktzahlen), `exam_analysis` (AFB) und `resolve_aid_split`
(Teile). Es gibt **keinen Aufgabentext**, nur die nummerierten Erwartungen.

Fehlerverhalten:

* Blockierende Diagnosen (PK001/PK002/PK004/PK005, SL008 und alle anderen
  Fehler) → kein Export (`ValueError` mit Zusammenfassung).
* Ziel ohne jede `(P)`-Angabe → Export mit leerer Punktspalte, SL005.
* Teilweise annotiert (SL006) → Export mit der Validator-Warnung.
* (Teil-)Aufgabe ohne nummerierte Erwartung → Zeile „keine Erwartung
  hinterlegt“, SL007.
* AFB unvollständig → AFB-Tabelle zeigt „unvollständig“, keine Prozente.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import markdown

from .blatt_kern_io_pdf import write_pdf_from_html
from .blatt_kern_shared import parse_blocks, split_front_matter
from .blatt_validator import has_blocking_diagnostics, inspect_markdown_text, summarize_blocking_diagnostics
from .blatt_validator_types import BuildDiagnostic
from .document_semantics import resolve_aid_split
from .exam_analysis import AFB_LEVELS, analyze_exam
from .export_path_guardrails import validate_export_output_path
from .frontmatter import content_after_frontmatter
from .math_span_protection import convert_markdown_with_math
from .points_model import build_points_model, format_points, subtask_effective
from .solution_items import collect_solution_targets
from .student_header import HEADER_DATE_KIND, InvalidHeaderValue, resolve_header_value

_REGION = "exam:expectation-horizon"
_STYLE = """
@page { size: A4 portrait; margin: 1.8cm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10.5pt; color: #111; }
h1 { font-size: 16pt; margin: 0 0 0.2em; } h2 { font-size: 13pt; margin: 1em 0 0.3em; }
h3 { font-size: 11.5pt; margin: 0.9em 0 0.3em; } .meta { color: #444; margin: 0 0 0.8em; }
table { border-collapse: collapse; width: 100%; margin: 0.2em 0 0.6em; }
th, td { border: 1px solid #999; padding: 0.25em 0.45em; vertical-align: top; text-align: left; }
th { background: #eee; } td.num, th.num { width: 2.4em; text-align: center; }
td.pts, th.pts { width: 4.5em; text-align: center; } .target-row td { background: #f6f6f6; font-weight: 600; }
.missing { color: #a33; font-style: italic; } .sum { font-weight: 600; margin: 0.2em 0 0.8em; }
"""


def _inline(text: str) -> str:
    html = convert_markdown_with_math(markdown.Markdown(), text, lambda value: value).strip()
    if html.startswith("<p>") and html.endswith("</p>") and html.count("<p>") == 1:
        html = html[3:-4]
    return html


def _diag(code: str, message: str) -> BuildDiagnostic:
    return BuildDiagnostic(code=code, message=message, region_id=_REGION, anchor=message)


def build_expectation_horizon_html(text: str) -> tuple[str, list[BuildDiagnostic]]:
    """Erzeugt das HTML des Erwartungshorizonts samt eigener Hinweise (SL005/SL007)."""
    meta, _rest = split_front_matter(text)
    content, _line = content_after_frontmatter(text)
    blocks = parse_blocks(content.strip())
    units = build_points_model(blocks)
    targets, _issues = collect_solution_targets(blocks)
    split = resolve_aid_split(blocks, "exam")
    analysis = analyze_exam(blocks, "exam")
    diagnostics: list[BuildDiagnostic] = []
    targets_by_key = {(t.unit_index, t.subtask_position): t for t in targets}

    body = [f"<h1>Erwartungshorizont</h1>", _meta_line(meta)]
    current_part = None
    for unit_index, unit in enumerate(units):
        part = None if split is None else ("A" if unit.block_index < split.index else "B")
        if part != current_part and part is not None:
            if current_part is not None:
                body.append(_part_sum(analysis.parts[0]))
            body.append(f"<h2>{'Teil A – hilfsmittelfrei' if part == 'A' else 'Teil B – mit Hilfsmitteln'}</h2>")
            current_part = part
        body.append(f"<h3>Aufgabe {unit.number} ({format_points(unit.effective)} P)</h3>")
        body.append("<table><tr><th class='num'>Nr.</th><th>Erwartung</th><th class='pts'>max. P.</th><th class='pts'>erreicht</th></tr>")
        keys = []
        if not unit.subtasks or (unit_index, None) in targets_by_key:
            keys.append((unit_index, None))  # Aufgabenebene (bei Teilaufgaben nur, wenn dort Lösungen stehen)
        keys.extend((unit_index, position) for position in range(len(unit.subtasks)))
        for key in keys:
            body.extend(_target_rows(unit, key, targets_by_key.get(key), diagnostics))
        body.append("</table>")
    if split is not None and analysis.parts:
        body.append(_part_sum(analysis.parts[1]))
    body.append(_afb_table(analysis))
    title = escape(str(meta.get("Titel") or "Erwartungshorizont")) if isinstance(meta, dict) else "Erwartungshorizont"
    html = (
        "<!DOCTYPE html>\n<html lang=\"de\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>Erwartungshorizont – {title}</title>\n"
        "<script>window.MathJax={tex:{inlineMath:[['$','$']],displayMath:[['$$','$$']]},svg:{fontCache:'none'}};</script>\n"
        "<script defer src=\"https://cdn.jsdelivr.net/npm/mathjax@4/tex-svg.js\"></script>\n"
        f"<style>{_STYLE}</style>\n</head>\n<body>\n" + "\n".join(body) + "\n</body>\n</html>\n"
    )
    return html, diagnostics


def _meta_line(meta) -> str:
    """Kopfzeile des Erwartungshorizonts: Titel · Fach · Thema · Datum · Dauer.

    `Datum` folgt denselben Typregeln wie die Schülerkopfzeile
    (`student_header.resolve_header_value`): ISO-Datum → `TT.MM.JJJJ`,
    Platzhalter und ungültige Typen entfallen.
    """
    if not isinstance(meta, dict):
        return ""
    parts = []
    for key in ("Titel", "Fach", "Thema", "Datum", "Dauer"):
        if key == "Datum":
            try:
                value = resolve_header_value(HEADER_DATE_KIND, meta.get(key))
            except InvalidHeaderValue:
                value = None
        else:
            value = str(meta.get(key)).strip() if meta.get(key) else None
        if value:
            parts.append(value)
    return f"<p class='meta'>{escape(' · '.join(parts))}</p>" if parts else ""


def _target_rows(unit, key, target, diagnostics) -> list[str]:
    _unit_index, position = key
    if position is None:
        label, expected = f"Aufgabe {unit.number}", unit.effective
    else:
        sub = unit.subtasks[position]
        label = f"Aufgabe {unit.number}{sub.letter or ''}"
        expected = subtask_effective(unit, sub)
    rows = []
    if position is not None:
        rows.append(f"<tr class='target-row'><td colspan='4'>{escape(label)} ({format_points(expected)} P)</td></tr>")
    if target is None or not target.items:
        diagnostics.append(_diag("SL007", f"Erwartungshorizont: {label} hat keine nummerierte Erwartung."))
        rows.append("<tr><td class='num'></td><td class='missing'>keine Erwartung hinterlegt</td><td class='pts'></td><td class='pts'></td></tr>")
        return rows
    if all(item.points is None for item in target.items):
        diagnostics.append(_diag("SL005", f"Erwartungshorizont: {label} hat keine Teilpunkte `(xP)`."))
    for number, item in enumerate(target.items, start=1):
        points = _item_points_text(item)
        rows.append(f"<tr><td class='num'>{number}</td><td>{_inline(item.text)}</td><td class='pts'>{points}</td><td class='pts'></td></tr>")
    return rows


def _item_points_text(item) -> str:
    """Punktspalte eines Erwartungspunkts: `2` bei `(2P)`, `1/3` bei Teilpunkten `(1/3P)`.

    Teilpunkte alternativer Lösungswege bleiben als Bruch sichtbar, damit
    die Korrektur erkennt, dass die Zeilen nicht aufsummiert werden.
    """
    if item.points is None:
        return ""
    if item.of_total is not None:
        return f"{format_points(item.points)}/{format_points(item.of_total)}"
    return format_points(item.points)


def _part_sum(part) -> str:
    return f"<p class='sum'>Summe {escape(part.label)}: {format_points(part.points)} P</p>"


def _afb_table(analysis) -> str:
    rows = ["<h2>Anforderungsbereiche</h2>", "<table><tr><th></th><th>Punkte</th>"]
    rows[-1] += "".join(f"<th>AFB {'I' * level}</th>" for level in AFB_LEVELS) + "</tr>"
    for part in (analysis.parts + [analysis.total]) if analysis.parts else [analysis.total]:
        cells = []
        for level in AFB_LEVELS:
            share = analysis.percent(part.afb_points[level])
            cells.append(f"{format_points(part.afb_points[level])} P" + (f" ({format_points(share)} %)" if share is not None else ""))
        rows.append(f"<tr><td>{escape(part.label)}</td><td>{format_points(part.points)} P</td>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    rows.append("</table>")
    if not analysis.total.complete:
        rows.append(f"<p class='missing'>unvollständig: {escape('; '.join(dict.fromkeys(analysis.total.reasons)))}</p>")
    elif analysis.total.points <= 0:
        rows.append("<p class='missing'>Keine Punkte vergeben.</p>")
    return "\n".join(rows)


def build_expectation_horizon(input_path, output_path, *, diagnostics_out: list | None = None) -> Path:
    """Exportiert den Erwartungshorizont als `.html` oder `.pdf` (Endung von `output_path`).

    Raises:
        ValueError: bei blockierenden Diagnosen (z. B. Punktfehlern).
    """
    text = Path(input_path).read_text(encoding="utf-8")
    inspected = inspect_markdown_text(text, document_type="exam")
    if has_blocking_diagnostics(inspected.diagnostics):
        raise ValueError(summarize_blocking_diagnostics(inspected.diagnostics))
    html, diagnostics = build_expectation_horizon_html(text)
    if diagnostics_out is not None:
        diagnostics_out.extend(diagnostics)
    target = validate_export_output_path(output_path, allowed_suffixes={".pdf", ".html"})
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.suffix.lower() == ".html":
        target.write_text(html, encoding="utf-8")
        return target
    return Path(write_pdf_from_html(html, target))
