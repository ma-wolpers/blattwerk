"""Kleine Wert-/Format-Prüfungen und Diagnose-Bausteine für den Blattwerk-Validator.

Enthält Funktionen, die einzelne Rohwerte (Options-Werte, Pfade, URLs,
CSS-Größen) auf Gültigkeit prüfen oder normalisieren, sowie zwei
Hilfsfunktionen, die eine `BuildDiagnostic` in ein vorhandenes
Diagnose-Array anhängen (`_append_invalid_option_value`,
`_append_invalid_yaml_show_diagnostic`) — beide werden von mehreren
Call-Sites in `blatt_validator_document.py` mit identischem Diagnosecode
verwendet und sollen deshalb nicht mehrfach dupliziert werden.
"""

from __future__ import annotations

from urllib.parse import urlparse

import yaml

from .blatt_validator_constants import KNOWN_ALIGN_VALUES
from .blatt_validator_patterns import (
    _POSIX_ABSOLUTE_PATH_RE,
    _QRCODE_CSS_SIZE_PATTERN,
    _UNC_ABSOLUTE_PATH_RE,
    _WINDOWS_ABSOLUTE_PATH_RE,
    _MARKDOWN_IMAGE_PATH_RE,
    _HTML_IMAGE_SRC_RE,
)
from .blatt_validator_types import BuildDiagnostic


def _normalize_value(value):
    """Normalisiert einen rohen Options-Wert für robuste Vergleiche (getrimmt, lowercase)."""
    return (value or "").strip().lower()


def _is_truthy_meta_bool(value):
    """Interpretiert Frontmatter-Bool-Werte aus verschiedenen Nutzer-Schreibweisen."""
    if isinstance(value, bool):
        return True

    normalized = _normalize_value(str(value or ""))
    return normalized in {
        "1",
        "true",
        "wahr",
        "ja",
        "yes",
        "on",
        "0",
        "false",
        "falsch",
        "nein",
        "no",
        "off",
    }


def _as_matching_list(value):
    """Normalisiert einen `matching`-Seiten-Wert (Liste oder `|`/`,`/Zeilen-getrennter Text) zu einer Liste."""
    if isinstance(value, list):
        return [entry for entry in value if str(entry).strip()]
    if isinstance(value, str):
        normalized = value.replace("\n", "|").replace(",", "|")
        return [entry.strip() for entry in normalized.split("|") if entry.strip()]
    return []


def _get_matching_item_counts(options, content):
    """Ermittelt die Anzahl Elemente je Seite eines `matching`-Blocks (für `MA001`).

    Liest sowohl aus dem YAML-Payload (`content`) als auch aus den
    Block-Optionen, da `matching`-Listen historisch an beiden Stellen
    definiert werden können; YAML-Werte haben Vorrang, Options-Werte dienen
    als Fallback, falls im YAML nichts gesetzt ist.
    """
    payload = {}
    try:
        parsed = yaml.safe_load(content or "")
        if isinstance(parsed, dict):
            payload = parsed
    except yaml.YAMLError:
        payload = {}

    layout_raw = _normalize_value(
        (options or {}).get("layout") or (options or {}).get("orientation")
    )
    if not layout_raw and (payload.get("top") or payload.get("bottom")):
        layout_raw = "vertical"

    if layout_raw in {"vertical", "topbottom", "tb", "obenunten", "oben_unten"}:
        first_items = _as_matching_list(
            payload.get("top") or payload.get("oben") or payload.get("first")
        )
        second_items = _as_matching_list(
            payload.get("bottom") or payload.get("unten") or payload.get("second")
        )
    else:
        first_items = _as_matching_list(
            payload.get("left") or payload.get("links") or payload.get("first")
        )
        second_items = _as_matching_list(
            payload.get("right") or payload.get("rechts") or payload.get("second")
        )

    if not first_items:
        first_items = _as_matching_list(
            (options or {}).get("left") or (options or {}).get("top")
        )
    if not second_items:
        second_items = _as_matching_list(
            (options or {}).get("right") or (options or {}).get("bottom")
        )

    return len(first_items), len(second_items)


def _option_items(options):
    """Iteriert Block-Optionen und überspringt interne Laufzeit-Schlüssel (`_`-Präfix, z. B. `_printable_width_cm`)."""
    for key, value in (options or {}).items():
        if str(key).startswith("_"):
            continue
        yield key, value


