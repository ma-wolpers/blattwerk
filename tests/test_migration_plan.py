"""Scan, Ausschlüsse, Plan-Validierung, Laufzeitprüfungen und Pfadvergleich der Migration."""

import json
import os
import subprocess
import sys

import pytest

from app.core.migration import plan as plan_module
from app.core.migration.plan import MigrationPlan, PlanInvalid, scan, target_name
from app.core.migration.runner import execute_plan, load_plan
from app.core.migration.side_state import InMemorySideStateStore, canonical_path_key

from migration_helpers import WORKSHEET, ScriptedResolver, make_tree, planned_run


def _status(plan, path):
    return next(item.status for item in plan.report if item.path == path)


def test_excludes_lerngruppen_git_hidden_and_custom_patterns(tmp_path):
    root = make_tree(
        tmp_path,
        {
            "Lerngruppen/6a/plan.md": WORKSHEET,
            "Fach/Mathe-lerngruppen-alt/x.md": WORKSHEET,
            ".git/x.md": WORKSHEET,
            ".versteckt/x.md": WORKSHEET,
            "Archiv/alt.md": WORKSHEET,
            "ok/blatt.md": WORKSHEET,
        },
    )

    plan = scan(root, excludes=("Archiv",))

    assert [e.source for e in plan.entries] == ["ok/blatt.md"]
    assert all("Lerngruppen" not in item.path and "lerngruppen" not in item.path for item in plan.report)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-Attribut HIDDEN")
def test_windows_hidden_attribute_is_excluded(tmp_path):
    root = make_tree(tmp_path, {"sichtbar.md": WORKSHEET, "versteckt.md": WORKSHEET})
    subprocess.run(["attrib", "+h", str(root / "versteckt.md")], check=True)

    assert [e.source for e in scan(root).entries] == ["sichtbar.md"]


@pytest.mark.skipif(sys.platform != "win32", reason="Junctions nur unter Windows")
def test_junctions_are_never_entered(tmp_path):
    root = make_tree(tmp_path, {"blatt.md": WORKSHEET})
    outside = tmp_path / "aussen"
    outside.mkdir()
    (outside / "fremd.md").write_text(WORKSHEET, encoding="utf-8")
    subprocess.run(["cmd", "/c", "mklink", "/J", str(root / "link"), str(outside)], check=True, capture_output=True)

    assert [e.source for e in scan(root).entries] == ["blatt.md"]


def test_symlinked_file_is_reported_not_migrated(tmp_path):
    root = make_tree(tmp_path, {"blatt.md": WORKSHEET})
    try:
        os.symlink(root / "blatt.md", root / "link.md")
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks nicht erlaubt")

    plan = scan(root)

    assert [e.source for e in plan.entries] == ["blatt.md"]
    assert _status(plan, "link.md") == "reparse_point"


def test_size_guard_and_non_utf8_are_skip_reasons(tmp_path):
    root = make_tree(tmp_path, {"gross.md": WORKSHEET + "x" * 200, "latin.md": "Größe".encode("latin-1")})

    plan = scan(root, max_size=100)

    assert _status(plan, "gross.md") == "uebersprungen_groesse"
    assert _status(plan, "latin.md") == "nicht_utf8"


def test_cloud_placeholders_are_not_read(tmp_path, monkeypatch):
    root = make_tree(tmp_path, {"platzhalter.md": WORKSHEET})
    monkeypatch.setattr(plan_module, "file_attributes", lambda _stat: plan_module.PLACEHOLDER_ATTRIBUTES)

    plan = scan(root)

    assert plan.entries == [] and _status(plan, "platzhalter.md") == "nicht_lokal"


def test_rewrite_unsafe_only_after_safe_classification(tmp_path):
    root = make_tree(
        tmp_path,
        {
            "doppelt.md": "---\nTitel: T\nTitel: U\nFach: M\nThema: X\n---\n:::task\nA\n:::\n",
            "\nnotiz.md".strip(): "# Text\n",
        },
    )

    plan = scan(root)

    assert _status(plan, "doppelt.md") == "rewrite_unsicher"
    assert _status(plan, "notiz.md") == "kein_blattwerk"


def test_target_name_rule():
    assert target_name("a.md", "worksheet") == "a.abw"
    assert target_name("Stunde.KWE.MD", "kurzentwurf") == "Stunde.ebw"
    assert target_name("x.kwe.backup.md", "worksheet") == "x.kwe.backup.abw"


def test_plan_roundtrip_and_version_check(tmp_path):
    root = make_tree(tmp_path, {"blatt.md": WORKSHEET})
    _plan, run_dir = planned_run(tmp_path, root)
    loaded = load_plan(run_dir)
    assert loaded.entries[0].target == "blatt.abw"

    data = json.loads((run_dir / "plan.json").read_text(encoding="utf-8"))
    data["rewrite_version"] = 999
    with pytest.raises(PlanInvalid):
        MigrationPlan.from_json(json.dumps(data))
    with pytest.raises(PlanInvalid):
        MigrationPlan.from_json("{kaputt")


@pytest.mark.parametrize(
    "tamper",
    [
        lambda e: e.update(target="anderes.abw"),
        lambda e: e.update(target_type="exam", target="blatt.kbw"),
        lambda e: e.update(source="../aussen/blatt.md", target="../aussen/blatt.abw"),
        lambda e: e.update(rewrite_sha256="0" * 64),
    ],
)
def test_tampered_plan_with_valid_syntax_is_refused(tmp_path, tamper):
    root = make_tree(tmp_path, {"blatt.md": WORKSHEET})
    _plan, run_dir = planned_run(tmp_path, root)
    data = json.loads((run_dir / "plan.json").read_text(encoding="utf-8"))
    tamper(data["entries"][0])
    (run_dir / "plan.json").write_text(json.dumps(data), encoding="utf-8")

    result = execute_plan(run_dir, store=None, resolver=ScriptedResolver(default="ueberspringen"))

    assert not result.committed
    assert (root / "blatt.md").read_text(encoding="utf-8") == WORKSHEET
    assert not list(root.glob("*.abw")) and not list(root.glob("*.kbw"))


def test_canonical_path_key_windows_and_posix():
    assert canonical_path_key("C:\\Schule\\x.md", windows=True) == canonical_path_key("c:/schule/X.md", windows=True)
    assert canonical_path_key("/a/x.md", windows=False) != canonical_path_key("/a/X.md", windows=False)
    assert canonical_path_key("/a/b/", windows=False) == canonical_path_key("/a/b", windows=False)


def test_side_state_store_renames_only_matching_entries(tmp_path):
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    store = InMemorySideStateStore([a.as_posix(), b.as_posix()], {a.as_posix(): ["x"]})

    store.apply_rename(str(a).upper() if sys.platform == "win32" else str(a), str(tmp_path / "a.abw"))

    assert store.recent_files == [(tmp_path / "a.abw").as_posix(), b.as_posix()]
    assert list(store.acknowledged) == [(tmp_path / "a.abw").as_posix()]
