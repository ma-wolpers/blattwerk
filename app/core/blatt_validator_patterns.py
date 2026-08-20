"""Kompilierte Regex-Muster für den Blattwerk-Validator.

Reine Datendatei (kompilierte `re.Pattern`-Konstanten ohne Logik) — vom
300-Zeilen-Limit ausgenommen, aber ohnehin klein. Getrennt von
`blatt_validator_constants.py`, damit die deutlich umfangreichere
`BLOCK_ALLOWED_OPTIONS`-Struktur nicht mit den Regex-Definitionen vermischt
wird.

Die Block-Marker- und Kontrollsyntax-Muster (`_BLOCK_START_PATTERN`,
`_SELF_CLOSING_BLOCK_PATTERN`, `_VALID_SECTION_MARK_PATTERN`,
`_VALID_VSPACER_MARK_PATTERN`, `_VALID_SLIDE_CHROME_OFF_PATTERN`) sind
**keine** Neudefinitionen, sondern werden direkt aus
`blatt_kern_shared` (`_BLOCK_START_PATTERN`/`_SELF_CLOSING_BLOCK_PATTERN`)
bzw. `CONTROL_MARKERS` (Sektions-/Vertikalabstands-/Folien-Chrome-Marker)
abgeleitet — dem Parser, der dieselbe Syntax tatsächlich interpretiert.
Vor dieser Änderung pflegte dieses Modul eigene, inhaltlich identische
Kopien dieser Muster; das war eine echte, unbeabsichtigte Doppelquelle
(Parser- und Validator-Syntax konnten unbemerkt auseinanderlaufen).
"""

from __future__ import annotations

import re

from .blatt_kern_shared import (
    PRESENTATION_SECTION_MARK_PATTERN,
    PRESENTATION_SPACER_MARK_PATTERN,
    CONTROL_MARKERS,
)
from .blatt_kern_shared_parsing import _BLOCK_START_PATTERN, _SELF_CLOSING_BLOCK_PATTERN

_MARKDOWN_IMAGE_PATH_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
_HTML_IMAGE_SRC_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.IGNORECASE)
_WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")
_UNC_ABSOLUTE_PATH_RE = re.compile(r"^[\\/]{2}[^\\/]+[\\/][^\\/]+")
_POSIX_ABSOLUTE_PATH_RE = re.compile(r"^/")
_BLOCK_WHITESPACE_AFTER_MARKER_PATTERN = re.compile(r"^:::\s+")

# Funktional identisch zu den bisherigen eigenen `_VALID_*`-Mustern
# (nur mit Capture-Gruppe statt ohne, was `.match()` nicht beeinflusst) --
# direkt aus der Parser-Quelle übernommen statt dupliziert.
_VALID_SECTION_MARK_PATTERN = PRESENTATION_SECTION_MARK_PATTERN
_VALID_VSPACER_MARK_PATTERN = PRESENTATION_SPACER_MARK_PATTERN

_SLIDE_CHROME_OFF_LITERAL = next(
    marker.literal_or_regex for marker in CONTROL_MARKERS if marker.name == "slidechromeoff"
)
_VALID_SLIDE_CHROME_OFF_PATTERN = re.compile(
    rf"^{re.escape(_SLIDE_CHROME_OFF_LITERAL)}\s*$"
)

_QRCODE_CSS_SIZE_PATTERN = re.compile(
    r"(?:\d+(?:\.\d+)?(?:px|%|cm|mm|in|pt|em|rem|vw|vh|vmin|vmax)?|auto)",
    flags=re.IGNORECASE,
)
