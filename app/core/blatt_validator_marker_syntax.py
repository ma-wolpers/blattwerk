"""Zeilenbasierte `:::`-Marker-Syntaxprüfung und Arbeitsblatt/Lösung-Paarungscheck.

`_collect_block_marker_syntax_diagnostics` validiert die reine Block-Syntax
(offene/geschlossene `:::`-Marker, Abschnittstrenner, Vertikalabstands- und
Folien-Chrome-Marker) direkt auf den Quellzeilen, bevor überhaupt in
strukturierte Blöcke geparst wird. Die Zeilenrollen liefert `scan_block_lines`
(`block_line_scan.py`), dieselbe Zustandsmaschine wie im Editor.
"""

from __future__ import annotations

from .answer_line_markers import parse_answer_line_visibility
from .blatt_validator_patterns import (
    _VALID_SECTION_MARK_PATTERN,
    _VALID_SLIDE_CHROME_OFF_PATTERN,
    _VALID_VSPACER_MARK_PATTERN,
)
from .blatt_validator_types import BuildDiagnostic
from .block_line_scan import LineKind, scan_block_lines
from .control_markers import is_control_marker_line

_DOCUMENT_TEXT_REGION_ID = "worksheet:document-text"


def _block_type_region_id(block_type: str | None) -> str:
    """Region for marker-syntax diagnostics anchored to a known enclosing block type.

    Falls back to the document-wide bucket when no enclosing block is
    known -- these diagnostics arise exactly because the surrounding
    structure doesn't parse cleanly, so there is nothing more concrete
    available (see `docs/intern/ARCHITEKTUR.md`).
    """

    if block_type is None:
        return _DOCUMENT_TEXT_REGION_ID
    return f"worksheet:block-type:{block_type}"


def _collect_block_marker_syntax_diagnostics(content_text, base_line=1):
    """Validiert die `:::`-Marker-Syntax direkt auf den Quellzeilen.

    Die Zeilenrollen kommen aus `scan_block_lines` (dieselben Regeln wie der
    Parser); hier wird nur noch je Rolle die passende Diagnose gebaut:
    `BL002` (`:::` mit Text dahinter), `BL003` (`:::` ohne offenen Block),
    `BL004` (Kopf innerhalb eines Blocks), `BL005` (Abschnittstrenner im
    Block), `BL006` (fehlerhafter Marker auf oberster Ebene) und `BL017`
    (Block am Ende nicht geschlossen).

    `base_line` verschiebt gemeldete Zeilennummern auf die Position im
    Gesamtdokument, da `content_text` bereits um das Frontmatter gekürzt ist.
    """
    diagnostics = []
    scan = scan_block_lines(content_text or "", base_line=max(1, int(base_line)), detect_frontmatter=False)

    for line in scan.lines:
        open_type = None
        if line.span is not None and line.kind is not LineKind.OPEN:
            open_type = scan.spans[line.span].block_type
        if open_type is not None and is_control_marker_line(line.stripped):
            diagnostics.append(_marker_inside_block(line, open_type))
        builder = _LINE_DIAGNOSTICS.get(line.kind)
        if builder is not None:
            diagnostics.extend(builder(line, open_type))

    for span in scan.spans:
        if span.close_line is None:
            diagnostics.append(
                BuildDiagnostic(
                    code="BL017",
                    message=(
                        f"Der Block `:::{span.block_type}` in Zeile {span.open_line} wird nicht mit "
                        "einer eigenen Zeile `:::` geschlossen. Ohne Schluss wird er als Text ausgegeben."
                    ),
                    severity="error",
                    line_number=span.open_line,
                    region_id=_block_type_region_id(span.block_type),
                    anchor=f":::{span.block_type}",
                )
            )
    return diagnostics


def _marker_inside_block(line, open_type):
    """`BL005`: Abschnittstrenner innerhalb eines offenen Blocks."""
    return BuildDiagnostic(
        code="BL005",
        message=(
            f"Ungültiger Abschnittstrenner in Zeile {line.number}: `{line.stripped}` innerhalb eines "
            "offenen `:::`-Blocks ist nicht erlaubt. Schließe zuerst den aktuellen Block mit `:::` "
            "und setze den Abschnittstrenner danach auf oberste Ebene."
        ),
        severity="error",
        line_number=line.number,
        region_id=_block_type_region_id(open_type),
        anchor=line.stripped,
    )


