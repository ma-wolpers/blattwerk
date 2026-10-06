"""Gegenseitiger Ausschluss zwischen laufender Blattwerk-App und Migration (Plan 2.6).

Befund: Der Single-Instance-Port (`single_instance.py`) ist kein Lock -- ein
App-Start wartet höchstens 30 s auf eine Bestätigung und startet danach
trotzdem. Deshalb gibt es hier echte, absturzsichere OS-Byte-Locks
(`msvcrt.locking` bzw. `fcntl.flock`; das Betriebssystem gibt sie beim
Prozessende frei).

Protokoll ("erst anmelden, dann die andere Seite prüfen"):

* **App:** `locks/app-<pid>.lock` sperren und für die Lebensdauer halten,
  **dann** prüfen, ob `migration.lock` belegt ist; falls ja, eigene Sperre
  freigeben und nicht starten.
* **Migration (CLI/GUI-Lauf):** `migration.lock` für die gesamte Laufzeit
  halten, **dann** alle `app-*.lock` prüfen (die eigene App-Instanz bei der
  GUI-Migration ausgenommen); belegt → abbrechen, verwaist → löschen.

Weil jede Seite sich zuerst anmeldet, sieht mindestens eine die andere; es
laufen nie beide gleichzeitig (schlimmstenfalls brechen beide ab).
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

MIGRATION_LOCK_NAME = "migration.lock"

_current_app_lock = None


def current_app_lock() -> "ProcessLock | None":
    """Die Sperre dieser App-Instanz (für die GUI-Migration), falls registriert."""
    return _current_app_lock


def default_lock_dir() -> Path:
    """Gemeinsamer Lock-Ordner von App und CLI (gleicher Code-Stand, gleicher Ordner)."""
    return Path(__file__).resolve().parents[1] / "storage" / ".state" / "locks"


@dataclass
class ProcessLock:
    """Gehaltene Sperre; `release()` gibt sie frei (idempotent)."""

    path: Path
    handle: object

    def release(self) -> None:
        if self.handle is None:
            return
        try:
            _unlock(self.handle)
        finally:
            self.handle.close()
            self.handle = None


def _try_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "a+b")
    try:
        if sys.platform == "win32":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def _unlock(handle) -> None:
    if sys.platform == "win32":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _is_locked_by_other(path: Path) -> bool:
    handle = _try_lock(path)
    if handle is None:
        return True
    _unlock(handle)
    handle.close()
    return False


def register_app_instance(lock_dir: Path) -> ProcessLock | None:
    """App-Start: eigene Sperre halten, dann Migration prüfen.

    Returns:
        Die gehaltene Sperre oder ``None``, wenn gerade eine Migration läuft
        (dann darf die App nicht starten).
    """
    path = Path(lock_dir) / f"app-{os.getpid()}.lock"
    handle = _try_lock(path)
    if handle is None:
        return None
    lock = ProcessLock(path, handle)
    if _is_locked_by_other(Path(lock_dir) / MIGRATION_LOCK_NAME):
        lock.release()
        _remove_quietly(path)
        return None
    global _current_app_lock
    _current_app_lock = lock
    return lock


def acquire_migration_lock(lock_dir: Path, *, own_app_lock: ProcessLock | None = None) -> ProcessLock | None:
    """Migration: `migration.lock` halten, dann laufende App-Instanzen prüfen.

    Args:
        own_app_lock: Bei der GUI-Migration die Sperre der eigenen App-Instanz,
            die nicht als „fremde laufende App“ zählt.

    Returns:
        Die gehaltene Sperre oder ``None`` (andere Migration oder fremde App läuft).
    """
    path = Path(lock_dir) / MIGRATION_LOCK_NAME
    handle = _try_lock(path)
    if handle is None:
        return None
    lock = ProcessLock(path, handle)
    own = own_app_lock.path.resolve() if own_app_lock is not None else None
    for app_lock in sorted(Path(lock_dir).glob("app-*.lock")):
        if own is not None and app_lock.resolve() == own:
            continue
        if _is_locked_by_other(app_lock):
            lock.release()
            return None
        _remove_quietly(app_lock)  # verwaist (Prozess beendet)
    return lock


def _remove_quietly(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass
