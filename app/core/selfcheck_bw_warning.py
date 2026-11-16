"""Build-Warnung `SC002`: Ampel-Skala im Schwarz-Weiß-Profil.

Im S/W-Profil bekommen alle Emojis die Outline-Darstellung (`emoji_markup.py` plus
CSS-Regel in `worksheet_design.py`). Bei der Ampel (🔴🟡🟢) trägt aber gerade die
Farbe die Bedeutung, die Kreise sind dann kaum zu unterscheiden. Das Farbprofil ist
eine App-Einstellung und dem Validator unbekannt, deshalb prüft `build_worksheet`
diese Lage beim Bauen (wie `PT002`/`IM003`).
"""

from __future__ import annotations

from .answer_special_selfcheck import AMPEL_SCALE, resolve_selfcheck_scale
from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic
from ..styles.worksheet_design import normalize_color_profile

SC002_AMPEL_IN_BW = "SC002"
"""Diagnosecode der Warnung (in `blatt_ui_export._SURFACED_COMPILE_WARNING_CODES` sichtbar)."""

_SELFCHECK_BLOCK_TYPE = "selfcheck"


def append_bw_ampel_warnings(*, diagnostics_out, blocks, color_profile) -> None:
    """Hängt je `:::selfcheck`-Block mit `scale=ampel` eine `SC002`-Warnung an.

    Nur im S/W-Profil (`normalize_color_profile(color_profile) == "bw"`); in
    Farbprofilen bleibt die Ampel farbig und unterscheidbar.

    Args:
        diagnostics_out: Ausgabeliste für Diagnosen oder `None` (dann passiert nichts).
        blocks: Geparste Blöcke als `(block_type, options, content)`-Tupel.
        color_profile: Farbprofil des Builds (roh, wird normalisiert).
    """
    if diagnostics_out is None or normalize_color_profile(color_profile) != "bw":
        return
    for index, (block_type, options, _content) in enumerate(blocks or []):
        if block_type != _SELFCHECK_BLOCK_TYPE or resolve_selfcheck_scale(options) != AMPEL_SCALE:
            continue
        diagnostics_out.append(
            BuildDiagnostic(
                code=SC002_AMPEL_IN_BW,
                message=(
                    "Die Ampel-Skala (`scale=ampel`) ist im Schwarz-Weiß-Profil kaum "
                    "unterscheidbar, weil die Emojis dort ohne Farbe erscheinen. "
                    "Für S/W-Drucke eignet sich z. B. `scale=smiley` oder `scale=zahlen`."
                ),
                block_index=index,
                block_type=block_type,
                region_id=compute_block_region_id(block_type, options or {}),
                anchor="ampel-bw",
            )
        )
