"""Validierung und Metadaten fuer nutzerspezifische Einstellungen.

Der Katalog selbst (`TAB_ORDER`, `TAB_LABELS`, `PREFERENCE_SPECS`) liegt als reines
Datenmodul in `user_preferences_specs.py` und wird hier re-exportiert.
"""

from __future__ import annotations

from copy import deepcopy

from .user_preferences_specs import PREFERENCE_SPECS, TAB_LABELS, TAB_ORDER

__all__ = [
    "PREFERENCE_SPECS",
    "TAB_LABELS",
    "TAB_ORDER",
    "default_user_preferences",
    "get_tab_specs",
    "normalize_user_preferences",
]


def default_user_preferences() -> dict[str, object]:
    payload: dict[str, object] = {}
    for key, spec in PREFERENCE_SPECS.items():
        payload[key] = deepcopy(spec.get("default"))
    return payload


def _coerce_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return bool(default)


def _coerce_int(value: object, default: int, min_value: int | None, max_value: int | None) -> int:
    try:
        normalized = int(value)
    except Exception:
        normalized = int(default)
    if min_value is not None:
        normalized = max(min_value, normalized)
    if max_value is not None:
        normalized = min(max_value, normalized)
    return normalized


def _coerce_float(value: object, default: float, min_value: float | None, max_value: float | None) -> float:
    try:
        normalized = float(value)
    except Exception:
        normalized = float(default)
    if min_value is not None:
        normalized = max(min_value, normalized)
    if max_value is not None:
        normalized = min(max_value, normalized)
    return normalized


def _coerce_enum(value: object, default: str, allowed_values: list[str]) -> str:
    text = str(value or "").strip()
    return text if text in allowed_values else str(default)


def _coerce_str(value: object, default: str) -> str:
    text = str(value or "").strip()
    return text if text else str(default)


def normalize_user_preferences(raw: object) -> dict[str, object]:
    defaults = default_user_preferences()
    if not isinstance(raw, dict):
        return defaults

    # Backward compatibility for pre-split export defaults.
    raw_payload = dict(raw)
    if "default_export_format_worksheet" not in raw_payload and "default_export_format" in raw_payload:
        raw_payload["default_export_format_worksheet"] = raw_payload["default_export_format"]
    if "default_export_format_presentation" not in raw_payload and "default_export_format" in raw_payload:
        raw_payload["default_export_format_presentation"] = raw_payload["default_export_format"]

    if "default_export_page_format_worksheet" not in raw_payload and "default_export_page_format" in raw_payload:
        raw_payload["default_export_page_format_worksheet"] = raw_payload["default_export_page_format"]
    if "default_export_page_format_presentation" not in raw_payload and "default_export_page_format" in raw_payload:
        raw_payload["default_export_page_format_presentation"] = raw_payload["default_export_page_format"]

    normalized = defaults
    for key, spec in PREFERENCE_SPECS.items():
        default_value = defaults[key]
        raw_value = raw_payload.get(key, default_value)
        pref_type = spec.get("type")

        if pref_type == "bool":
            normalized[key] = _coerce_bool(raw_value, bool(default_value))
            continue

        if pref_type == "int":
            normalized[key] = _coerce_int(
                raw_value,
                int(default_value),
                spec.get("min"),
                spec.get("max"),
            )
            continue

        if pref_type == "float":
            normalized[key] = _coerce_float(
                raw_value,
                float(default_value),
                spec.get("min"),
                spec.get("max"),
            )
            continue

        if pref_type == "enum":
            normalized[key] = _coerce_enum(raw_value, str(default_value), list(spec.get("values", [])))
            continue

        normalized[key] = _coerce_str(raw_value, str(default_value))

    return normalized


def get_tab_specs() -> list[tuple[str, str, list[tuple[str, dict[str, object]]]]]:
    result: list[tuple[str, str, list[tuple[str, dict[str, object]]]]] = []
    for tab_key in TAB_ORDER:
        tab_specs: list[tuple[str, dict[str, object]]] = []
        for key, spec in PREFERENCE_SPECS.items():
            if spec.get("tab") == tab_key:
                tab_specs.append((key, spec))
        result.append((tab_key, TAB_LABELS.get(tab_key, tab_key), tab_specs))
    return result
