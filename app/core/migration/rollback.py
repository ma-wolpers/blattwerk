"""Rückwärtsrichtung der Zustandsmaschine: Rollback abgebrochener Einträge und Undo.

Reihenfolge pro Eintrag (jeweils mit Zustandsprüfung vor jedem destruktiven Schritt):

1. Begleitzustand: inverses Delta nur, wenn `SIDE_STATE_APPLIED` erreicht war.
2. Quelle wiederherstellen -- aus der Quarantäne (`rename_no_replace`, Original-
   Schreibschutz aus dem Journal, Plan-`atime`) oder, wenn sie schon gelöscht
   war, aus dem Backup (Temp + `rename_no_replace`, Attribute/Zeiten aus dem Plan).
3. Ziel entfernen -- nur, wenn es noch genau dem geschriebenen Stand entspricht
   (Hash **und** Identität). Wurde es verändert: Rückfrage
   [b]ehalten / [p]arallel wiederherstellen / [a]bbrechen.
4. Eigene Temp-Datei aufräumen (nur Präfix der erwarteten Bytes).

Backups im Run-Ordner bleiben immer erhalten.
"""

from __future__ import annotations

import os
import time

from .context import (
    ROLLED_BACK,
    SIDE_STATE_APPLIED,
    SIDE_STATE_REVERTED,
    SOURCE_QUARANTINED,
    SOURCE_REMOVED,
    TARGET_WRITTEN,
    ConflictError,
    ItemContext,
)
from .forward import _identity_equals, _same_inode_ok, rewritten_bytes
from .fs_ops import (
    identity_of,
    rename_no_replace,
    set_creation_time,
    set_readonly,
    set_times,
    set_windows_attributes,
    write_new_file,
)

CHOICE_KEEP = "behalten"
CHOICE_PARALLEL = "parallel"
CHOICE_ABORT = "abbrechen"


class AbortRequested(Exception):
    """Die Nutzerin hat bei einer Rückfrage „abbrechen“ gewählt."""


def rollback_item(ctx: ItemContext, store, resolver) -> str:
    """Nimmt einen Eintrag zurück; liefert `ROLLED_BACK` oder `"behalten"`.

    Der Begleitzustand wird nur invertiert, wenn der Eintrag tatsächlich
    zurückgerollt wird -- bei „behalten“/„parallel“ bleibt der neue Pfad (R6-1).
    """
    target_unchanged = _target_unchanged(ctx)
    if ctx.reached(TARGET_WRITTEN) and ctx.dst.exists() and not target_unchanged:
        choice = resolver.resolve(
            "target_modified", ctx.label(), (CHOICE_KEEP, CHOICE_PARALLEL, CHOICE_ABORT)
        )
        if choice == CHOICE_ABORT:
            raise AbortRequested(ctx.label())
        if ctx.quarantine.exists():
            # Laufender Vorwärtslauf: das Original liegt noch in der Quarantäne und
            # kommt unter seinen Namen zurück (nie überschreibend), egal wie entschieden wurde.
            _restore_source(ctx, parallel=False)
            ctx.mark("KEPT", restored_from_quarantine=True, backup=str(ctx.backup))
            return CHOICE_KEEP
        if choice == CHOICE_KEEP:
            ctx.mark("KEPT", backup=str(ctx.backup))
            return CHOICE_KEEP
        _restore_source(ctx, parallel=True)
        ctx.mark("KEPT", restored_parallel=True, backup=str(ctx.backup))
        return CHOICE_KEEP

    _restore_source(ctx, parallel=False)
    if target_unchanged:
        if ctx.entry.readonly:
            set_readonly(ctx.dst, False)
        ctx.intent("remove_target")
        os.unlink(ctx.dst)
    _cleanup_temp(ctx)
    if ctx.reached(SIDE_STATE_APPLIED) and not ctx.reached(SIDE_STATE_REVERTED):
        ctx.intent("side_state_revert", old=str(ctx.src), new=str(ctx.dst))
        if store is not None:
            store.apply_rename(str(ctx.dst), str(ctx.src))
        ctx.mark(SIDE_STATE_REVERTED)
    ctx.mark(ROLLED_BACK)
    return ROLLED_BACK


