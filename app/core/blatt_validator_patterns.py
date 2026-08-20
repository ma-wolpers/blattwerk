"""Kompilierte Regex-Muster für den Blattwerk-Validator.

Reine Datendatei (kompilierte `re.Pattern`-Konstanten ohne Logik) — vom
300-Zeilen-Limit ausgenommen, aber ohnehin klein. Getrennt von
`blatt_validator_constants.py`, damit die deutlich umfangreichere
`BLOCK_ALLOWED_OPTIONS`-Struktur nicht mit den Regex-Definitionen vermischt
wird.
"""

from __future__ import annotations

import re

_MARKDOWN_IMAGE_PATH_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
_HTML_IMAGE_SRC_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.IGNORECASE)
_WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")
_UNC_ABSOLUTE_PATH_RE = re.compile(r"^[\\/]{2}[^\\/]+[\\/][^\\/]+")
_POSIX_ABSOLUTE_PATH_RE = re.compile(r"^/")
_BLOCK_START_PATTERN = re.compile(r"^:::(\w+)(.*)$")
_SELF_CLOSING_BLOCK_PATTERN = re.compile(r"^:::(\w+)(.*?):::$")
_BLOCK_WHITESPACE_AFTER_MARKER_PATTERN = re.compile(r"^:::\s+")
_VALID_SECTION_MARK_PATTERN = re.compile(r"^--#\s+.+$")
_VALID_VSPACER_MARK_PATTERN = re.compile(
    r"^-=\s*\d+(?:\.\d+)?(?:cm|mm|px|pt|em|rem|vh|vw|%)\s*$",
    flags=re.IGNORECASE,
)
_VALID_SLIDE_CHROME_OFF_PATTERN = re.compile(r"^--hf\s*$")
_QRCODE_CSS_SIZE_PATTERN = re.compile(
    r"(?:\d+(?:\.\d+)?(?:px|%|cm|mm|in|pt|em|rem|vw|vh|vmin|vmax)?|auto)",
    flags=re.IGNORECASE,
)
