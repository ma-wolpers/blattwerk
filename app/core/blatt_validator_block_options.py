"""Validierung der `key=value`-Optionen eines einzelnen `:::blocktyp ...`-Headers.

Aus `blatt_validator_document.py` ausgelagert, da diese eine Funktion
(die Options-Werteprüfung mit ihrer langen `elif`-Kette) allein bereits
gut ein Drittel der Zeilen der ursprünglichen ~400-Zeilen-Datei ausmachte.
"""

from __future__ import annotations

from .blatt_validator_constants import (
    ANSWER_BLOCK_TYPES,
    KNOWN_ACTION_VALUES,
    KNOWN_BLOCK_MODE_VALUES,
    KNOWN_GRID_LINE_STYLES,
    KNOWN_HINT_VALUES,
    KNOWN_SHOW_VALUES,
    KNOWN_WORK_VALUES,
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
        elif option_key == "mode" and normalized_value not in KNOWN_BLOCK_MODE_VALUES:
            _append_invalid_option_value(
                diagnostics, index, block_type, option_key, option_value, KNOWN_BLOCK_MODE_VALUES
            )
        elif option_key == "work" and normalized_value not in KNOWN_WORK_VALUES:
            _append_invalid_option_value(
                diagnostics, index, block_type, option_key, option_value, KNOWN_WORK_VALUES
            )
        elif (
            option_key == "action"
            and normalized_value not in KNOWN_ACTION_VALUES
        ):
            _append_invalid_option_value(
                diagnostics, index, block_type, option_key, option_value, KNOWN_ACTION_VALUES
            )
        elif option_key == "hint" and normalized_value not in KNOWN_HINT_VALUES:
            _append_invalid_option_value(
                diagnostics, index, block_type, option_key, option_value, KNOWN_HINT_VALUES
            )
        elif (
            option_key == "line"
            and block_type in {"grid", "geometry"}
            and normalized_value not in KNOWN_GRID_LINE_STYLES
        ):
            _append_invalid_option_value(
                diagnostics, index, block_type, option_key, option_value, KNOWN_GRID_LINE_STYLES
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
