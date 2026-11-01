"""Validierung der `key=value`-Optionen eines einzelnen `:::blocktyp ...`-Headers.

Aus `blatt_validator_document.py` ausgelagert, da diese eine Funktion
(die Options-Werteprüfung mit ihrer langen `elif`-Kette) allein bereits
gut ein Drittel der Zeilen der ursprünglichen ~400-Zeilen-Datei ausmachte.

Die einfachen Enum-Optionen (`mode`, `work`, `action`, `hint`, `line`,
`type`, `background` -- strukturell identisch: "Wert nicht in der für
diesen Blocktyp erlaubten Menge -> `OP002`") werden generisch aus `BLOCK_OPTION_SPECS`
(`blatt_validator_constants.py`) geprüft, statt vier/fünf fast identische
`elif`-Zweige zu pflegen: der Katalogeintrag *ist* die Prüfregel, kann
strukturell nicht mehr von ihr abweichen. `show` (eigener Deprecation-
Zweig `OP003`), `align`/`alignment` (Sonderregel: bei `table`/`matching`
nicht über diesen generischen Weg geprüft, siehe deren eigene
Katalogeinträge) und `qrcode`s `url`/Größenoptionen bleiben bewusst
eigene Sonderlogik -- echte Blockausnahmen, kein sauberer generischer Fall.
"""

from __future__ import annotations

import re

from .blatt_kern_shared_data import JA_NEIN_BOOLEAN_TOKENS
from .answer_grid_axis import _resolve_axis_state
from .blatt_validator_constants import (
    ANSWER_BLOCK_TYPES,
    BLOCK_OPTION_SPECS,
    DEPRECATED_IGNORED_OPTIONS,
    KNOWN_SHOW_VALUES,
    OBJECT_ALIGN_VALUE_HINT,
    QRCODE_SIZE_OPTION_KEYS,
)
from .blatt_validator_region import compute_block_region_id
from .diagram_block_catalog import DIAGRAM_BLOCK_NAMES
from .blatt_validator_types import BuildDiagnostic
from .blatt_validator_value_helpers import (
    _append_invalid_option_value,
    _is_valid_object_align,
    _is_valid_qrcode_css_size,
    _is_valid_qrcode_url,
    _normalize_value,
    _option_items,
)

_CSS_LENGTH_RE = re.compile(r"^(?:auto|\d+(?:\.\d+)?(?:%|px|cm|mm|in|pt|em|rem|vh|vw)?)$", re.IGNORECASE)
_INTEGER_RE = re.compile(r"^-?\d+$")
_BOOLEAN_VALUES = JA_NEIN_BOOLEAN_TOKENS | {"none"}
_POSITIVE_INTEGER_OPTIONS = frozenset({"rows", "cols", "lines", "branches", "steps", "maxw", "maxh"})
"""Zahlen, bei denen 0 oder weniger nichts zu zeichnen übrig ließe."""

_GENERIC_VALIDATED_ENUM_OPTION_NAMES = {"mode", "work", "action", "hint", "line", "type", "background", "afb", "level", "scope", "labels"}


def _lookup_option_spec(block_type, option_key):
    """Findet den `BlockOptionSpec` für `(block_type, option_key)`, falls vorhanden."""
    for spec in BLOCK_OPTION_SPECS.get(block_type, ()):
        if spec.name == option_key:
            return spec
    return None


def _validate_generic_enum_option(diagnostics, index, block_type, option_key, option_value, normalized_value, options):
    """Prüft eine Option generisch gegen `BLOCK_OPTION_SPECS`, wenn ihr Katalogeintrag ein validiertes Enum ist.

    Deckt `mode`/`work`/`action`/`hint` (blockübergreifend) sowie `line`
    (nur bei `grid`/`geometry`), `type` (nur bei `info`) und `background`
    (nur bei `geometry`) ab -- jeweils nur dort, wo die Option überhaupt
    existiert; andere Blöcke scheitern für diese Keys bereits vorher an
    `OP001`.
    """
    spec = _lookup_option_spec(block_type, option_key)
    if spec is None or spec.kind != "enum" or not spec.validated or not spec.allowed_values:
        return
    if normalized_value not in spec.allowed_values:
        _append_invalid_option_value(
            diagnostics, index, block_type, option_key, option_value, spec.allowed_values, options
        )


