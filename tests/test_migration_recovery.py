"""Abbruch, Fehlerinjektion und Recovery der Migrations-Zustandsmaschine.

`SimulatedCrash` erbt von `BaseException`, damit der Runner ihn -- wie einen
echten Prozessabbruch -- nicht abfängt; das Journal bleibt im Zwischenstand.
"""

import os
import stat

import pytest

from app.core.migration import forward, journal as journal_module
from app.core.migration.journal import JournalCorrupt, read_journal
from app.core.migration.runner import execute_plan, resume_run, undo_run

from migration_helpers import WORKSHEET, ScriptedResolver, make_tree, planned_run, store_with


class SimulatedCrash(BaseException):
    pass


def _crash_after_journal_entries(monkeypatch, count):
    """Bricht ab, nachdem `count` Journal-Einträge verbindlich geschrieben wurden."""
    original = journal_module.Journal.append
    calls = {"n": 0}

    def append(self, record):
        result = original(self, record)
        calls["n"] += 1
        if calls["n"] == count:
            raise SimulatedCrash()
        return result

    monkeypatch.setattr(journal_module.Journal, "append", append)


def _setup(tmp_path):
    root = make_tree(tmp_path, {"blatt.md": WORKSHEET})
    _plan, run_dir = planned_run(tmp_path, root)
    return root, run_dir


def _final_state_ok(root):
    assert not (root / "blatt.md").exists()
    assert (root / "blatt.abw").read_text(encoding="utf-8").startswith("---\ndocument_type: worksheet\n")
    assert not list(root.glob("*.bw-*")) and not list(root.glob(".*.bw-*"))


def _original_state_ok(root):
    assert (root / "blatt.md").read_text(encoding="utf-8") == WORKSHEET
    assert not (root / "blatt.abw").exists()
    assert not list(root.glob("*.bw-*")) and not list(root.glob(".*.bw-*"))


TOTAL_ENTRIES = 18  # start + Absichten + Zustände eines Eintrags (inkl. finish)


@pytest.mark.parametrize("crash_at", range(1, TOTAL_ENTRIES))
def test_crash_after_any_journal_entry_resume_completes(tmp_path, monkeypatch, crash_at):
    root, run_dir = _setup(tmp_path)
    _crash_after_journal_entries(monkeypatch, crash_at)
    try:
        execute_plan(run_dir, store=None, resolver=ScriptedResolver())
    except SimulatedCrash:
        pass
    monkeypatch.undo()

    resume_run(run_dir, store=None, resolver=ScriptedResolver())

    _final_state_ok(root)


@pytest.mark.parametrize("crash_at", range(1, TOTAL_ENTRIES))
def test_crash_after_any_journal_entry_undo_restores_original(tmp_path, monkeypatch, crash_at):
    root, run_dir = _setup(tmp_path)
    store = store_with(root / "blatt.md")
    _crash_after_journal_entries(monkeypatch, crash_at)
    try:
        execute_plan(run_dir, store=store, resolver=ScriptedResolver())
    except SimulatedCrash:
        pass
    monkeypatch.undo()

    undo_run(run_dir, store=store, resolver=ScriptedResolver())

    _original_state_ok(root)
    assert store.recent_files == [(root / "blatt.md").as_posix()]


