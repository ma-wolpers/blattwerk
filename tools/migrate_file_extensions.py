"""Migration alter Blattwerk-`.md`-Dateien auf die typgebundenen Endungen (.abw/.pbw/.kbw/.ebw).

Ablauf:
    1. Dry-Run (Standard): scannt, klassifiziert, schreibt nur `plan.json` in einen
       neuen Run-Ordner und gibt eine Zusammenfassung aus.
           python tools/migrate_file_extensions.py --root "A:\\Schule"
    2. Ausführen genau dieses Plans (kein neuer Scan):
           python tools/migrate_file_extensions.py --write --run <run-id>
    3. Fortsetzen bzw. Rückgängig machen:
           python tools/migrate_file_extensions.py --resume <run-id>
           python tools/migrate_file_extensions.py --undo <run-id>

Die Ausgabe enthält ausschließlich Pfade, Zieltypen, Status/Skip-Gründe und
Signalnamen -- nie Dateiinhalte. `--write/--resume/--undo` verweigern, solange
Blattwerk läuft (Lock-Protokoll in `app/bootstrap/process_locks.py`).
Exit-Codes: 0 ok, 1 Fehler/abgelehnt, 2 Konflikte bzw. nicht-interaktive
Entscheidungen, 4 Blattwerk läuft.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from bw_libs.shared_gui_core import ensure_bw_gui_on_path  # noqa: E402

ensure_bw_gui_on_path()

from app.bootstrap.process_locks import acquire_migration_lock, default_lock_dir  # noqa: E402
from app.core.migration.plan import DEFAULT_MAX_SIZE_BYTES, scan  # noqa: E402
from app.core.migration.runner import (  # noqa: E402
    PlanConsumed,
    PlanInvalid,
    default_runs_dir,
    execute_plan,
    new_run_dir,
    resume_run,
    undo_run,
    write_plan,
)
from app.storage.migration_side_state_store import LocalConfigSideStateStore  # noqa: E402

PROMPTS = {"ueberspringen": "[ü]berspringen", "abbrechen": "[a]bbrechen", "behalten": "[b]ehalten", "parallel": "[p]arallel wiederherstellen"}


class CliResolver:
    """Rückfragen im Terminal; nicht-interaktiv: sicherer Default und Exit-Code 2."""

    def __init__(self, interactive: bool) -> None:
        self.interactive = interactive
        self.defaulted = False

    def resolve(self, kind, item_label, choices):
        if not self.interactive:
            self.defaulted = True
            return "ueberspringen" if "ueberspringen" in choices else "behalten"
        options = " / ".join(PROMPTS[c] for c in choices)
        while True:
            answer = input(f"Konflikt ({kind}) bei {item_label}: {options}? ").strip().lower()
            for choice in choices:
                if answer and choice.startswith(answer[0].replace("ü", "u")):
                    return choice


def print_plan_summary(plan, run_dir: Path) -> None:
    by_target = Counter(entry.target_type for entry in plan.entries)
    by_status = Counter(item.status for item in plan.report)
    print(f"Run: {run_dir.name}  (Ordner: {run_dir})")
    print(f"Root: {plan.root}")
    print(f"Zu migrieren: {len(plan.entries)}  " + ", ".join(f"{k}={v}" for k, v in sorted(by_target.items())))
    print("Nicht migriert: " + (", ".join(f"{k}={v}" for k, v in sorted(by_status.items())) or "-"))
    structural = [e for e in plan.entries if e.signals == ("S_WS",)]
    if structural:
        print("\nSicher nur per Struktur (S_WS) -- bitte gezielt pruefen:")
        for entry in structural:
            print(f"  {entry.source} -> {entry.target}")
    print("\nGeplant:")
    for entry in plan.entries:
        print(f"  {entry.source} -> {entry.target}  [{entry.target_type}; {', '.join(entry.signals)}]")
    for status in sorted(by_status):
        if status == "kein_blattwerk":
            continue
        print(f"\n{status}:")
        for item in plan.report:
            if item.status == status:
                print(f"  {item.path}" + (f"  [{', '.join(item.signals)}]" if item.signals else ""))
    print(f"\nAusfuehren: python tools/migrate_file_extensions.py --write --run {run_dir.name}")


def print_result(result) -> None:
    if result.already_finished:
        print("Lauf ist bereits abgeschlossen (nichts zu tun).")
        return
    for label, values in (("Migriert", result.committed), ("Zurueckgenommen", result.rolled_back), ("Behalten", result.kept)):
        if values:
            print(f"{label} ({len(values)}):")
            for value in values:
                print(f"  {value}")
    for label, pairs in (("Uebersprungen", result.skipped), ("Konflikte", result.conflicts)):
        if pairs:
            print(f"{label} ({len(pairs)}):")
            for path, reason in pairs:
                print(f"  {path}: {reason}")
    if result.warnings:
        print(f"Warnungen ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"  {warning}")
    if result.aborted:
        print("Abgebrochen; der Lauf laesst sich mit --resume fortsetzen.")
    print(f"Rueckgaengig: python tools/migrate_file_extensions.py --undo {result.run_dir.name}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Blattwerk-Dateiendungs-Migration (Dry-Run standardmaessig).")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--max-size", type=float, default=DEFAULT_MAX_SIZE_BYTES / 1024 / 1024, help="MB")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--run", help="Run-ID (Ordnername) fuer --write")
    parser.add_argument("--resume", metavar="RUN_ID")
    parser.add_argument("--undo", metavar="RUN_ID")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--runs-dir", type=Path, default=default_runs_dir())
    parser.add_argument("--lock-dir", type=Path, default=default_lock_dir())
    args = parser.parse_args(argv)

    if not (args.write or args.resume or args.undo):
        if args.root is None:
            parser.error("--root ist fuer den Dry-Run erforderlich")
        plan = scan(args.root, excludes=tuple(args.exclude), max_size=int(args.max_size * 1024 * 1024))
        run_dir = new_run_dir(args.runs_dir)
        write_plan(plan, run_dir)
        print_plan_summary(plan, run_dir)
        return 0

    run_id = args.run if args.write else (args.resume or args.undo)
    if not run_id:
        parser.error("--write braucht --run <run-id>")
    run_dir = args.runs_dir / run_id
    lock = acquire_migration_lock(args.lock_dir)
    if lock is None:
        print("Blattwerk (oder eine andere Migration) laeuft. Bitte zuerst schliessen.")
        return 4
    resolver = CliResolver(interactive=not args.non_interactive and sys.stdin.isatty())
    store = LocalConfigSideStateStore()
    try:
        if args.write:
            result = execute_plan(run_dir, store=store, resolver=resolver)
        elif args.resume:
            result = resume_run(run_dir, store=store, resolver=resolver)
        else:
            result = undo_run(run_dir, store=store, resolver=resolver)
    except PlanConsumed:
        print("Dieser Plan wurde bereits ausgefuehrt. Unterbrochen? Dann --resume verwenden.")
        return 1
    except (PlanInvalid, FileNotFoundError) as error:
        print(f"Plan ungueltig oder nicht gefunden: {error}")
        return 1
    finally:
        lock.release()
    print_result(result)
    return 2 if (result.conflicts or resolver.defaulted) else 0


if __name__ == "__main__":
    raise SystemExit(main())