def _validate_option_value_form(diagnostics, index, block_type, option_key, option_value, options):
    """Prüft CSS-Längen, Zahlen und Wahrheitswerte aller Blöcke (`OP006`-`OP008`).

    Die Renderer fallen bei unlesbaren Werten still auf den Standard zurück. Wer `height=abc`
    schreibt, sähe also nur eine falsche Größe, ohne Hinweis auf die Ursache.
    """
    spec = _lookup_option_spec(block_type, option_key)
    if spec is None:
        return
    value = str(option_value).strip()
    problem = None
    if spec.kind == "css_length" and not _CSS_LENGTH_RE.match(value):
        problem = ("OP006", f"`{option_key}={value}` ist keine CSS-Länge wie `70%` oder `3cm`.")
    elif spec.kind == "integer":
        number = _INTEGER_RE.match(value)
        if not number:
            problem = ("OP007", f"`{option_key}={value}` ist keine ganze Zahl.")
        elif option_key in _POSITIVE_INTEGER_OPTIONS and int(value) <= 0:
            problem = ("OP007", f"`{option_key}={value}` muss größer als 0 sein.")
    elif spec.kind == "boolean" and value.lower() not in _BOOLEAN_VALUES:
        problem = ("OP008", f"`{option_key}={value}` ist kein Wahrheitswert wie `true` oder `false`.")
    if problem:
        diagnostics.append(
            BuildDiagnostic(
                code=problem[0],
                message=problem[1],
                block_index=index,
                block_type=block_type,
                region_id=compute_block_region_id(block_type, options),
                anchor=option_key,
            )
        )


def _validate_geometry_axis_origin_pair(diagnostics, index, block_type, options):
    """Prüft `:::geometry axis=true` ohne gültiges `origin` (`OP005`).

    Nutzt exakt `_resolve_axis_state` (`answer_grid_axis.py`), dieselbe
    Funktion, die auch der Renderer (`render_geometry_answer`,
    `_render_grid_primitives_svg`) für dieselbe Entscheidung aufruft --
    Validator und Renderer können dadurch strukturell nicht auseinander-
    laufen. `severity="error"`, weil der praktische Effekt der totale,
    stille Verlust des gesamten Geometry-Payloads dieses Blocks ist (kein
    Achsenkreuz, keine Shapes, keine Labels, in keinem Koordinatenmodus --
    siehe `_render_grid_primitives_svg`'s `"broken"`-Frühausstieg), nicht
    nur eine kosmetische Abweichung.
    """
    axis_state, _origin = _resolve_axis_state(options)
    if axis_state != "broken":
        return
    diagnostics.append(
        BuildDiagnostic(
            code="OP005",
            message=(
                "`axis=true` ohne gueltiges `origin` (Format \"col,row\"). Der gesamte "
                "Geometry-Payload dieses Blocks (alle Sektionen) wird dadurch nicht "
                "gerendert -- kein stiller Ruecksfall auf Rasterkoordinaten."
            ),
            severity="error",
            block_index=index,
            block_type=block_type,
            region_id=compute_block_region_id(block_type, options),
            anchor="axis",
        )
    )


