"""Vorwärtsschritte der Zustandsmaschine; jeder Schritt ist idempotent und prüft den Plattenzustand.

Jede `ensure_*`-Funktion bringt einen Eintrag vom vorigen in den nächsten
Zustand -- ob frischer Lauf oder Fortsetzen nach einem Abbruch. Sie
vergleicht dazu den **tatsächlichen** Plattenzustand mit den erwarteten
Zuständen vor bzw. nach dem Schritt (Recovery-Tabelle im Plan 2.4) und wirft
`ConflictError`, wenn keiner passt. Entscheidungen hängen immer an Hash
**und** Identität (Inode/File-ID); ist keine Identität verfügbar, wird bei
mehrdeutigen Zuständen `CONFLICT` gemeldet statt nach Hash zu entscheiden.
"""

from __future__ import annotations

import os
from pathlib import Path

from .context import (
    BACKED_UP,
    COMMITTED,
    SIDE_STATE_APPLIED,
    SOURCE_QUARANTINED,
    SOURCE_REMOVED,
    SOURCE_RO_CLEARED,
    TARGET_ATTRS_APPLIED,
    TARGET_VERIFIED,
    TARGET_WRITTEN,
    ConflictError,
    ItemContext,
    SkipItem,
)
from .fs_ops import (
    ChangedDuringRead,
    FileIdentity,
    identity_of,
    is_readonly,
    read_with_identity,
    rename_no_replace,
    set_creation_time,
    sha256_hex as _sha,
    set_readonly,
    set_times,
    set_windows_attributes,
    write_new_file,
)
from .rewrite import decode_utf8, encode_utf8, rewrite_for_target


def rewritten_bytes(ctx: ItemContext) -> bytes:
    """Deterministischer Rewrite aus dem verifizierten Backup (Plan-Bytes)."""
    data = ctx.backup.read_bytes()
    result = encode_utf8(rewrite_for_target(decode_utf8(data), ctx.entry.target_type))
    if _sha(result) != ctx.entry.rewrite_sha256:
        raise SkipItem("plan_invalid: Rewrite-Hash passt nicht mehr zur aktuellen Migrationslogik")
    return result


def _matches_plan(identity: FileIdentity, plan: FileIdentity) -> bool:
    if not plan.has_inode():
        return (identity.size, identity.sha256) == (plan.size, plan.sha256)
    return (identity.size, identity.sha256, identity.dev, identity.ino) == (plan.size, plan.sha256, plan.dev, plan.ino)


def ensure_backed_up(ctx: ItemContext) -> None:
    """Backup = Plan-Bytes (Hash der gelesenen Bytes und neu gelesenes Backup = Plan-Hash)."""
    if ctx.reached(BACKED_UP):
        return
    plan = ctx.plan_identity
    if ctx.backup.exists():
        ctx.backup.unlink()  # eigener, unvollständiger Versuch im Run-Ordner
    try:
        data, identity = read_with_identity(ctx.src)
    except (FileNotFoundError, ChangedDuringRead) as error:
        raise SkipItem(f"changed_since_plan: {error}") from error
    if not _matches_plan(identity, plan) or identity.mtime_ns != plan.mtime_ns:
        raise SkipItem("changed_since_plan: Quelle weicht vom Plan-Fingerprint ab")
    ctx.backup.parent.mkdir(parents=True, exist_ok=True)
    write_new_file(ctx.backup, data)
    if identity_of(ctx.backup).sha256 != plan.sha256:
        ctx.backup.unlink()
        raise SkipItem("changed_since_plan: Backup stimmt nicht mit dem Plan-Hash ueberein")
    ctx.mark(BACKED_UP, backup_sha256=plan.sha256)


def _target_ok(ctx: ItemContext, data_sha: str) -> bool:
    """Ziel existiert mit erwartetem Rewrite-Hash und der journalierten Identität."""
    recorded = ctx.recorded("target_identity")
    if not ctx.dst.exists() or recorded is None:
        return False
    identity = identity_of(ctx.dst)
    expected = FileIdentity.from_dict(recorded)
    if not expected.has_inode():
        return False
    return identity.sha256 == data_sha and (identity.dev, identity.ino) == (expected.dev, expected.ino)


