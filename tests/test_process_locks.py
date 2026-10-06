"""Gegenseitiger Ausschluss App ↔ Migration über OS-Byte-Locks (echte Subprozesse)."""

import subprocess
import sys
import textwrap
import time

from app.bootstrap.process_locks import acquire_migration_lock, register_app_instance

HOLDER = textwrap.dedent(
    """
    import sys, time
    sys.path.insert(0, {repo!r})
    from bw_libs.shared_gui_core import ensure_bw_gui_on_path
    ensure_bw_gui_on_path()
    from pathlib import Path
    from app.bootstrap.process_locks import acquire_migration_lock, register_app_instance
    lock_dir = Path({lock_dir!r})
    lock = register_app_instance(lock_dir) if {kind!r} == "app" else acquire_migration_lock(lock_dir)
    print("held" if lock else "refused", flush=True)
    time.sleep(30)
    """
)


def _spawn(tmp_path, kind):
    from pathlib import Path

    repo = str(Path(__file__).resolve().parents[1])
    code = HOLDER.format(repo=repo, lock_dir=str(tmp_path), kind=kind)
    process = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    assert process.stdout.readline().strip() == "held"
    return process


def test_running_app_blocks_migration_and_vice_versa(tmp_path):
    app = _spawn(tmp_path, "app")
    try:
        assert acquire_migration_lock(tmp_path) is None
    finally:
        app.kill()
        app.wait()

    migration = _spawn(tmp_path, "migration")
    try:
        assert register_app_instance(tmp_path) is None
    finally:
        migration.kill()
        migration.wait()


def test_stale_app_lock_is_cleaned_after_process_death(tmp_path):
    app = _spawn(tmp_path, "app")
    app.kill()
    app.wait()
    time.sleep(0.2)

    lock = acquire_migration_lock(tmp_path)
    try:
        assert lock is not None
        assert not list(tmp_path.glob("app-*.lock"))
    finally:
        lock.release()


def test_gui_migration_ignores_own_app_lock(tmp_path):
    own = register_app_instance(tmp_path)
    try:
        migration = acquire_migration_lock(tmp_path, own_app_lock=own)
        assert migration is not None
        migration.release()
    finally:
        own.release()


def test_simultaneous_start_never_runs_both(tmp_path):
    for _ in range(5):
        app = register_app_instance(tmp_path)
        migration = acquire_migration_lock(tmp_path, own_app_lock=None)
        try:
            assert not (app is not None and migration is not None)
        finally:
            for lock in (app, migration):
                if lock is not None:
                    lock.release()