def _validate_block_options(diagnostics, index, block_type, options, allowed_options):
    """Validiert die `key=value`-Optionen eines Blocks und hängt Diagnosen an `diagnostics` an.

    Liefert den `url`-Wert eines `qrcode`-Blocks zurück (leerer String, wenn
    keiner gesetzt ist) — der Aufrufer braucht ihn nach dieser Funktion noch
    für die `QR001`("Pflichtoption fehlt")-Prüfung, die erst nach der
    kompletten Options-Schleife feststellbar ist.
    """
    qrcode_url_value = ""

    for option_key, option_value in _option_items(options):
        if option_key == "type" and block_type in ANSWER_BLOCK_TYPES:
            diagnostics.append(
                BuildDiagnostic(
                    code="AN009",
                    message=(
                        f"Option `type` ist in Block `{block_type}` unzulaessig. "
                        "Der Blocktyp selbst definiert bereits den Antworttyp."
                    ),
                    severity="error",
                    block_index=index,
                    block_type=block_type,
                    region_id=compute_block_region_id(block_type, options),
                    anchor=option_key,
                )
            )
            continue

        if option_key in DEPRECATED_IGNORED_OPTIONS.get(block_type, ()):
            diagnostics.append(
                BuildDiagnostic(
                    code="OP004",
                    message=(
                        f"Option `{option_key}` bei `:::{block_type}` ist veraltet und wird ignoriert -- "
                        "Loesungen erscheinen nur in der Loesungsfassung."
                    ),
                    block_index=index,
                    block_type=block_type,
                    region_id=compute_block_region_id(block_type, options),
                    anchor=option_key,
                )
            )
            continue

        if option_key not in allowed_options:
            diagnostics.append(
                BuildDiagnostic(
                    code="OP001",
                    message=f"Unbekannte Option `{option_key}` in Block `{block_type}`.",
                    block_index=index,
                    block_type=block_type,
                    region_id=compute_block_region_id(block_type, options),
                    anchor=option_key,
                )
            )
            continue

        normalized_value = _normalize_value(option_value)
        _validate_option_value_form(diagnostics, index, block_type, option_key, option_value, options)
        if option_key == "show" and normalized_value not in KNOWN_SHOW_VALUES:
            _append_invalid_option_value(
                diagnostics, index, block_type, option_key, option_value, KNOWN_SHOW_VALUES, options
            )
        elif option_key == "show":
            diagnostics.append(
                BuildDiagnostic(
                    code="OP003",
                    message=(
                        f"Option `show` in Block `{block_type}` ist veraltet. "
                        "Bitte `mode=worksheet|solution` verwenden."
                    ),
                    block_index=index,
                    block_type=block_type,
                    region_id=compute_block_region_id(block_type, options),
                    anchor=option_key,
                )
            )
        elif option_key in _GENERIC_VALIDATED_ENUM_OPTION_NAMES or block_type in DIAGRAM_BLOCK_NAMES:
            _validate_generic_enum_option(
                diagnostics, index, block_type, option_key, option_value, normalized_value, options
            )
        elif (
            option_key in {"align", "alignment"}
            and block_type not in {"matching", "table"}
            and not _is_valid_object_align(option_value)
        ):
            diagnostics.append(
                BuildDiagnostic(
                    code="OP002",
                    message=(
                        "Ungueltiger Wert fuer "
                        f"`{option_key}` in Block `{block_type}`: `{option_value}`. "
                        f"Erlaubt ist `{OBJECT_ALIGN_VALUE_HINT}`."
                    ),
                    block_index=index,
                    block_type=block_type,
                    region_id=compute_block_region_id(block_type, options),
                    anchor=option_key,
                )
            )
        elif block_type == "qrcode" and option_key in QRCODE_SIZE_OPTION_KEYS:
            if not _is_valid_qrcode_css_size(option_value):
                diagnostics.append(
                    BuildDiagnostic(
                        code="OP002",
                        message=(
                            "Ungueltiger Wert fuer "
                            f"`{option_key}` in Block `qrcode`: `{option_value}`. "
                            "Erlaubt ist eine CSS-Groesse wie `3cm`, `120px`, `60%` oder `auto`."
                        ),
                        block_index=index,
                        block_type=block_type,
                        region_id=compute_block_region_id(block_type, options),
                        anchor=option_key,
                    )
                )
        elif block_type == "qrcode" and option_key == "url":
            qrcode_url_value = str(option_value or "").strip()
            if qrcode_url_value and not _is_valid_qrcode_url(qrcode_url_value):
                diagnostics.append(
                    BuildDiagnostic(
                        code="QR002",
                        message=(
                            "Ungueltiger QR-Link in Block `qrcode`. "
                            "Erlaubt sind http/https-Links oder relative Pfade ohne Leerzeichen."
                        ),
                        severity="error",
                        block_index=index,
                        block_type=block_type,
                        region_id=compute_block_region_id(block_type, options),
                        anchor=option_key,
                    )
                )

    if block_type == "geometry":
        _validate_geometry_axis_origin_pair(diagnostics, index, block_type, options)

    return qrcode_url_value
