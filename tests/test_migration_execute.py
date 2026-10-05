"""Zustandsmaschine der Migration: Glücksfall, Sicherheit, Idempotenz, Undo."""

import os
import stat

import pytest

from app.core.migration.journal import read_journal
from app.core.migration.plan import scan
from app.core.migration.runner import PlanConsumed, execute_plan, resume_run, undo_run

from migration_helpers import PRESENTATION, WORKSHEET, ScriptedResolver, make_tree, planned_run, store_with


def test_happy_path_renames_rewrites_and_updates_side_state(tmp_path):
    root = make_tree(tmp_path, {"a/blatt.md": WORKSHEET, "a/folien.md": PRESENTATION, "notiz.md": "# Notiz\n"})
    _plan, run_dir = planned_run(tmp_path, root)
    store = store_with(root / "a/blatt.md", root / "notiz.md")

    result = execute_plan(run_dir, store=store, resolver=ScriptedResolver())

    assert sorted(result.committed) == ["a/blatt.md", "a/folien.md"]
    assert not (root / "a/blatt.md").exists() and not (root / "a/folien.md").exists()
    assert (root / "a/blatt.abw").read_text(encoding="utf-8").startswith("---\ndocument_type: worksheet\n")
    folien = (root / "a/folien.pbw").read_text(encoding="utf-8")
    assert "document_type: presentation" in folien and "mode:" not in folien
    assert (root / "notiz.md").read_text(encoding="utf-8") == "# Notiz\n"
    assert store.recent_files == [(root / "a/blatt.abw").as_posix(), (root / "notiz.md").as_posix()]
    assert (root / "a/blatt.abw").as_posix() in store.acknowledged
    assert not list(root.rglob("*.bw-*"))


def test_rewrite_is_byte_exact_with_bom_crlf_and_no_final_newline(tmp_path):
    source = "﻿---\r\nTitel: T\r\nFach: M\r\nThema: X\r\nmode: test # alt\r\n---\r\n:::task\nA\r\n:::"
    root = make_tree(tmp_path, {"k.md": source.encode("utf-8")})
    _plan, run_dir = planned_run(tmp_path, root)

    execute_plan(run_dir, store=None, resolver=ScriptedResolver())

    expected = "﻿---\r\ndocument_type: exam\r\nTitel: T\r\nFach: M\r\nThema: X\r\n---\r\n:::task\nA\r\n:::"
    assert (root / "k.kbw").read_bytes() == expected.encode("utf-8")


def test_dry_run_writes_nothing(tmp_path):
    root = make_tree(tmp_path, {"blatt.md": WORKSHEET})
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}

    plan = scan(root)

    assert len(plan.entries) == 1
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


def test_target_created_after_plan_is_never_overwritten(tmp_path):
    root = make_tree(tmp_path, {"blatt.md": WORKSHEET})
    _plan, run_dir = planned_run(tmp_path, root)
    (root / "blatt.abw").write_text("FREMD", encoding="utf-8")
    resolver = ScriptedResolver("ueberspringen")

    result = execute_plan(run_dir, store=None, resolver=resolver)

    assert (root / "blatt.abw").read_text(encoding="utf-8") == "FREMD"
    assert (root / "blatt.md").read_text(encoding="utf-8") == WORKSHEET
    assert result.conflicts and resolver.calls[0][0] == "target_exists"


def test_source_changed_after_plan_is_skipped_untouched(tmp_path):
    root = make_tree(tmp_path, {"blatt.md": WORKSHEET})
    _plan, run_dir = planned_run(tmp_path, root)
    (root / "blatt.md").write_text(WORKSHEET + "\nneu\n", encoding="utf-8")

    result = execute_plan(run_dir, store=None, resolver=ScriptedResolver())

    assert result.skipped and not result.committed
    assert (root / "blatt.md").read_text(encoding="utf-8").endswith("neu\n")
    assert not (root / "blatt.abw").exists()


def test_plan_is_consumed_and_resume_after_finish_is_noop(tmp_path):
    root = make_tree(tmp_path, {"blatt.md": WORKSHEET})
    _plan, run_dir = planned_run(tmp_path, root)
    execute_plan(run_dir, store=None, resolver=ScriptedResolver())

    with pytest.raises(PlanConsumed):
        execute_plan(run_dir, store=None, resolver=ScriptedResolver())
    assert resume_run(run_dir, store=None, resolver=ScriptedResolver()).already_finished
    assert scan(root).entries == []  # neuer Dry-Run sieht migrierte Dateien nicht mehr


