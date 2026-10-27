"""Gesperrte Export-Zieldatei: sofort abbrechen oder auf ``(neu)`` ausweichen.

Abgesichert werden die Policy-Aufloesung (`resolve_locked_target`), die Windows-Probe
gegen echte offene Handles und dass `build_worksheet` *vor* dem Rendern scheitert.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import app.core.blatt_kern_io_build as build_module
from app.core.export_path_guardrails import (
    LOCK_POLICY_ALTERNATE,
    LOCK_POLICY_ERROR,
    ExportTargetPolicy,
    LockedExportTargetError,
    alternate_target_names,
    resolve_locked_target,
    validate_export_output_path,
)
from app.storage.file_lock_probe_adapter import default_lock_probe

WORKSHEET = "---\nTitel: Test\n---\n\n:::info\nHallo\n:::\n"


class _FakeProbe:
    """Probe, die genau die uebergebenen Pfade als gesperrt meldet."""

    def __init__(self, *locked: Path):
        """Merkt sich die gesperrten Pfade (aufgeloest)."""
        self.locked = {Path(p).resolve() for p in locked}

    def is_locked(self, path: Path) -> bool:
        """True fuer gemerkte Pfade."""
        return Path(path).resolve() in self.locked


def test_unlocked_target_is_returned_unchanged(tmp_path):
    """Ohne Sperre (und ohne Probe) bleibt der Pfad, wie er ist."""
    target = tmp_path / "blatt.pdf"
    assert resolve_locked_target(target, ExportTargetPolicy(probe=_FakeProbe())) == target
    assert resolve_locked_target(target, None) == target


def test_error_policy_raises_with_file_name(tmp_path):
    """Policy "error": klarer Fehler, der die Datei nennt."""
    target = tmp_path / "blatt.pdf"
    with pytest.raises(LockedExportTargetError, match="blatt.pdf"):
        resolve_locked_target(target, ExportTargetPolicy(LOCK_POLICY_ERROR, _FakeProbe(target)))


def test_alternate_policy_skips_locked_candidates_and_is_idempotent(tmp_path):
    """Ausweichname ``(neu)``, bei Sperre ``(neu 2)``; zweiter Aufruf liefert dasselbe."""
    target = tmp_path / "blatt.pdf"
    first_alt = tmp_path / "blatt (neu).pdf"
    policy = ExportTargetPolicy(LOCK_POLICY_ALTERNATE, _FakeProbe(target, first_alt))

    resolved = resolve_locked_target(target, policy)

    assert resolved.name == "blatt (neu 2).pdf"
    assert resolve_locked_target(resolved, policy) == resolved


def test_alternate_names_never_stack_the_mark():
    """Ein bereits umgeleiteter Name bekommt kein zweites ``(neu)``."""
    names = [p.name for p in list(alternate_target_names(Path("x (neu 3).pdf")))[:2]]
    assert names == ["x (neu).pdf", "x (neu 2).pdf"]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-Sperrsemantik")
def test_windows_probe_detects_open_handle(tmp_path):
    """Eine per ``open(..., "rb")`` offene Datei gilt als gesperrt, danach nicht mehr."""
    target = tmp_path / "offen.pdf"
    target.write_bytes(b"%PDF")
    probe = default_lock_probe()

    with open(target, "rb"):
        assert probe.is_locked(target)
    assert not probe.is_locked(target)
    assert not probe.is_locked(tmp_path / "fehlt.pdf")


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-Sperrsemantik")
def test_build_fails_before_rendering_when_target_is_locked(tmp_path, monkeypatch):
    """Policy "error": kein Rendern, alte Datei bleibt unveraendert."""
    source = tmp_path / "blatt.abw"
    source.write_text(WORKSHEET, encoding="utf-8")
    target = tmp_path / "blatt.html"
    target.write_text("alt", encoding="utf-8")
    render_calls = []
    monkeypatch.setattr(build_module, "render_html", lambda *a, **k: render_calls.append(1) or "")

    with open(target, "rb"):
        with pytest.raises(LockedExportTargetError):
            build_module.build_worksheet(
                source, target, target_policy=ExportTargetPolicy(LOCK_POLICY_ERROR, default_lock_probe())
            )

    assert render_calls == []
    assert target.read_text(encoding="utf-8") == "alt"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-Sperrsemantik")
def test_build_writes_alternate_name_when_target_is_locked(tmp_path):
    """Policy "alternate_name": Ergebnis landet in ``blatt (neu).html``."""
    source = tmp_path / "blatt.abw"
    source.write_text(WORKSHEET, encoding="utf-8")
    target = tmp_path / "blatt.html"
    target.write_text("alt", encoding="utf-8")

    with open(target, "rb"):
        written = build_module.build_worksheet(
            source, target, target_policy=ExportTargetPolicy(LOCK_POLICY_ALTERNATE, default_lock_probe())
        )

    assert Path(written).name == "blatt (neu).html"
    assert target.read_text(encoding="utf-8") == "alt"
    assert "Hallo" in Path(written).read_text(encoding="utf-8")


def test_validate_passes_policy_through(tmp_path):
    """`validate_export_output_path` wendet die Policy nach der Validierung an."""
    target = tmp_path / "blatt.pdf"
    policy = ExportTargetPolicy(LOCK_POLICY_ALTERNATE, _FakeProbe(target))
    assert validate_export_output_path(target, allowed_suffixes={".pdf"}, target_policy=policy).name == "blatt (neu).pdf"
