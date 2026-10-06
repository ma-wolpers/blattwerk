"""Validator für Schilder-Dokumente (`.sbw`).

Der Renderer (`schild_render.py`) ist absichtlich tolerant: ungültige
Optionen fallen still auf den Standard zurück, leere Stücke werden
übersprungen. Damit das nicht unbemerkt bleibt, meldet dieser Validator:

* ``SBW001`` (Fehler): Das Dokument enthält kein einziges Schild.
* ``SBW002`` (Warnung): Auf einen `---`-Trenner folgt ein leeres Stück
  (z. B. doppeltes `---` oder `---` am Ende) -- vermutlich ein Tippfehler.
* ``SBW003`` (Warnung): Unbekannter Wert für `ausrichtung`, `fett`,
  `schriftgroesse` oder ein `rand` außerhalb von 0-80 mm.

Die Marker-Diagnosen (`document_type`, FM008-FM010) kommen wie bei allen
Typen zusätzlich aus `document_semantics.marker_diagnostics`.
"""

from __future__ import annotations

from .blatt_validator_types import BuildDiagnostic
from .schild_render import (
    FONT_SIZE_MODES,
    MAX_MARGIN_MM,
    ORIENTATIONS,
    parse_bool_option,
    parse_margin_option,
    parse_schild,
)


def inspect_schild_text(text: str) -> list[BuildDiagnostic]:
    """Prüft einen `.sbw`-Text und liefert alle Schilder-Diagnosen.

    Args:
        text: Vollständiger Dokumenttext inkl. Frontmatter.

    Returns:
        Diagnosen in der Reihenfolge Optionen, leere Stücke, leeres Dokument.
    """
    parsed = parse_schild(text)
    diagnostics = _option_diagnostics(parsed.meta)
    diagnostics.extend(
        BuildDiagnostic(
            code="SBW002",
            message="Leeres Schild nach '---' (doppelter oder abschließender Trenner?).",
            severity="warning",
            line_number=line,
        )
        for line in parsed.empty_segment_lines
    )
    if not parsed.schilder:
        diagnostics.append(
            BuildDiagnostic(
                code="SBW001",
                message="Das Dokument enthält kein Schild. Schilder werden durch '---' getrennt.",
                severity="error",
            )
        )
    return diagnostics


def _option_diagnostics(meta: dict) -> list[BuildDiagnostic]:
    """SBW003 für jede gesetzte, aber ungültige Gestaltungsoption.

    Nicht gesetzte Optionen sind kein Fehler -- dann gilt der Standard.
    """
    problems: list[str] = []
    if "ausrichtung" in meta and str(meta["ausrichtung"]).strip().lower() not in ORIENTATIONS:
        problems.append(f"ausrichtung: '{meta['ausrichtung']}' (erlaubt: hoch, quer)")
    if "schriftgroesse" in meta and str(meta["schriftgroesse"]).strip().lower() not in FONT_SIZE_MODES:
        problems.append(f"schriftgroesse: '{meta['schriftgroesse']}' (erlaubt: einheitlich, maximal)")
    if "fett" in meta and parse_bool_option(meta["fett"]) is None:
        problems.append(f"fett: '{meta['fett']}' (erlaubt: ja, nein)")
    if "rand" in meta and parse_margin_option(meta["rand"]) is None:
        problems.append(f"rand: '{meta['rand']}' (erlaubt: Zahl in mm von 0 bis {MAX_MARGIN_MM:g})")
    return [
        BuildDiagnostic(
            code="SBW003",
            message=f"Ungültige Option {problem} -- es gilt der Standardwert.",
            severity="warning",
        )
        for problem in problems
    ]
