"""Staging von Exporten: privat bauen, erst am Ende aufs Ziel veroeffentlichen.

Regression: Chromium druckte direkt aufs Ziel; war die Ziel-PDF im Viewer offen, blieb
still die *alte* Datei liegen und Praesentationen meldeten trotzdem Erfolg.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import app.core.blatt_kern_io_build as io_build
import app.core.export_staging as staging
from app.core.export_path_guardrails import (
    LOCK_POLICY_ALTERNATE,
    ExportTargetPolicy,
    LockedExportTargetError,
)
from app.core.export_staging import staged_export, write_document_output

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="Windows-Sperrsemantik")
PRESENTATION = "---\nTitel: Folien\n---\n\n## Folie 1\n\n:::info\nHallo\n:::\n"


@pytest.fixture(autouse=True)
def _no_publish_delay(monkeypatch):
    """Retry ohne Wartezeit, damit gesperrte Faelle schnell bleiben."""
    monkeypatch.setattr(staging, "PUBLISH_RETRY_DELAY_SECONDS", 0)


def _fake_pdf(html, path):
    """Drucker-Ersatz: schreibt das HTML als Bytes (kein Chromium noetig)."""
    Path(path).write_bytes(html.encode("utf-8"))
    return Path(path)


def _leftovers(folder: Path):
    """Versteckte Publish-Reste im Zielordner."""
    return list(folder.glob(".~blattwerk-*"))


def test_publish_writes_target_and_leaves_nothing_behind(tmp_path):
    """Normalfall: Ziel enthaelt das neue Ergebnis, keine Reste."""
    target = tmp_path / "blatt.pdf"
    written = write_document_output("neu", target, render_pdf=_fake_pdf)
    assert written == target
    assert target.read_text(encoding="utf-8") == "neu"
    assert _leftovers(tmp_path) == []


def test_failed_render_publishes_nothing(tmp_path):
    """Fehler im Block: altes Ziel bleibt, keine Reste."""
    target = tmp_path / "blatt.pdf"
    target.write_text("alt", encoding="utf-8")
    with pytest.raises(ValueError):
        with staged_export(target) as staged:
            staged.work_path.write_text("halb", encoding="utf-8")
            raise ValueError("Build kaputt")
    assert target.read_text(encoding="utf-8") == "alt"
    assert _leftovers(tmp_path) == []


@windows_only
def test_lock_during_build_raises_and_keeps_old_file(tmp_path):
    """Ohne Probe (z. B. CLI) erkennt der Publish die Sperre exakt."""
    target = tmp_path / "blatt.pdf"
    target.write_text("alt", encoding="utf-8")
    with open(target, "rb"):
        with pytest.raises(LockedExportTargetError):
            write_document_output("neu", target, render_pdf=_fake_pdf)
    assert target.read_text(encoding="utf-8") == "alt"
    assert _leftovers(tmp_path) == []


@windows_only
def test_lock_during_build_uses_alternate_name(tmp_path):
    """Policy "alternate_name" gilt auch beim Publish."""
    target = tmp_path / "blatt.pdf"
    target.write_text("alt", encoding="utf-8")
    with open(target, "rb"):
        written = write_document_output(
            "neu", target, ExportTargetPolicy(LOCK_POLICY_ALTERNATE), render_pdf=_fake_pdf
        )
    assert written.name == "blatt (neu).pdf"
    assert written.read_text(encoding="utf-8") == "neu"
    assert target.read_text(encoding="utf-8") == "alt"


@windows_only
def test_presentation_with_locked_target_no_longer_reports_success(tmp_path, monkeypatch):
    """Frueher: Chromium scheiterte still, Erfolg mit alter PDF. Jetzt: klarer Fehler."""
    source = tmp_path / "folien.pbw"
    source.write_text(PRESENTATION, encoding="utf-8")
    target = tmp_path / "folien.pdf"
    target.write_text("alt", encoding="utf-8")
    monkeypatch.setattr(io_build, "write_pdf_from_html", _fake_pdf)
    monkeypatch.setattr(io_build, "_append_presentation_overflow_warning", lambda **kwargs: None)

    with open(target, "rb"):
        with pytest.raises(LockedExportTargetError):
            io_build.build_worksheet(source, target, page_format="presentation_16_9", document_type="presentation")
    assert target.read_text(encoding="utf-8") == "alt"
