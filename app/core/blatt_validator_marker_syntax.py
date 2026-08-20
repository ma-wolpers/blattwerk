"""Zeilenbasierte `:::`-Marker-Syntaxprüfung und Arbeitsblatt/Lösung-Paarungscheck.

`_collect_block_marker_syntax_diagnostics` validiert die reine Block-Syntax
(offene/geschlossene `:::`-Marker, Abschnittstrenner, Vertikalabstands- und
Folien-Chrome-Marker) direkt auf den Quellzeilen, bevor überhaupt in
strukturierte Blöcke geparst wird — deshalb arbeitet sie zustandsbehaftet
mit einem eigenen `block_stack` statt auf dem bereits geparsten
`blocks`-Ergebnis aufzusetzen.
"""

from __future__ import annotations

from .answer_line_markers import parse_answer_line_visibility
from .blatt_validator_patterns import (
    _BLOCK_START_PATTERN,
    _BLOCK_WHITESPACE_AFTER_MARKER_PATTERN,
    _SELF_CLOSING_BLOCK_PATTERN,
    _VALID_SECTION_MARK_PATTERN,
    _VALID_SLIDE_CHROME_OFF_PATTERN,
    _VALID_VSPACER_MARK_PATTERN,
)
from .blatt_validator_types import BuildDiagnostic


def _collect_block_marker_syntax_diagnostics(content_text, base_line=1):
    """Validiert `:::`-Marker-Syntax direkt auf den Quellzeilen.

    `base_line` verschiebt gemeldete Zeilennummern auf die Position im
    Gesamtdokument (siehe `_extract_validation_content_and_base_line`),
    da `content_text` bereits um das Frontmatter gekürzt sein kann.
    """
    diagnostics = []
    block_stack = []

    for line_no, raw_line in enumerate((content_text or "").splitlines(), start=1):
        absolute_line_no = max(1, int(base_line) + line_no - 1)
        stripped_line = raw_line.strip()

        if block_stack and (
            stripped_line in {"--", "--!", "-+", "--hf"}
            or stripped_line.startswith("--#")
            or stripped_line.startswith("-=")
        ):
            diagnostics.append(
                BuildDiagnostic(
                    code="BL005",
                    message=(
                        "Ungueltiger Abschnittstrenner in Zeile "
                        f"{absolute_line_no}: `{stripped_line}` innerhalb eines offenen "
                        "`:::`-Blocks ist nicht erlaubt. "
                        "Schliesse zuerst den aktuellen Block mit `:::` und setze den "
                        "Abschnittstrenner danach auf Top-Level."
                    ),
                    severity="error",
                    line_number=absolute_line_no,
                )
            )

        if not stripped_line.startswith(":::"):
            if not block_stack:
                if stripped_line.startswith("--#") and not _VALID_SECTION_MARK_PATTERN.match(stripped_line):
                    diagnostics.append(
                        BuildDiagnostic(
                            code="BL006",
                            message=(
                                "Ungueltiger Abschnittsmarker in Zeile "
                                f"{absolute_line_no}: `{stripped_line}`. "
                                "Erwartet: `--# <Abschnittsname>`."
                            ),
                            severity="error",
                            line_number=absolute_line_no,
                        )
                    )
                if stripped_line.startswith("-=") and not _VALID_VSPACER_MARK_PATTERN.match(stripped_line):
                    diagnostics.append(
                        BuildDiagnostic(
                            code="BL006",
                            message=(
                                "Ungueltiger Vertikalabstands-Marker in Zeile "
                                f"{absolute_line_no}: `{stripped_line}`. "
                                "Erwartet: `-=<zahl><einheit>`, z. B. `-=0.2cm`."
                            ),
                            severity="error",
                            line_number=absolute_line_no,
                        )
                    )
                if stripped_line.startswith("--hf") and not _VALID_SLIDE_CHROME_OFF_PATTERN.match(stripped_line):
                    diagnostics.append(
                        BuildDiagnostic(
                            code="BL006",
                            message=(
                                "Ungueltiger Folien-Chrome-Marker in Zeile "
                                f"{absolute_line_no}: `{stripped_line}`. "
                                "Erwartet: `--hf`."
                            ),
                            severity="error",
                            line_number=absolute_line_no,
                        )
                    )
            continue

        if _BLOCK_WHITESPACE_AFTER_MARKER_PATTERN.match(stripped_line):
            diagnostics.append(
                BuildDiagnostic(
                    code="BL002",
                    message=(
                        "Ungueltige Blocksyntax in Zeile "
                        f"{absolute_line_no}: Nach `:::` darf kein Leerzeichen folgen. "
                        "Erlaubt sind nur `:::blocktyp` oder `:::`."
                    ),
                    severity="error",
                    line_number=absolute_line_no,
                )
            )
            continue

        if stripped_line == ":::":
            if not block_stack:
                diagnostics.append(
                    BuildDiagnostic(
                        code="BL003",
                        message=(
                            "Ungueltiger Blockabschluss in Zeile "
                            f"{absolute_line_no}: `:::` ohne passenden geoeffneten Block."
                        ),
                        severity="error",
                        line_number=absolute_line_no,
                    )
                )
            else:
                block_stack.pop()
            continue

        self_closing_match = _SELF_CLOSING_BLOCK_PATTERN.match(stripped_line)
        if self_closing_match:
            if block_stack:
                nested_type = self_closing_match.group(1)
                open_type = block_stack[-1]
                diagnostics.append(
                    BuildDiagnostic(
                        code="BL004",
                        message=(
                            "Ungueltiger Blockwechsel in Zeile "
                            f"{absolute_line_no}: `:::{nested_type} ... :::` beginnt, bevor "
                            f"der geoeffnete Block `:::{open_type}` geschlossen wurde. "
                            "Blattwerk unterstuetzt keine verschachtelten Bloecke; "
                            "setze zuerst eine eigene Zeile mit `:::` zum Schliessen des "
                            "aktuellen Blocks."
                        ),
                        severity="error",
                        line_number=absolute_line_no,
                    )
                )
            continue

        start_match = _BLOCK_START_PATTERN.match(stripped_line)
        if start_match:
            open_type = block_stack[-1] if block_stack else None
            if block_stack:
                nested_type = start_match.group(1)
                follow_block_hint = ""
                if open_type == "task" and nested_type == "subtask":
                    follow_block_hint = (
                        " `subtask` ist ein Folgeblock auf Top-Level: "
                        "zuerst `task` mit `:::` schliessen, dann `:::subtask` oeffnen."
                    )
                diagnostics.append(
                    BuildDiagnostic(
                        code="BL004",
                        message=(
                            "Ungueltiger Blockwechsel in Zeile "
                            f"{absolute_line_no}: `:::{nested_type}` beginnt, bevor der "
                            f"geoeffnete Block `:::{open_type}` geschlossen wurde. "
                            "Blattwerk unterstuetzt keine verschachtelten Bloecke; "
                            "setze zuerst eine eigene Zeile mit `:::` zum Schliessen des "
                            f"aktuellen Blocks.{follow_block_hint}"
                        ),
                        severity="error",
                        line_number=absolute_line_no,
                    )
                )
                continue
            block_stack.append(start_match.group(1))

    return diagnostics


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
