"""Zentraler lokaler Config-Store fuer Blattwerk."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile

DEFAULT_HISTORY_ROOT_NAME = "7thCloud"
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


DEFAULT_LOCAL_CONFIG = {
    "version": 1,
    SYSTEM_KEY: {
        "history_root_name": DEFAULT_HISTORY_ROOT_NAME,
        "max_recent_files": DEFAULT_MAX_RECENT_FILES,
    },
    UI_SETTINGS_KEY: {},
    RECENT_FILES_KEY: [],
}


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=str(path.parent), suffix=".tmp") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2))
        temp_path = Path(handle.name)
    temp_path.replace(path)


def _normalize_system_settings(raw: object) -> dict[str, object]:
    normalized = deepcopy(DEFAULT_LOCAL_CONFIG[SYSTEM_KEY])
    if not isinstance(raw, dict):
        return normalized

    history_root_name = str(raw.get("history_root_name", "")).strip()
    if history_root_name:
        normalized["history_root_name"] = history_root_name

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


def normalize_local_config(raw: object) -> dict[str, object]:
    base = deepcopy(DEFAULT_LOCAL_CONFIG)
    if not isinstance(raw, dict):
        return base

    system_settings = _normalize_system_settings(raw.get(SYSTEM_KEY))
    max_recent_files = int(system_settings["max_recent_files"])

    base[SYSTEM_KEY] = system_settings
    base[UI_SETTINGS_KEY] = _normalize_ui_settings(raw.get(UI_SETTINGS_KEY))
    base[RECENT_FILES_KEY] = _normalize_recent_files(raw.get(RECENT_FILES_KEY), max_recent_files)
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
    _atomic_write_json(LOCAL_CONFIG_PATH, normalized)
    return normalized


def load_system_settings() -> dict[str, object]:
    config = load_local_config()
    return dict(config[SYSTEM_KEY])


def save_system_settings(*, history_root_name: str, max_recent_files: int) -> dict[str, object]:
    config = load_local_config()
    config[SYSTEM_KEY] = _normalize_system_settings(
        {
            "history_root_name": history_root_name,
            "max_recent_files": max_recent_files,
        }
    )
    return save_local_config(config)


def load_ui_settings() -> dict[str, object]:
    config = load_local_config()
    return dict(config[UI_SETTINGS_KEY])


def save_ui_settings(settings: dict[str, object]) -> dict[str, object]:
    config = load_local_config()
    config[UI_SETTINGS_KEY] = _normalize_ui_settings(settings)
    return save_local_config(config)


def load_recent_files() -> list[str]:
    config = load_local_config()
    system = config[SYSTEM_KEY]
    max_recent = int(system.get("max_recent_files", DEFAULT_MAX_RECENT_FILES))
    return _normalize_recent_files(config[RECENT_FILES_KEY], max_recent)


def save_recent_files(recent_files: list[str]) -> dict[str, object]:
    config = load_local_config()
    system = config[SYSTEM_KEY]
    max_recent = int(system.get("max_recent_files", DEFAULT_MAX_RECENT_FILES))
    config[RECENT_FILES_KEY] = _normalize_recent_files(recent_files, max_recent)
    return save_local_config(config)


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
        merged_ui.update(dict(config.get(UI_SETTINGS_KEY, {})))
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
        current_recent = list(config.get(RECENT_FILES_KEY, []))
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
