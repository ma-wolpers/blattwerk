"""Validierung der `key=value`-Optionen eines einzelnen `:::blocktyp ...`-Headers.

Aus `blatt_validator_document.py` ausgelagert, da diese eine Funktion
(die Options-Werteprüfung mit ihrer langen `elif`-Kette) allein bereits
gut ein Drittel der Zeilen der ursprünglichen ~400-Zeilen-Datei ausmachte.

Die einfachen Enum-Optionen (`mode`, `work`, `action`, `hint`, `line` --
strukturell identisch: "Wert nicht in der für diesen Blocktyp erlaubten
Menge -> `OP002`") werden generisch aus `BLOCK_OPTION_SPECS`
(`blatt_validator_constants.py`) geprüft, statt vier/fünf fast identische
`elif`-Zweige zu pflegen: der Katalogeintrag *ist* die Prüfregel, kann
strukturell nicht mehr von ihr abweichen. `show` (eigener Deprecation-
Zweig `OP003`), `align`/`alignment` (Sonderregel: bei `table`/`matching`
nicht über diesen generischen Weg geprüft, siehe deren eigene
Katalogeinträge) und `qrcode`s `url`/Größenoptionen bleiben bewusst
eigene Sonderlogik -- echte Blockausnahmen, kein sauberer generischer Fall.
"""

from __future__ import annotations

from .blatt_validator_constants import (
    ANSWER_BLOCK_TYPES,
    BLOCK_OPTION_SPECS,
    KNOWN_SHOW_VALUES,
    OBJECT_ALIGN_VALUE_HINT,
    QRCODE_SIZE_OPTION_KEYS,
)
from .blatt_validator_types import BuildDiagnostic
from .blatt_validator_value_helpers import (
    _append_invalid_option_value,
    _is_valid_object_align,
    _is_valid_qrcode_css_size,
    _is_valid_qrcode_url,
    _normalize_value,
    _option_items,
)

_GENERIC_VALIDATED_ENUM_OPTION_NAMES = {"mode", "work", "action", "hint", "line"}


def _lookup_option_spec(block_type, option_key):
    """Findet den `BlockOptionSpec` für `(block_type, option_key)`, falls vorhanden."""
    for spec in BLOCK_OPTION_SPECS.get(block_type, ()):
        if spec.name == option_key:
            return spec
    return None


def _validate_generic_enum_option(diagnostics, index, block_type, option_key, option_value, normalized_value):
    """Prüft eine Option generisch gegen `BLOCK_OPTION_SPECS`, wenn ihr Katalogeintrag ein validiertes Enum ist.

    Deckt `mode`/`work`/`action`/`hint` (blockübergreifend) sowie `line`
    (nur bei `grid`/`geometry`, wo es überhaupt als Option existiert --
    andere Blöcke scheitern für `line` bereits vorher an `OP001`) ab.
    """
    spec = _lookup_option_spec(block_type, option_key)
    if spec is None or spec.kind != "enum" or not spec.validated or not spec.allowed_values:
        return
    if normalized_value not in spec.allowed_values:
        _append_invalid_option_value(
            diagnostics, index, block_type, option_key, option_value, spec.allowed_values
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
                )
            )
            continue

        normalized_value = _normalize_value(option_value)
        if option_key == "show" and normalized_value not in KNOWN_SHOW_VALUES:
            _append_invalid_option_value(
                diagnostics, index, block_type, option_key, option_value, KNOWN_SHOW_VALUES
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
                )
            )
        elif option_key in _GENERIC_VALIDATED_ENUM_OPTION_NAMES:
            _validate_generic_enum_option(
                diagnostics, index, block_type, option_key, option_value, normalized_value
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
                    )
                )

    return qrcode_url_value