def ensure_target_written(ctx: ItemContext) -> None:
    """Temp exklusiv schreiben, dann `rename_no_replace` aufs Ziel (nie überschreiben)."""
    if ctx.reached(TARGET_WRITTEN):
        return
    data = rewritten_bytes(ctx)
    expected_sha = _sha(data)
    tmp_identity = ctx.recorded("tmp_identity")
    if ctx.dst.exists():
        if ctx.tmp.exists() and tmp_identity and _same_inode_ok(ctx.tmp, ctx.dst, expected_sha):
            os.unlink(ctx.tmp)  # POSIX-Zwischenzustand nach link: beide Namen, ein Inode
        elif not (tmp_identity and _identity_equals(ctx.dst, tmp_identity, expected_sha)):
            raise ConflictError("target_exists", f"Ziel existiert bereits: {ctx.dst}")
        ctx.mark(TARGET_WRITTEN, target_identity=tmp_identity)
        return
    if ctx.tmp.exists():
        content = ctx.tmp.read_bytes()
        if not data.startswith(content):
            raise ConflictError("foreign_temp", f"Unerwartete Temp-Datei: {ctx.tmp}")
        os.unlink(ctx.tmp)  # eigener, abgebrochener Schreibversuch (Präfix der erwarteten Bytes)
    ctx.intent("write_target")
    identity = write_new_file(ctx.tmp, data)
    ctx.intent("rename_target", tmp_identity=identity.as_dict())
    try:
        rename_no_replace(ctx.tmp, ctx.dst)
    except FileExistsError as error:
        os.unlink(ctx.tmp)
        raise ConflictError("target_exists", f"Ziel ist nach dem Plan entstanden: {ctx.dst}") from error
    ctx.mark(TARGET_WRITTEN, target_identity=identity.as_dict())


def _identity_equals(path: Path, identity_dict: dict, sha: str) -> bool:
    expected = FileIdentity.from_dict(identity_dict)
    actual = identity_of(path)
    return expected.has_inode() and actual.sha256 == sha and (actual.dev, actual.ino) == (expected.dev, expected.ino)


def _same_inode_ok(path_a: Path, path_b: Path, sha: str) -> bool:
    stat_a, stat_b = os.stat(path_a), os.stat(path_b)
    return stat_a.st_ino != 0 and (stat_a.st_dev, stat_a.st_ino) == (stat_b.st_dev, stat_b.st_ino) and identity_of(path_b).sha256 == sha


def ensure_target_verified(ctx: ItemContext) -> None:
    if ctx.reached(TARGET_VERIFIED):
        return
    if not _target_ok(ctx, ctx.entry.rewrite_sha256):
        raise ConflictError("target_changed", f"Ziel entspricht nicht dem geschriebenen Stand: {ctx.dst}")
    ctx.mark(TARGET_VERIFIED)


def ensure_target_attributes(ctx: ItemContext) -> None:
    """Überträgt Zeiten/Attribute explizit; jeder Fehlschlag ist nur eine Warnung."""
    if ctx.reached(TARGET_ATTRS_APPLIED):
        return
    entry = ctx.entry
    ctx.intent("apply_attributes", readonly=entry.readonly, attributes=entry.attributes)
    for label, action in (
        ("atime/mtime", lambda: set_times(ctx.dst, entry.atime_ns, entry.mtime_ns)),
        ("Hidden/Archive/System", lambda: _require(set_windows_attributes(ctx.dst, entry.attributes))),
        ("Erstellungsdatum", lambda: _require(set_creation_time(ctx.dst, entry.birthtime_ns))),
        ("Schreibschutz", lambda: set_readonly(ctx.dst, True) if entry.readonly else None),
    ):
        try:
            action()
        except Exception as error:  # Nutzerentscheidung: Metadaten-Fehlschlag = Warnung
            ctx.warnings.append(f"{ctx.label()}: {label} nicht uebertragen ({error})")
    if entry.birthtime_ns is None:
        ctx.warnings.append(f"{ctx.label()}: kein Erstellungsdatum verfuegbar, nicht uebertragen")
    ctx.mark(TARGET_ATTRS_APPLIED)


def _require(ok: bool) -> None:
    if not ok:
        raise OSError("vom Betriebssystem abgelehnt")


