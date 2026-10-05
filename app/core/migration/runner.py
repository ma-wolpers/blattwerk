"""Ablaufsteuerung der Migration: Schreiben, Fortsetzen und Undo eines Plans.

Idempotenz (Nutzerentscheidung „Vorschlag A“):

1. `resume` auf einem abgeschlossenen Lauf → No-op.
2. `execute` mit einem bereits verbrauchten Plan (Journal existiert) → `PlanConsumed`.
3. Ein neuer Dry-Run nach der Migration sieht migrierte Dateien nicht mehr
   (sie sind keine `.md` mehr); nach einem Undo erscheinen sie wieder.

Vor jedem Eintrag laufen Laufzeit-Sicherheitsprüfungen (Plan 2.4), obwohl der
Plan festgeschrieben ist: Pfade im Root, keine neuen Reparse Points, Zielname
nach der Namensregel, Zieltyp = Neu-Klassifikation, Rewrite-Hash.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .classify import STATUS_SAFE, classify
from .context import (
    COMMITTED,
    CONFLICT,
    ROLLED_BACK,
    SIDE_STATE_APPLIED,
    SKIPPED,
    TERMINAL_STATES,
    ConflictError,
    ItemContext,
    SkipItem,
)
from .forward import FORWARD_STEPS, ensure_side_state_applied
from .fs_ops import is_link_or_reparse
from .journal import Journal, read_journal
from .plan import FORCEABLE_STATUSES, MigrationPlan, PlanInvalid, target_name
from .rewrite import decode_utf8
from .rollback import CHOICE_ABORT, AbortRequested, rollback_item

CHOICE_SKIP = "ueberspringen"
JOURNAL_NAME = "journal.jsonl"
PLAN_NAME = "plan.json"


class PlanConsumed(Exception):
    """Der Plan wurde bereits ausgeführt (Journal vorhanden)."""


@dataclass
class RunResult:
    """Zusammenfassung eines Laufs (nur Pfade, Status, Gründe -- keine Inhalte)."""

    run_dir: Path
    committed: list[str] = field(default_factory=list)
    rolled_back: list[str] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    conflicts: list[tuple[str, str]] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    aborted: bool = False
    already_finished: bool = False


def default_runs_dir() -> Path:
    """Feste Ablage für Pläne, Journale und Backups (lokale Platte, nicht der Sync-Ordner)."""
    base = os.environ.get("APPDATA") or str(Path.home() / ".local" / "share")
    return Path(base) / "Blattwerk" / "migrations"


def new_run_dir(base_dir: Path) -> Path:
    """Legt einen neuen Run-Ordner an (`<zeitstempel>-<kurz-id>`)."""
    run_dir = Path(base_dir) / f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_plan(plan: MigrationPlan, run_dir: Path) -> Path:
    path = Path(run_dir) / PLAN_NAME
    path.write_text(plan.to_json(), encoding="utf-8")
    return path


def load_plan(run_dir: Path) -> MigrationPlan:
    return MigrationPlan.from_json((Path(run_dir) / PLAN_NAME).read_text(encoding="utf-8"))


def runtime_check(plan: MigrationPlan, entry) -> None:
    """Sicherheitsprüfungen vor jedem Eintrag; wirft `SkipItem` bei Abweichung."""
    root = Path(plan.root).resolve()
    src = (root / entry.source).resolve()
    dst = (root / entry.target).resolve()
    for path in (src, dst):
        if root not in path.parents:
            raise SkipItem("plan_invalid: Pfad ausserhalb des Plan-Roots")
    parent = src.parent
    while parent != root:
        if is_link_or_reparse(parent):
            raise SkipItem("plan_invalid: Elternordner ist inzwischen ein Symlink/Reparse Point")
        parent = parent.parent
    if dst.parent != src.parent or dst.name != target_name(src.name, entry.target_type):
        raise SkipItem("plan_invalid: Zielpfad folgt nicht der Namensregel")
    if not src.exists():
        return  # Fortsetzen nach der Quarantäne: Prüfung erfolgt über das Journal
    if is_link_or_reparse(src):
        raise SkipItem("plan_invalid: Quelle ist inzwischen ein Symlink/Reparse Point")
    try:
        result = classify(src.name, decode_utf8(src.read_bytes()))
    except UnicodeDecodeError as error:
        raise SkipItem("changed_since_plan: nicht mehr UTF-8") from error
    if getattr(entry, "forced", False):
        if result.status not in FORCEABLE_STATUSES:
            raise SkipItem("plan_invalid: vorgegebener Typ, aber die Datei ist nicht (mehr) als Blattwerk erkennbar")
    elif result.status != STATUS_SAFE or result.target_type != entry.target_type:
        raise SkipItem("plan_invalid: Zieltyp entspricht nicht der aktuellen Klassifikation")


def _context(plan, entry, run_dir, journal, records) -> ItemContext:
    return ItemContext(entry, Path(plan.root), Path(run_dir), Path(run_dir).name, journal, records)


def _drive_item(ctx: ItemContext, plan, store, resolver, result: RunResult, *, check: bool) -> bool:
    """Bringt einen Eintrag vorwärts; liefert ``False``, wenn der Lauf abgebrochen werden soll."""
    try:
        if check and ctx.last_state() is None:
            runtime_check(plan, ctx.entry)
        for step in FORWARD_STEPS:
            step(ctx)
        ensure_side_state_applied(ctx, store)
        result.committed.append(ctx.label())
        return True
    except SkipItem as skip:
        return _rollback_after_failure(ctx, store, resolver, result, skip.reason, skipped=True)
    except ConflictError as conflict:
        choice = resolver.resolve(conflict.kind, ctx.label(), (CHOICE_SKIP, CHOICE_ABORT))
        keep_going = _rollback_after_failure(ctx, store, resolver, result, str(conflict), skipped=False)
        return keep_going and choice != CHOICE_ABORT
    except Exception as error:  # unerwarteter Fehler: Eintrag zurückrollen, Lauf fortsetzen
        return _rollback_after_failure(ctx, store, resolver, result, f"Fehler: {error}", skipped=True)


def _rollback_after_failure(ctx, store, resolver, result, reason, *, skipped: bool) -> bool:
    try:
        if ctx.last_state() is not None:
            rollback_item(ctx, store, resolver)
        ctx.mark(SKIPPED if skipped else CONFLICT, reason=reason)
        (result.skipped if skipped else result.conflicts).append((ctx.label(), reason))
        return True
    except AbortRequested:
        result.aborted = True
        return False
    except ConflictError as conflict:
        ctx.mark(CONFLICT, reason=str(conflict))
        result.conflicts.append((ctx.label(), str(conflict)))
        return True


def execute_plan(run_dir: Path, *, store, resolver) -> RunResult:
    """Führt genau den Plan in `run_dir` aus (kein neuer Scan)."""
    run_dir = Path(run_dir)
    if (run_dir / JOURNAL_NAME).exists():
        raise PlanConsumed(str(run_dir))
    plan = load_plan(run_dir)
    return _run(plan, run_dir, store, resolver, check=True)


def resume_run(run_dir: Path, *, store, resolver) -> RunResult:
    """Setzt einen unterbrochenen Lauf fort; ein abgeschlossener Lauf ist ein No-op."""
    run_dir = Path(run_dir)
    records = read_journal(run_dir / JOURNAL_NAME)
    if any(record.get("event") == "finish" for record in records):
        return RunResult(run_dir=run_dir, already_finished=True)
    return _run(load_plan(run_dir), run_dir, store, resolver, check=False)


def _run(plan: MigrationPlan, run_dir: Path, store, resolver, *, check: bool) -> RunResult:
    journal = Journal(run_dir / JOURNAL_NAME)
    records = read_journal(journal.path)
    if not any(record.get("event") == "start" for record in records):
        records.append(journal.append({"event": "start", "root": plan.root}))
    result = RunResult(run_dir=run_dir)
    for entry in plan.entries:
        ctx = _context(plan, entry, run_dir, journal, records)
        if ctx.last_state() in TERMINAL_STATES or ctx.last_state() in (CONFLICT, "KEPT"):
            continue
        keep_going = _drive_item(ctx, plan, store, resolver, result, check=check)
        result.warnings.extend(ctx.warnings)
        if not keep_going:
            result.aborted = True
            break
    if not result.aborted:
        records.append(journal.append({"event": "finish"}))
    return result


def undo_run(run_dir: Path, *, store, resolver) -> RunResult:
    """Nimmt alle committed bzw. angefangenen Einträge zurück (umgekehrte Reihenfolge)."""
    run_dir = Path(run_dir)
    plan = load_plan(run_dir)
    journal = Journal(run_dir / JOURNAL_NAME)
    records = read_journal(journal.path)
    result = RunResult(run_dir=run_dir)
    for entry in reversed(plan.entries):
        ctx = _context(plan, entry, run_dir, journal, records)
        if ctx.last_state() in (None, ROLLED_BACK, SKIPPED, "KEPT"):
            continue  # nie angefangen, schon zurückgenommen oder bewusst behalten
        try:
            outcome = rollback_item(ctx, store, resolver)
        except AbortRequested:
            result.aborted = True
            break
        except ConflictError as conflict:
            result.conflicts.append((ctx.label(), str(conflict)))
            continue
        finally:
            result.warnings.extend(ctx.warnings)
        (result.rolled_back if outcome == ROLLED_BACK else result.kept).append(ctx.label())
    if not result.aborted:
        records.append(journal.append({"event": "undo_finish"}))
    return result


def committed_count(run_dir: Path) -> int:
    """Anzahl verbindlich committeter Einträge (für Berichte)."""
    records = read_journal(Path(run_dir) / JOURNAL_NAME)
    return len({r["item"] for r in records if r.get("state") in (COMMITTED, SIDE_STATE_APPLIED)})


__all__ = [
    "CHOICE_SKIP",
    "PlanConsumed",
    "PlanInvalid",
    "RunResult",
    "committed_count",
    "default_runs_dir",
    "execute_plan",
    "load_plan",
    "new_run_dir",
    "resume_run",
    "undo_run",
    "write_plan",
]
