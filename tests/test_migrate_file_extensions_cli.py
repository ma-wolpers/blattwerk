"""CLI der Dateiendungs-Migration: Dry-Run, Write, Undo, keine Inhalte in der Ausgabe."""

import importlib.util
from pathlib import Path

import pytest

from app.core.migration.side_state import InMemorySideStateStore
from app.storage import migration_side_state_store

from migration_helpers import WORKSHEET, make_tree

CANARY = "KANARIENVOGEL-4711"
TOOL_PATH = Path(__file__).resolve().parents[1] / "tools" / "migrate_file_extensions.py"


@pytest.fixture
def cli(monkeypatch):
    spec = importlib.util.spec_from_file_location("migrate_file_extensions_cli", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    store = InMemorySideStateStore()
    monkeypatch.setattr(module, "LocalConfigSideStateStore", lambda: store)  # echte Config nie anfassen
    module.test_store = store
    return module


def _args(tmp_path, *extra):
    return [*extra, "--runs-dir", str(tmp_path / "runs"), "--lock-dir", str(tmp_path / "locks")]


def test_dry_run_writes_only_plan_and_never_prints_content(cli, tmp_path, capsys):
    root = make_tree(tmp_path, {"blatt.md": WORKSHEET.replace("A\n", f"{CANARY}\n"), "notiz.md": f"# {CANARY}\n"})
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}

    assert cli.main(_args(tmp_path, "--root", str(root))) == 0

    output = capsys.readouterr().out
    assert CANARY not in output
    assert "blatt.md -> blatt.abw" in output
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before
    assert len(list((tmp_path / "runs").glob("*/plan.json"))) == 1


def test_write_then_undo_roundtrip(cli, tmp_path, capsys):
    root = make_tree(tmp_path, {"blatt.md": WORKSHEET})
    cli.main(_args(tmp_path, "--root", str(root)))
    run_id = next((tmp_path / "runs").iterdir()).name

    assert cli.main(_args(tmp_path, "--write", "--run", run_id, "--non-interactive")) == 0
    assert (root / "blatt.abw").exists() and not (root / "blatt.md").exists()
    assert cli.main(_args(tmp_path, "--write", "--run", run_id, "--non-interactive")) == 1  # verbraucht
    assert cli.main(_args(tmp_path, "--resume", run_id, "--non-interactive")) == 0  # No-op

    assert cli.main(_args(tmp_path, "--undo", run_id, "--non-interactive")) == 0
    assert (root / "blatt.md").read_text(encoding="utf-8") == WORKSHEET
    assert CANARY not in capsys.readouterr().out


def test_write_refused_while_app_runs(cli, tmp_path, capsys):
    from app.bootstrap.process_locks import register_app_instance

    root = make_tree(tmp_path, {"blatt.md": WORKSHEET})
    cli.main(_args(tmp_path, "--root", str(root)))
    run_id = next((tmp_path / "runs").iterdir()).name
    app_lock = register_app_instance(tmp_path / "locks")
    try:
        assert cli.main(_args(tmp_path, "--write", "--run", run_id, "--non-interactive")) == 4
    finally:
        app_lock.release()
    assert (root / "blatt.md").exists()


def test_non_interactive_conflict_returns_exit_2(cli, tmp_path):
    root = make_tree(tmp_path, {"blatt.md": WORKSHEET})
    cli.main(_args(tmp_path, "--root", str(root)))
    run_id = next((tmp_path / "runs").iterdir()).name
    (root / "blatt.abw").write_text("FREMD", encoding="utf-8")

    assert cli.main(_args(tmp_path, "--write", "--run", run_id, "--non-interactive")) == 2
    assert (root / "blatt.abw").read_text(encoding="utf-8") == "FREMD"


def test_storage_adapter_renames_only_matching_entries(monkeypatch, tmp_path):
    a = (tmp_path / "a.md").as_posix()
    b = (tmp_path / "b.md").as_posix()
    config = {"recent_files": [a, b], "acknowledged_warnings": {a: ["x"], b: ["y"]}}
    saved = {}
    monkeypatch.setattr(migration_side_state_store, "load_local_config", lambda: dict(config))
    monkeypatch.setattr(migration_side_state_store, "save_local_config", lambda c: saved.update(c))

    migration_side_state_store.LocalConfigSideStateStore().apply_rename(a, str(tmp_path / "a.abw"))

    assert saved["recent_files"] == [(tmp_path / "a.abw").resolve().as_posix(), b]
    assert set(saved["acknowledged_warnings"]) == {(tmp_path / "a.abw").resolve().as_posix(), b}