def _check_target_before_destroying_source(ctx: ItemContext) -> None:
    """R6-2: Vor quellzerstörenden Schritten muss das Ziel unverändert existieren."""
    if not _target_ok(ctx, ctx.entry.rewrite_sha256):
        raise ConflictError("target_changed", f"Ziel fehlt oder wurde veraendert: {ctx.dst}")


def ensure_source_quarantined(ctx: ItemContext) -> None:
    """Quelle exklusiv zur Quarantäne umbenennen; danach Hash und Identität prüfen."""
    if ctx.reached(SOURCE_QUARANTINED):
        return
    _check_target_before_destroying_source(ctx)
    plan = ctx.plan_identity
    src_exists, quarantine_exists = ctx.src.exists(), ctx.quarantine.exists()
    if src_exists and quarantine_exists:
        if not (plan.has_inode() and _same_inode_ok(ctx.src, ctx.quarantine, plan.sha256)):
            raise ConflictError("quarantine_conflict", f"Quelle und Quarantaene unterschiedlich: {ctx.src}")
        os.unlink(ctx.src)  # POSIX-Zwischenzustand
    elif src_exists:
        if not _matches_plan(identity_of(ctx.src), plan):
            raise SkipItem("changed_since_plan: Quelle vor der Quarantaene veraendert")
        ctx.intent("quarantine")
        rename_no_replace(ctx.src, ctx.quarantine)
        if not _matches_plan(identity_of(ctx.quarantine), plan):
            rename_no_replace(ctx.quarantine, ctx.src)
            raise ConflictError("source_changed", f"Quelle wurde waehrend der Quarantaene veraendert: {ctx.src}")
    elif not (quarantine_exists and _matches_plan(identity_of(ctx.quarantine), plan)):
        raise ConflictError("source_missing", f"Quelle und Quarantaene fehlen oder sind fremd: {ctx.src}")
    ctx.mark(SOURCE_QUARANTINED)


def ensure_source_readonly_cleared(ctx: ItemContext) -> None:
    """Eigener Zustand: Original-Schreibschutz journalieren, dann entfernen (R3-2.4)."""
    if ctx.reached(SOURCE_RO_CLEARED):
        return
    original = ctx.recorded("original_readonly")
    if original is None:
        original = is_readonly(ctx.quarantine)
        ctx.intent("clear_readonly", original_readonly=original)
    if is_readonly(ctx.quarantine):
        set_readonly(ctx.quarantine, False)
    ctx.mark(SOURCE_RO_CLEARED, original_readonly=original)


def ensure_source_removed(ctx: ItemContext) -> None:
    """Unmittelbar vor dem irreversiblen Löschen erneut die Zielprüfung (R6-2)."""
    if ctx.reached(SOURCE_REMOVED):
        return
    if ctx.quarantine.exists():
        _check_target_before_destroying_source(ctx)
        if not _matches_plan(identity_of(ctx.quarantine), ctx.plan_identity):
            raise ConflictError("source_changed", f"Quarantaenedatei veraendert: {ctx.quarantine}")
        ctx.intent("remove_source")
        os.unlink(ctx.quarantine)
    elif ctx.src.exists():
        raise ConflictError("source_reappeared", f"Unter dem Originalnamen liegt wieder eine Datei: {ctx.src}")
    ctx.mark(SOURCE_REMOVED)


def ensure_committed(ctx: ItemContext) -> None:
    if not ctx.reached(COMMITTED):
        ctx.mark(COMMITTED)


def ensure_side_state_applied(ctx: ItemContext, store) -> None:
    """Delta `alt → neu` für genau dieses Item (nie ein Snapshot)."""
    if ctx.reached(SIDE_STATE_APPLIED):
        return
    ctx.intent("side_state", old=str(ctx.src), new=str(ctx.dst))
    if store is not None:
        store.apply_rename(str(ctx.src), str(ctx.dst))
    ctx.mark(SIDE_STATE_APPLIED)


FORWARD_STEPS = (
    ensure_backed_up,
    ensure_target_written,
    ensure_target_verified,
    ensure_target_attributes,
    ensure_source_quarantined,
    ensure_source_readonly_cleared,
    ensure_source_removed,
    ensure_committed,
)
