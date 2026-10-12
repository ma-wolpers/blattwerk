"""Zahlenstrahl: Zahlwerte, Groessenangaben und Sichtbarkeit lesen und formatieren
(reine Hilfsfunktionen ohne Layout).
"""

from __future__ import annotations

import re


def _css_length_to_mm(css_size):
    """Convert absolute CSS lengths to mm where possible, else return None."""
    text = str(css_size or "").strip().lower()
    mm_match = re.fullmatch(r"(\d+(?:\.\d+)?)mm", text)
    if mm_match:
        return float(mm_match.group(1))

    cm_match = re.fullmatch(r"(\d+(?:\.\d+)?)cm", text)
    if cm_match:
        return float(cm_match.group(1)) * 10.0

    return None


def _format_numberline_value(value, positive_sign=False):
    """Format numeric values with compact decimal output and comma separator."""
    rounded = 0.0 if abs(value) < 1e-9 else value
    text = f"{rounded:.6f}".rstrip("0").rstrip(".")
    if text in {"-0", ""}:
        text = "0"
    if positive_sign and rounded > 0:
        text = f"+{text}"
    return text.replace(".", ",")


def _parse_css_size(raw_value, default_value):
    """Parse safe CSS sizes for answer-field width/height values."""
    if raw_value is None:
        return default_value

    text = str(raw_value).strip().lower().replace(",", ".")
    if text == "auto":
        return text
    if re.fullmatch(r"\d+(?:\.\d+)?(px|%|cm|mm|in|pt|em|rem|vh|vw)", text):
        return text
    return default_value


def _as_numberline_float(value):
    """Parse numeric values for numberline config, tolerant to decimal comma."""
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
    return _as_float(value)


def _parse_numberline_positive_float(value, default):
    """Parse strictly positive floats for numberline values (comma tolerant)."""
    parsed = _as_numberline_float(value)
    if parsed is None or parsed <= 0:
        return default
    return parsed


def _as_float(value):
    """Convert value to float and return None on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_visible(show_value, include_solutions):
    """Evaluate marker-based visibility for numberline elements."""
    if show_value in {"worksheet", "solution", "both", "invalid"}:
        normalized = show_value
    else:
        normalized = _normalize_show_mode(show_value)
    if normalized == "worksheet":
        return not include_solutions
    if normalized == "solution":
        return include_solutions
    if normalized == "both":
        return True
    return False


def _normalize_show_mode(show_value):
    """Normalize marker visibility to internal `worksheet|solution|both` mode."""
    normalized = str(show_value or "&").strip()
    if normalized == "§":
        return "worksheet"
    if normalized == "%":
        return "solution"
    if normalized == "&":
        return "both"
    return "invalid"