def _is_local_absolute_path(path_text):
    """Erkennt lokale absolute Dateipfade (Windows/UNC/POSIX), aber keine URLs/Data-URIs."""
    normalized = str(path_text or "").strip().strip("\"").strip("'")
    if not normalized:
        return False

    if normalized.startswith(("http://", "https://", "data:", "mailto:")):
        return False

    return bool(
        _WINDOWS_ABSOLUTE_PATH_RE.match(normalized)
        or _UNC_ABSOLUTE_PATH_RE.match(normalized)
        or _POSIX_ABSOLUTE_PATH_RE.match(normalized)
    )


def _collect_absolute_image_paths(block_content):
    """Sammelt absolute lokale Bildpfade aus Markdown- und HTML-`<img>`-Referenzen (für `PT001`)."""
    paths = []
    content = str(block_content or "")

    for match in _MARKDOWN_IMAGE_PATH_RE.finditer(content):
        candidate = match.group(1).strip()
        if _is_local_absolute_path(candidate):
            paths.append(candidate)

    for match in _HTML_IMAGE_SRC_RE.finditer(content):
        candidate = match.group(1).strip()
        if _is_local_absolute_path(candidate):
            paths.append(candidate)

    return paths


def _is_valid_qrcode_css_size(value):
    """Prüft, ob ein `qrcode`-Größenwert (`w`/`h`/`maxw`/...) eine gültige CSS-Länge oder `auto` ist."""
    text = str(value or "").strip()
    if not text:
        return False
    return bool(_QRCODE_CSS_SIZE_PATTERN.fullmatch(text))


def _is_valid_object_align(value):
    """Prüft einen `align`/`alignment`-Wert gegen die unterstützten deutschen/englischen Schreibweisen."""
    normalized = _normalize_value(str(value or ""))
    normalized = normalized.replace("ü", "u").replace("ß", "ss")
    return normalized in KNOWN_ALIGN_VALUES


def _is_valid_qrcode_url(value):
    """Prüft, ob ein `qrcode`-`url`-Wert ein http(s)-Link oder ein relativer Pfad ohne Leerzeichen ist."""
    text = str(value or "").strip()
    if not text or any(character.isspace() for character in text):
        return False

    parsed = urlparse(text)
    if parsed.scheme in {"http", "https"}:
        return bool(parsed.netloc)

    if parsed.scheme:
        return False

    return not text.startswith("//")


def _extract_validation_content_and_base_line(markdown_text):
    """Liefert den zu validierenden Inhalt (ohne Frontmatter) und dessen 1-basierte Startzeile im Gesamtdokument.

    Wird gebraucht, damit gemeldete `line_number`-Werte in Diagnosen sich
    auf die Zeilennummer im *Originaldokument* beziehen, nicht auf die
    Zeilennummer im (um das Frontmatter gekürzten) Validierungsausschnitt.
    """
    lines = (markdown_text or "").splitlines(keepends=True)
    content_start_line = 1
    content_raw = markdown_text or ""

    if lines and lines[0].strip() == "---":
        for line_index in range(1, len(lines)):
            if lines[line_index].strip() == "---":
                content_start_line = line_index + 2
                content_raw = "".join(lines[line_index + 1 :])
                break

    content_for_validation = content_raw.strip()
    if not content_for_validation:
        return "", max(1, content_start_line)

    leading_removed_text = content_raw[: content_raw.find(content_for_validation)]
    leading_removed_lines = leading_removed_text.count("\n")
    base_line = content_start_line + leading_removed_lines
    return content_for_validation, max(1, base_line)


def _append_invalid_option_value(
    diagnostics, block_index, block_type, option, value, allowed
):
    """Hängt eine `OP002`-Diagnose (ungültiger Options-Wert) an `diagnostics` an."""
    diagnostics.append(
        BuildDiagnostic(
            code="OP002",
            message=(
                f"Ungueltiger Wert fuer `{option}` in Block `{block_type}`: `{value}`. "
                f"Erlaubt: {', '.join(sorted(allowed))}."
            ),
            block_index=block_index,
            block_type=block_type,
        )
    )


def _append_invalid_yaml_show_diagnostic(
    diagnostics,
    block_index,
    answer_type,
    section,
    position,
    value,
):
    """Hängt eine `AN007`-Diagnose (ungültiger YAML-`show`-Marker) an `diagnostics` an."""
    diagnostics.append(
        BuildDiagnostic(
            code="AN007",
            message=(
                "YAML nutzt ungueltigen Sichtbarkeitswert "
                f"`{value}` in answer `{answer_type}` bei `{section}[{position}].show`. "
                "Erlaubt sind nur `&`, `§` oder `%`."
            ),
            severity="error",
            block_index=block_index,
            block_type=answer_type,
        )
    )
