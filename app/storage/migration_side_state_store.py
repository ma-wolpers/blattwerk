"""Speicher-Adapter für den Begleitzustand der Dateiendungs-Migration.

Implementiert strukturell den Port `app.core.migration.context.SideStateStore`
(der Kern importiert `app/storage` nie). Jedes Delta liest die lokale Config
**frisch**, ersetzt nur Einträge, die kanonisch (`canonical_path_key`) genau
dem alten Pfad entsprechen, und schreibt atomar zurück -- nie einen Snapshot.
So bleiben Einträge anderer Dateien und spätere Änderungen der Nutzerin
unberührt, und wiederholtes Anwenden ist idempotent.
"""

from __future__ import annotations

from pathlib import Path

from ..core.migration.side_state import canonical_path_key, rename_entries
from .history_paths_adapter import normalize_recent_path
from .local_config_store import (
    ACKNOWLEDGED_WARNINGS_KEY,
    RECENT_FILES_KEY,
    load_local_config,
    save_local_config,
)


class LocalConfigSideStateStore:
    """Wendet `alt → neu` auf Recent-Files und Keys quittierter Warnungen an."""

    def apply_rename(self, old: str, new: str) -> None:
        config = load_local_config()
        to_storage = lambda path: normalize_recent_path(Path(path))  # noqa: E731
        recent = list(config.get(RECENT_FILES_KEY) or [])
        config[RECENT_FILES_KEY], recent_changed = rename_entries(recent, old, new, to_storage=to_storage)

        acknowledged = dict(config.get(ACKNOWLEDGED_WARNINGS_KEY) or {})
        old_key = canonical_path_key(old)
        ack_changed = False
        for key in list(acknowledged):
            if canonical_path_key(key) == old_key:
                acknowledged[to_storage(new)] = acknowledged.pop(key)
                ack_changed = True
        config[ACKNOWLEDGED_WARNINGS_KEY] = acknowledged

        if recent_changed or ack_changed:
            save_local_config(config)