_TOP_LEVEL_MARKER_CHECKS = (
    ("--#", _VALID_SECTION_MARK_PATTERN, "Abschnittsmarker", "`--# <Abschnittsname>`"),
    ("-=", _VALID_VSPACER_MARK_PATTERN, "Vertikalabstands-Marker", "`-=<zahl><einheit>`, z. B. `-=0.2cm`"),
    ("--hf", _VALID_SLIDE_CHROME_OFF_PATTERN, "Folien-Chrome-Marker", "`--hf`"),
)
"""`(Präfix, gültiges Muster, Bezeichnung, Erwartung)` für `BL006`."""


def _outside_diagnostics(line, _open_type):
    """`BL006`: Marker auf oberster Ebene, deren Präfix stimmt, deren Rest aber nicht."""
    return [
        BuildDiagnostic(
            code="BL006",
            message=f"Ungültiger {label} in Zeile {line.number}: `{line.stripped}`. Erwartet: {expected}.",
            severity="error",
            line_number=line.number,
            region_id=_DOCUMENT_TEXT_REGION_ID,
            anchor=line.stripped,
        )
        for prefix, pattern, label, expected in _TOP_LEVEL_MARKER_CHECKS
        if line.stripped.startswith(prefix) and not pattern.match(line.stripped)
    ]


def _malformed_diagnostics(line, open_type):
    """`BL002`: `:::` gefolgt von Leerzeichen oder anderem Text statt eines Blocknamens."""
    return [
        BuildDiagnostic(
            code="BL002",
            message=(
                f"Ungültige Blocksyntax in Zeile {line.number}: Nach `:::` darf weder ein Leerzeichen "
                "noch weiterer Text folgen. Erlaubt sind nur `:::blocktyp` oder `:::` allein."
            ),
            severity="error",
            line_number=line.number,
            region_id=_block_type_region_id(open_type),
            anchor=line.stripped,
        )
    ]


def _stray_close_diagnostics(line, _open_type):
    """`BL003`: `:::` ohne offenen Block."""
    return [
        BuildDiagnostic(
            code="BL003",
            message=f"Ungültiger Blockabschluss in Zeile {line.number}: `:::` ohne passenden geöffneten Block.",
            severity="error",
            line_number=line.number,
            region_id=_DOCUMENT_TEXT_REGION_ID,
            anchor=line.stripped,
        )
    ]


def _nested_header_diagnostics(line, open_type):
    """`BL004`: Kopfzeile, bevor der offene Block geschlossen wurde (mit Hinweis `task` → `subtask`)."""
    shown = f":::{line.header_type} ... :::" if line.kind is LineKind.NESTED_SELF_CLOSING else f":::{line.header_type}"
    follow_block_hint = ""
    if line.kind is LineKind.NESTED_OPEN and open_type == "task" and line.header_type == "subtask":
        follow_block_hint = (
            " `subtask` ist ein Folgeblock auf oberster Ebene: zuerst `task` mit `:::` schließen, "
            "dann `:::subtask` öffnen."
        )
    return [
        BuildDiagnostic(
            code="BL004",
            message=(
                f"Ungültiger Blockwechsel in Zeile {line.number}: `{shown}` beginnt, bevor der geöffnete "
                f"Block `:::{open_type}` geschlossen wurde. Blattwerk unterstützt keine verschachtelten "
                "Blöcke; setze zuerst eine eigene Zeile mit `:::` zum Schließen des aktuellen Blocks."
                f"{follow_block_hint}"
            ),
            severity="error",
            line_number=line.number,
            region_id=_block_type_region_id(open_type),
            anchor=line.stripped,
        )
    ]


_LINE_DIAGNOSTICS = {
    LineKind.OUTSIDE: _outside_diagnostics,
    LineKind.MALFORMED: _malformed_diagnostics,
    LineKind.STRAY_CLOSE: _stray_close_diagnostics,
    LineKind.NESTED_OPEN: _nested_header_diagnostics,
    LineKind.NESTED_SELF_CLOSING: _nested_header_diagnostics,
}
"""Welche Zeilenrolle welche Diagnosen erzeugt (`BL005` gilt quer dazu, siehe oben)."""


def _has_explicit_worksheet_marker_without_solution(content):
    """Prüft, ob Inhalt `§`-Marker ohne sichtbares Lösungs-Gegenstück nutzt (für `AN010`)."""
    has_worksheet_marker = False
    has_solution_marker = False

    for raw_line in str(content or "").splitlines():
        if not raw_line.strip():
            continue

        parsed = parse_answer_line_visibility(raw_line, default_show="both")
        for segment in parsed.get("segments", []):
            segment_text = str(segment.get("text", "")).strip()
            if not segment_text:
                continue

            segment_show = segment.get("show")
            if segment_show == "worksheet":
                has_worksheet_marker = True
            elif segment_show == "solution":
                has_solution_marker = True

            if has_worksheet_marker and has_solution_marker:
                return False

    return has_worksheet_marker and not has_solution_marker