def _target_unchanged(ctx: ItemContext) -> bool:
    """Ziel = geschriebener Stand (Hash + Identität); vor `TARGET_WRITTEN` gilt die Temp-Identität."""
    identity = ctx.recorded("target_identity") or ctx.recorded("tmp_identity")
    return bool(identity) and ctx.dst.exists() and _identity_equals(ctx.dst, identity, ctx.entry.rewrite_sha256)


def _restore_source(ctx: ItemContext, *, parallel: bool) -> None:
    """Stellt das Original wieder her (aus Quarantäne bzw. Backup), nie überschreibend."""
    if not parallel and ctx.src.exists() and not ctx.quarantine.exists():
        return  # Quelle ist (noch) da: nichts zu tun
    if ctx.quarantine.exists() and not parallel:
        if ctx.src.exists():
            if _same_inode_ok(ctx.src, ctx.quarantine, ctx.plan_identity.sha256):
                os.unlink(ctx.quarantine)  # POSIX-Zwischenzustand: beide Namen, ein Inode
                return
            raise ConflictError("source_reappeared", f"Unter dem Originalnamen liegt eine Datei: {ctx.src}")
        ctx.intent("restore_from_quarantine")
        rename_no_replace(ctx.quarantine, ctx.src)
        original_readonly = ctx.recorded("original_readonly")
        if original_readonly:
            set_readonly(ctx.src, True)
        _restore_atime(ctx, ctx.src)
        return
    if not (ctx.reached(SOURCE_REMOVED) or ctx.reached(SOURCE_QUARANTINED) or parallel):
        return
    destination = ctx.src if not parallel else ctx.src.with_name(
        f"{ctx.src.stem}.restored-{time.strftime('%Y%m%d-%H%M%S')}.md"
    )
    if not ctx.backup.exists() or identity_of(ctx.backup).sha256 != ctx.plan_identity.sha256:
        raise ConflictError("backup_missing", f"Backup fehlt oder ist beschaedigt: {ctx.backup}")
    temp = destination.with_name(f".{destination.name}.bw-restore-{ctx.run_id}")
    if temp.exists():
        os.unlink(temp)
    ctx.intent("restore_from_backup", destination=str(destination))
    write_new_file(temp, ctx.backup.read_bytes())
    try:
        rename_no_replace(temp, destination)
    except FileExistsError as error:
        os.unlink(temp)
        raise ConflictError("source_reappeared", f"Wiederherstellungsziel existiert: {destination}") from error
    _restore_metadata(ctx, destination)


def _restore_atime(ctx: ItemContext, path) -> None:
    try:
        set_times(path, ctx.entry.atime_ns, os.stat(path).st_mtime_ns)
    except OSError as error:
        ctx.warnings.append(f"{ctx.label()}: atime nicht wiederhergestellt ({error})")


def _restore_metadata(ctx: ItemContext, path) -> None:
    entry = ctx.entry
    for label, action in (
        ("atime/mtime", lambda: set_times(path, entry.atime_ns, entry.mtime_ns)),
        ("Attribute", lambda: set_windows_attributes(path, entry.attributes)),
        ("Erstellungsdatum", lambda: set_creation_time(path, entry.birthtime_ns)),
        ("Schreibschutz", lambda: set_readonly(path, True) if entry.readonly else None),
    ):
        try:
            action()
        except Exception as error:
            ctx.warnings.append(f"{ctx.label()}: {label} nicht wiederhergestellt ({error})")


def _cleanup_temp(ctx: ItemContext) -> None:
    """Löscht die eigene Temp-Datei nur, wenn ihr Inhalt ein Präfix der erwarteten Bytes ist."""
    if not ctx.tmp.exists():
        return
    try:
        expected = rewritten_bytes(ctx)
    except Exception:
        expected = None
    if expected is not None and expected.startswith(ctx.tmp.read_bytes()):
        os.unlink(ctx.tmp)
    else:
        ctx.warnings.append(f"{ctx.label()}: Temp-Datei nicht eindeutig zuzuordnen, bleibt liegen: {ctx.tmp}")
