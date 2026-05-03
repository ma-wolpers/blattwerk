"""Zentraler lokaler Config-Store fuer Blattwerk."""

from __future__ import annotations

import json
import math
import time
from copy import deepcopy
from pathlib import Path

from bw_libs.app_paths import atomic_write_json

DEFAULT_MAX_RECENT_FILES = 5
MIN_MAX_RECENT_FILES = 1
MAX_MAX_RECENT_FILES = 20

STORAGE_STATE_DIR = Path(__file__).resolve().parent / ".state"
LOCAL_CONFIG_PATH = STORAGE_STATE_DIR / "blattwerk_local_config.json"
LEGACY_RECENT_FILES_PATH = STORAGE_STATE_DIR / "blattwerk_recent.json"
LEGACY_UI_SETTINGS_PATH = STORAGE_STATE_DIR / "blattwerk_ui_settings.json"
ROOT_LEGACY_RECENT_FILES_PATH = Path(__file__).resolve().parents[2] / ".blattwerk_recent.json"
ROOT_LEGACY_UI_SETTINGS_PATH = Path(__file__).resolve().parents[2] / ".blattwerk_ui_settings.json"


SYSTEM_KEY = "system"
UI_SETTINGS_KEY = "ui_settings"
RECENT_FILES_KEY = "recent_files"
COMPLETION_STATS_KEY = "completion_stats"
USER_PREFERENCES_KEY = "user_preferences"

_COMPLETION_DECAY_HALF_LIFE_DAYS = 14.0
_SECONDS_PER_DAY = 86400.0


def _completion_decay_lambda() -> float:
    return math.log(2.0) / (_COMPLETION_DECAY_HALF_LIFE_DAYS * _SECONDS_PER_DAY)


def _decay_value(value: float, *, from_ts: float, to_ts: float) -> float:
    if value <= 0.0:
        return 0.0
    delta = max(0.0, float(to_ts) - float(from_ts))
    return value * math.exp(-_completion_decay_lambda() * delta)


DEFAULT_LOCAL_CONFIG = {
    "version": 1,
    SYSTEM_KEY: {
        "max_recent_files": DEFAULT_MAX_RECENT_FILES,
    },
    UI_SETTINGS_KEY: {},
    RECENT_FILES_KEY: [],
    COMPLETION_STATS_KEY: {
        "block_type_usage": {},
        "option_value_usage": {},
    },
    USER_PREFERENCES_KEY: {},
}


def _normalize_system_settings(raw: object) -> dict[str, object]:
    normalized = deepcopy(DEFAULT_LOCAL_CONFIG[SYSTEM_KEY])
    if not isinstance(raw, dict):
        return normalized

    max_recent_raw = raw.get("max_recent_files", DEFAULT_MAX_RECENT_FILES)
    try:
        max_recent_value = int(max_recent_raw)
    except Exception:
        max_recent_value = DEFAULT_MAX_RECENT_FILES
    max_recent_value = max(MIN_MAX_RECENT_FILES, min(MAX_MAX_RECENT_FILES, max_recent_value))
    normalized["max_recent_files"] = max_recent_value

    return normalized


def _normalize_recent_files(raw: object, max_recent_files: int) -> list[str]:
    if not isinstance(raw, list):
        return []

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in raw:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)

    return cleaned[:max_recent_files]


def _normalize_ui_settings(raw: object) -> dict[str, object]:
    return dict(raw) if isinstance(raw, dict) else {}


def _normalize_user_preferences(raw: object) -> dict[str, object]:
    return dict(raw) if isinstance(raw, dict) else {}


def _normalize_completion_stats(raw: object) -> dict[str, object]:
    base: dict[str, object] = {"block_type_usage": {}, "option_value_usage": {}}
    if not isinstance(raw, dict):
        return base

    def _normalize_usage_map(raw_map: object) -> dict[str, dict[str, float | int]]:
        if not isinstance(raw_map, dict):
            return {}

        normalized_usage: dict[str, dict[str, float | int]] = {}
        for raw_key, raw_entry in raw_map.items():
            key = str(raw_key or "").strip().lower()
            if not key:
                continue

            if isinstance(raw_entry, dict):
                count_raw = raw_entry.get("count", 0)
                last_used_raw = raw_entry.get("last_used", 0.0)
                score_raw = raw_entry.get("score", 0.0)
            else:
                count_raw = 0
                last_used_raw = 0.0
                score_raw = 0.0

            try:
                count = max(0, int(count_raw))
            except Exception:
                count = 0

            try:
                last_used = max(0.0, float(last_used_raw))
            except Exception:
                last_used = 0.0

            try:
                score = max(0.0, float(score_raw))
            except Exception:
                score = 0.0

            if count <= 0 and score <= 0.0:
                continue

            normalized_usage[key] = {
                "count": count,
                "last_used": last_used,
                "score": score,
            }

        return normalized_usage

    base["block_type_usage"] = _normalize_usage_map(raw.get("block_type_usage"))
    base["option_value_usage"] = _normalize_usage_map(raw.get("option_value_usage"))
    return base


def normalize_local_config(raw: object) -> dict[str, object]:
    base: dict[str, object] = deepcopy(DEFAULT_LOCAL_CONFIG)
    if not isinstance(raw, dict):
        return base

    system_settings = _normalize_system_settings(raw.get(SYSTEM_KEY))
    max_recent_raw = system_settings.get("max_recent_files", DEFAULT_MAX_RECENT_FILES)
    try:
        max_recent_files = int(str(max_recent_raw))
    except Exception:
        max_recent_files = DEFAULT_MAX_RECENT_FILES

    base[SYSTEM_KEY] = system_settings
    base[UI_SETTINGS_KEY] = _normalize_ui_settings(raw.get(UI_SETTINGS_KEY))
    base[RECENT_FILES_KEY] = _normalize_recent_files(raw.get(RECENT_FILES_KEY), max_recent_files)
    base[COMPLETION_STATS_KEY] = _normalize_completion_stats(raw.get(COMPLETION_STATS_KEY))
    base[USER_PREFERENCES_KEY] = _normalize_user_preferences(raw.get(USER_PREFERENCES_KEY))
    return base


def load_local_config() -> dict[str, object]:
    if not LOCAL_CONFIG_PATH.exists():
        return deepcopy(DEFAULT_LOCAL_CONFIG)

    try:
        payload = json.loads(LOCAL_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return deepcopy(DEFAULT_LOCAL_CONFIG)

    return normalize_local_config(payload)


def save_local_config(config: dict[str, object]) -> dict[str, object]:
    normalized = normalize_local_config(config)
    atomic_write_json(LOCAL_CONFIG_PATH, normalized)
    return normalized


def load_system_settings() -> dict[str, object]:
    config = load_local_config()
    payload = config.get(SYSTEM_KEY)
    return dict(payload) if isinstance(payload, dict) else dict(DEFAULT_LOCAL_CONFIG[SYSTEM_KEY])


def save_system_settings(*, max_recent_files: int) -> dict[str, object]:
    config = load_local_config()
    config[SYSTEM_KEY] = _normalize_system_settings(
        {
            "max_recent_files": max_recent_files,
        }
    )
    return save_local_config(config)


def load_ui_settings() -> dict[str, object]:
    config = load_local_config()
    payload = config.get(UI_SETTINGS_KEY)
    return dict(payload) if isinstance(payload, dict) else {}


def save_ui_settings(settings: dict[str, object]) -> dict[str, object]:
    config = load_local_config()
    config[UI_SETTINGS_KEY] = _normalize_ui_settings(settings)
    return save_local_config(config)


def load_user_preferences() -> dict[str, object]:
    config = load_local_config()
    payload = config.get(USER_PREFERENCES_KEY)
    return dict(payload) if isinstance(payload, dict) else {}


def save_user_preferences(preferences: dict[str, object]) -> dict[str, object]:
    config = load_local_config()
    config[USER_PREFERENCES_KEY] = _normalize_user_preferences(preferences)
    return save_local_config(config)


def load_recent_files() -> list[str]:
    config = load_local_config()
    system = config.get(SYSTEM_KEY)
    if not isinstance(system, dict):
        system = dict(DEFAULT_LOCAL_CONFIG[SYSTEM_KEY])
    max_recent = int(system.get("max_recent_files", DEFAULT_MAX_RECENT_FILES))
    return _normalize_recent_files(config.get(RECENT_FILES_KEY), max_recent)


def save_recent_files(recent_files: list[str]) -> dict[str, object]:
    config = load_local_config()
    system = config.get(SYSTEM_KEY)
    if not isinstance(system, dict):
        system = dict(DEFAULT_LOCAL_CONFIG[SYSTEM_KEY])
    max_recent = int(system.get("max_recent_files", DEFAULT_MAX_RECENT_FILES))
    config[RECENT_FILES_KEY] = _normalize_recent_files(recent_files, max_recent)
    return save_local_config(config)


def load_completion_stats() -> dict[str, object]:
    config = load_local_config()
    return _normalize_completion_stats(config.get(COMPLETION_STATS_KEY))


def save_completion_stats(stats: dict[str, object]) -> dict[str, object]:
    config = load_local_config()
    config[COMPLETION_STATS_KEY] = _normalize_completion_stats(stats)
    return save_local_config(config)


def reset_completion_stats() -> dict[str, object]:
    return save_completion_stats({"block_type_usage": {}, "option_value_usage": {}})


def record_block_type_usage(block_type: str, *, now_ts: float | None = None, increment: int = 1) -> dict[str, object]:
    stats = load_completion_stats()
    raw_usage = stats.get("block_type_usage")
    usage = dict(raw_usage) if isinstance(raw_usage, dict) else {}

    normalized_block_type = str(block_type or "").strip().lower()
    if not normalized_block_type or increment <= 0:
        return stats

    now = float(now_ts if now_ts is not None else time.time())
    current = usage.get(normalized_block_type, {})

    try:
        previous_count = max(0, int(current.get("count", 0)))
    except Exception:
        previous_count = 0
    try:
        previous_last_used = max(0.0, float(current.get("last_used", 0.0)))
    except Exception:
        previous_last_used = 0.0
    try:
        previous_score = max(0.0, float(current.get("score", 0.0)))
    except Exception:
        previous_score = 0.0

    decayed_score = _decay_value(previous_score, from_ts=previous_last_used, to_ts=now) if previous_last_used > 0 else previous_score
    usage[normalized_block_type] = {
        "count": previous_count + int(increment),
        "last_used": now,
        "score": decayed_score + float(increment),
    }

    return save_completion_stats({"block_type_usage": usage})


def record_block_type_usage_batch(increments: dict[str, int], *, now_ts: float | None = None) -> dict[str, object]:
    stats = load_completion_stats()
    raw_usage = stats.get("block_type_usage")
    usage = dict(raw_usage) if isinstance(raw_usage, dict) else {}
    now = float(now_ts if now_ts is not None else time.time())

    for raw_block_type, raw_increment in (increments or {}).items():
        normalized_block_type = str(raw_block_type or "").strip().lower()
        if not normalized_block_type:
            continue
        try:
            increment = int(raw_increment)
        except Exception:
            increment = 0
        if increment <= 0:
            continue

        current = usage.get(normalized_block_type, {})
        try:
            previous_count = max(0, int(current.get("count", 0)))
        except Exception:
            previous_count = 0
        try:
            previous_last_used = max(0.0, float(current.get("last_used", 0.0)))
        except Exception:
            previous_last_used = 0.0
        try:
            previous_score = max(0.0, float(current.get("score", 0.0)))
        except Exception:
            previous_score = 0.0

        decayed_score = (
            _decay_value(previous_score, from_ts=previous_last_used, to_ts=now)
            if previous_last_used > 0
            else previous_score
        )
        usage[normalized_block_type] = {
            "count": previous_count + increment,
            "last_used": now,
            "score": decayed_score + float(increment),
        }

    return save_completion_stats({"block_type_usage": usage})


def get_block_type_decay_scores(*, now_ts: float | None = None) -> dict[str, float]:
    stats = load_completion_stats()
    usage = stats.get("block_type_usage", {})
    if not isinstance(usage, dict):
        return {}

    now = float(now_ts if now_ts is not None else time.time())
    result: dict[str, float] = {}
    for raw_block_type, raw_entry in usage.items():
        block_type = str(raw_block_type or "").strip().lower()
        if not block_type or not isinstance(raw_entry, dict):
            continue

        try:
            score = max(0.0, float(raw_entry.get("score", 0.0)))
        except Exception:
            score = 0.0
        try:
            last_used = max(0.0, float(raw_entry.get("last_used", 0.0)))
        except Exception:
            last_used = 0.0

        if score <= 0.0:
            continue
        if last_used > 0.0:
            score = _decay_value(score, from_ts=last_used, to_ts=now)
        result[block_type] = score

    return result


def _option_value_usage_key(block_type: str, option_key: str, value: str) -> str:
    return f"{str(block_type or '').strip().lower()}|{str(option_key or '').strip().lower()}|{str(value or '').strip().lower()}"


def record_option_value_usage(
    block_type: str,
    option_key: str,
    value: str,
    *,
    now_ts: float | None = None,
    increment: int = 1,
) -> dict[str, object]:
    stats = load_completion_stats()
    raw_usage = stats.get("option_value_usage")
    usage = dict(raw_usage) if isinstance(raw_usage, dict) else {}

    block_type_norm = str(block_type or "").strip().lower()
    option_key_norm = str(option_key or "").strip().lower()
    value_norm = str(value or "").strip().lower()
    if not block_type_norm or not option_key_norm or not value_norm or increment <= 0:
        return stats

    usage_key = _option_value_usage_key(block_type_norm, option_key_norm, value_norm)

    now = float(now_ts if now_ts is not None else time.time())
    current = usage.get(usage_key, {})

    try:
        previous_count = max(0, int(current.get("count", 0)))
    except Exception:
        previous_count = 0
    try:
        previous_last_used = max(0.0, float(current.get("last_used", 0.0)))
    except Exception:
        previous_last_used = 0.0
    try:
        previous_score = max(0.0, float(current.get("score", 0.0)))
    except Exception:
        previous_score = 0.0

    decayed_score = _decay_value(previous_score, from_ts=previous_last_used, to_ts=now) if previous_last_used > 0 else previous_score
    usage[usage_key] = {
        "count": previous_count + int(increment),
        "last_used": now,
        "score": decayed_score + float(increment),
    }

    stats["option_value_usage"] = usage
    return save_completion_stats(stats)


def get_option_value_decay_scores(block_type: str, option_key: str, *, now_ts: float | None = None) -> dict[str, float]:
    stats = load_completion_stats()
    usage = stats.get("option_value_usage", {})
    if not isinstance(usage, dict):
        return {}

    block_type_norm = str(block_type or "").strip().lower()
    option_key_norm = str(option_key or "").strip().lower()
    if not block_type_norm or not option_key_norm:
        return {}

    prefix = f"{block_type_norm}|{option_key_norm}|"
    now = float(now_ts if now_ts is not None else time.time())
    result: dict[str, float] = {}

    for usage_key, raw_entry in usage.items():
        if not isinstance(usage_key, str) or not usage_key.startswith(prefix):
            continue
        if not isinstance(raw_entry, dict):
            continue

        value = usage_key[len(prefix):]
        if not value:
            continue

        try:
            score = max(0.0, float(raw_entry.get("score", 0.0)))
        except Exception:
            score = 0.0
        try:
            last_used = max(0.0, float(raw_entry.get("last_used", 0.0)))
        except Exception:
            last_used = 0.0

        if score <= 0.0:
            continue
        if last_used > 0.0:
            score = _decay_value(score, from_ts=last_used, to_ts=now)
        result[value] = score

    return result


def add_recent_file(recent_files: list[str], path_text: str, max_recent_files: int) -> list[str]:
    """Insert a recent-file entry at the front, remove duplicates, and cap list size."""
    cleaned = [item for item in recent_files if item != path_text]
    cleaned.insert(0, path_text)
    return cleaned[:max_recent_files]


def remove_recent_file(recent_files: list[str], path_text: str) -> list[str]:
    """Remove a recent-file entry from the in-memory list."""
    return [item for item in recent_files if item != path_text]


def _load_legacy_payload(path: Path) -> object:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def migrate_legacy_config(delete_legacy_files: bool = True) -> dict[str, object]:
    config = load_local_config()
    changed = False

    ui_payload = _load_legacy_payload(LEGACY_UI_SETTINGS_PATH)
    if ui_payload is None:
        ui_payload = _load_legacy_payload(ROOT_LEGACY_UI_SETTINGS_PATH)
    if isinstance(ui_payload, dict):
        merged_ui = dict(ui_payload)
        current_ui = config.get(UI_SETTINGS_KEY)
        if isinstance(current_ui, dict):
            merged_ui.update(current_ui)
        config[UI_SETTINGS_KEY] = merged_ui
        changed = True

    recent_payload = _load_legacy_payload(LEGACY_RECENT_FILES_PATH)
    if recent_payload is None:
        recent_payload = _load_legacy_payload(ROOT_LEGACY_RECENT_FILES_PATH)
    if isinstance(recent_payload, dict):
        legacy_recent = recent_payload.get("recent_files")
    elif isinstance(recent_payload, list):
        legacy_recent = recent_payload
    else:
        legacy_recent = None

    if isinstance(legacy_recent, list):
        raw_recent = config.get(RECENT_FILES_KEY)
        current_recent = list(raw_recent) if isinstance(raw_recent, list) else []
        if not current_recent:
            config[RECENT_FILES_KEY] = legacy_recent
            changed = True

    normalized = save_local_config(config) if changed else config

    if delete_legacy_files:
        for path in (
            LEGACY_RECENT_FILES_PATH,
            LEGACY_UI_SETTINGS_PATH,
            ROOT_LEGACY_RECENT_FILES_PATH,
            ROOT_LEGACY_UI_SETTINGS_PATH,
        ):
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass

    return normalize_local_config(normalized)