@pytest.mark.parametrize("function_name", ["write_new_file", "rename_no_replace", "set_readonly", "identity_of"])
def test_fault_injection_rolls_item_back_and_keeps_original(tmp_path, monkeypatch, function_name):
    root, run_dir = _setup(tmp_path)
    original = getattr(forward, function_name)
    calls = {"n": 0}

    def failing(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("injiziert")
        return original(*args, **kwargs)

    monkeypatch.setattr(forward, function_name, failing)
    result = execute_plan(run_dir, store=None, resolver=ScriptedResolver(default="ueberspringen"))
    monkeypatch.undo()

    if result.committed:
        _final_state_ok(root)  # Fehler traf nur eine nicht-kritische Metadaten-Operation
    else:
        _original_state_ok(root)


def _crash_between_link_and_unlink(monkeypatch, which):
    """Simuliert den POSIX-Zwischenzustand: `link` erfolgt, `unlink` nicht."""
    original = forward.rename_no_replace

    def link_only(src, dst):
        if which in str(dst):
            os.link(src, dst)
            raise SimulatedCrash()
        return original(src, dst)

    monkeypatch.setattr(forward, "rename_no_replace", link_only)


@pytest.mark.parametrize("which", [".abw", ".bw-migrating-"])
def test_two_names_one_inode_resume_and_undo(tmp_path, monkeypatch, which):
    for action in ("resume", "undo"):
        base = tmp_path / action
        base.mkdir()
        root, run_dir = _setup(base)
        _crash_between_link_and_unlink(monkeypatch, which)
        with pytest.raises(SimulatedCrash):
            execute_plan(run_dir, store=None, resolver=ScriptedResolver())
        monkeypatch.undo()
        if action == "resume":
            resume_run(run_dir, store=None, resolver=ScriptedResolver())
            _final_state_ok(root)
        else:
            undo_run(run_dir, store=None, resolver=ScriptedResolver())
            _original_state_ok(root)


def test_two_names_with_different_identity_is_a_conflict(tmp_path, monkeypatch):
    root, run_dir = _setup(tmp_path)
    original = forward.rename_no_replace

    def crash_before_quarantine(src, dst):
        if ".bw-migrating-" in str(dst):
            raise SimulatedCrash()
        return original(src, dst)

    monkeypatch.setattr(forward, "rename_no_replace", crash_before_quarantine)
    with pytest.raises(SimulatedCrash):
        execute_plan(run_dir, store=None, resolver=ScriptedResolver())
    monkeypatch.undo()
    quarantine = next(iter([root / f"blatt.md.bw-migrating-{run_dir.name}"]))
    quarantine.write_text(WORKSHEET, encoding="utf-8")  # gleicher Inhalt, fremde Identität

    result = resume_run(run_dir, store=None, resolver=ScriptedResolver(default="ueberspringen"))

    assert result.conflicts
    assert quarantine.exists() and (root / "blatt.md").exists()


def test_target_changed_before_source_removal_keeps_source(tmp_path, monkeypatch):
    root, run_dir = _setup(tmp_path)
    original = forward.ensure_source_removed

    def edit_target_then_remove(ctx):
        os.chmod(ctx.dst, stat.S_IREAD | stat.S_IWRITE)
        ctx.dst.write_text("zwischendurch bearbeitet", encoding="utf-8")
        return original(ctx)

    steps = tuple(edit_target_then_remove if s is original else s for s in forward.FORWARD_STEPS)
    monkeypatch.setattr("app.core.migration.runner.FORWARD_STEPS", steps)
    result = execute_plan(run_dir, store=None, resolver=ScriptedResolver("ueberspringen", default="behalten"))

    assert result.conflicts or result.kept or result.skipped
    assert (root / "blatt.md").read_text(encoding="utf-8") == WORKSHEET
    assert (root / "blatt.abw").read_text(encoding="utf-8") == "zwischendurch bearbeitet"


def test_crash_between_readonly_clear_and_delete_restores_readonly_on_undo(tmp_path, monkeypatch):
    root, run_dir = _setup(tmp_path)
    os.chmod(root / "blatt.md", stat.S_IREAD)
    _plan, run_dir = planned_run(tmp_path, root)
    original_remove = forward.ensure_source_removed

    def crash(ctx):
        raise SimulatedCrash()

    steps = tuple(crash if s is original_remove else s for s in forward.FORWARD_STEPS)
    monkeypatch.setattr("app.core.migration.runner.FORWARD_STEPS", steps)
    with pytest.raises(SimulatedCrash):
        execute_plan(run_dir, store=None, resolver=ScriptedResolver())
    monkeypatch.undo()

    undo_run(run_dir, store=None, resolver=ScriptedResolver())

    assert (root / "blatt.md").read_text(encoding="utf-8") == WORKSHEET
    assert not (os.stat(root / "blatt.md").st_mode & stat.S_IWRITE)
    os.chmod(root / "blatt.md", stat.S_IREAD | stat.S_IWRITE)


def test_torn_last_journal_line_is_ignored_but_middle_damage_is_fatal(tmp_path):
    root, run_dir = _setup(tmp_path)
    execute_plan(run_dir, store=None, resolver=ScriptedResolver())
    path = run_dir / "journal.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()

    path.write_text("\n".join(lines) + "\n{\"seq\": 99, \"kaputt", encoding="utf-8")
    assert len(read_journal(path)) == len(lines)

    damaged = lines[:2] + ['{"seq": 3, "state": "X", "crc32": 1}'] + lines[3:]
    path.write_text("\n".join(damaged) + "\n", encoding="utf-8")
    with pytest.raises(JournalCorrupt):
        read_journal(path)