def test_undo_restores_original_bytes_and_side_state(tmp_path):
    root = make_tree(tmp_path, {"blatt.md": WORKSHEET, "folien.md": PRESENTATION})
    _plan, run_dir = planned_run(tmp_path, root)
    store = store_with(root / "blatt.md", root / "folien.md")
    execute_plan(run_dir, store=store, resolver=ScriptedResolver())

    result = undo_run(run_dir, store=store, resolver=ScriptedResolver())

    assert sorted(result.rolled_back) == ["blatt.md", "folien.md"]
    assert (root / "blatt.md").read_text(encoding="utf-8") == WORKSHEET
    assert (root / "folien.md").read_text(encoding="utf-8") == PRESENTATION
    assert not (root / "blatt.abw").exists() and not (root / "folien.pbw").exists()
    assert store.recent_files == [(root / "blatt.md").as_posix(), (root / "folien.md").as_posix()]
    assert scan(root).entries  # nach Undo wieder sichtbar
    assert undo_run(run_dir, store=store, resolver=ScriptedResolver()).rolled_back == []  # idempotent


def test_partial_undo_keeps_edited_target_and_side_state_exact(tmp_path):
    root = make_tree(tmp_path, {"a.md": WORKSHEET, "b.md": WORKSHEET})
    _plan, run_dir = planned_run(tmp_path, root)
    store = store_with(root / "a.md", root / "b.md")
    execute_plan(run_dir, store=store, resolver=ScriptedResolver())
    (root / "b.abw").write_text("bearbeitet", encoding="utf-8")
    store.recent_files.append((root / "andere.abw").as_posix())  # Nutzerin hat weitergearbeitet

    result = undo_run(run_dir, store=store, resolver=ScriptedResolver("behalten"))

    assert result.rolled_back == ["a.md"] and result.kept == ["b.md"]
    assert (root / "b.abw").read_text(encoding="utf-8") == "bearbeitet" and not (root / "b.md").exists()
    assert store.recent_files == [
        (root / "a.md").as_posix(),
        (root / "b.abw").as_posix(),
        (root / "andere.abw").as_posix(),
    ]


def test_undo_parallel_restore_creates_restored_copy(tmp_path):
    root = make_tree(tmp_path, {"b.md": WORKSHEET})
    _plan, run_dir = planned_run(tmp_path, root)
    execute_plan(run_dir, store=None, resolver=ScriptedResolver())
    (root / "b.abw").write_text("bearbeitet", encoding="utf-8")

    undo_run(run_dir, store=None, resolver=ScriptedResolver("parallel"))

    restored = list(root.glob("b.restored-*.md"))
    assert len(restored) == 1 and restored[0].read_text(encoding="utf-8") == WORKSHEET
    assert (root / "b.abw").read_text(encoding="utf-8") == "bearbeitet"


def test_readonly_and_times_are_transferred(tmp_path):
    root = make_tree(tmp_path, {"r.md": WORKSHEET})
    source = root / "r.md"
    os.utime(source, ns=(1_600_000_000_000_000_000, 1_500_000_000_000_000_000))
    os.chmod(source, stat.S_IREAD)
    _plan, run_dir = planned_run(tmp_path, root)

    result = execute_plan(run_dir, store=None, resolver=ScriptedResolver())

    target = root / "r.abw"
    assert result.committed == ["r.md"] and not source.exists()
    assert not (os.stat(target).st_mode & stat.S_IWRITE)
    assert os.stat(target).st_mtime_ns == 1_500_000_000_000_000_000
    os.chmod(target, stat.S_IREAD | stat.S_IWRITE)
    undo_run(run_dir, store=None, resolver=ScriptedResolver())
    os.chmod(source, stat.S_IREAD | stat.S_IWRITE)


def test_journal_records_every_state_in_order(tmp_path):
    root = make_tree(tmp_path, {"blatt.md": WORKSHEET})
    _plan, run_dir = planned_run(tmp_path, root)
    execute_plan(run_dir, store=None, resolver=ScriptedResolver())

    states = [r["state"] for r in read_journal(run_dir / "journal.jsonl") if "state" in r]
    assert states == [
        "BACKED_UP", "TARGET_WRITTEN", "TARGET_VERIFIED", "TARGET_ATTRS_APPLIED",
        "SOURCE_QUARANTINED", "SOURCE_RO_CLEARED", "SOURCE_REMOVED", "COMMITTED", "SIDE_STATE_APPLIED",
    ]
