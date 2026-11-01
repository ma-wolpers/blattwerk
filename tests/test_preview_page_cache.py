"""Cache der Vorschauseiten, Compile-Warnungen, Formel-Hinweis und feste Wortbank-Mischung."""

from __future__ import annotations

import os

from PIL import Image

from app.core.blatt_kern_answer_choice import _shuffle_word_bank
from app.core.blatt_validator_types import BuildDiagnostic
from app.core.diagnostic_warnings import build_warning_payload
from app.core.document_diagnostics import HTML_EXPORT_ONLY_CODES, without_html_export_notices
from app.core.document_preview_build import preview_environment_stamp
from app.core.operator_legend import OPERATOR_DATA_DIR
from app.core.render_job import note_file_dependency, run_observed
from app.ui.blatt_ui_export import BlattwerkAppExportMixin
from app.ui.preview_page_cache import CachedPreview, FileDependencyCollector, PreviewPageCache


def _entry(path="a.abw", pages=1, dependencies=None, size=10):
    images = tuple(Image.new("RGB", (size, size)) for _ in range(pages))
    return CachedPreview(images=images, diagnostics=(), dependencies=dependencies or {}, path=path)


def test_views_of_one_document_keep_separate_entries():
    cache = PreviewPageCache()
    worksheet, solution = _entry(), _entry()
    cache.put("aufgabe", worksheet)
    cache.put("loesung", solution)
    assert cache.get("aufgabe") is worksheet
    assert cache.get("loesung") is solution


def test_least_recently_used_entry_is_evicted_first():
    one_entry = _entry().size_bytes
    cache = PreviewPageCache(budget_bytes=2 * one_entry)
    cache.put("a", _entry())
    cache.put("b", _entry())
    cache.get("a")
    cache.put("c", _entry())
    assert cache.get("b") is None
    assert cache.get("a") is not None
    assert cache.get("c") is not None


def test_entry_above_the_budget_is_not_stored_and_replaces_nothing_stale():
    cache = PreviewPageCache(budget_bytes=_entry().size_bytes)
    cache.put("k", _entry())
    cache.put("k", _entry(pages=2))
    assert cache.get("k") is None


def test_drop_removes_all_entries_of_a_document():
    cache = PreviewPageCache()
    cache.put("a1", _entry("a.abw"))
    cache.put("a2", _entry("a.abw"))
    cache.put("b1", _entry("b.abw"))
    cache.drop("a.abw")
    assert cache.get("a1") is None and cache.get("a2") is None
    assert cache.get("b1") is not None


def _collect(path):
    collector = FileDependencyCollector()
    run_observed(lambda: note_file_dependency(path), collector)
    return collector.dependencies


def test_changed_image_invalidates_the_entry(tmp_path):
    image = tmp_path / "bild.png"
    image.write_bytes(b"alt")
    cache = PreviewPageCache()
    cache.put("k", _entry(dependencies=_collect(image)))
    assert cache.get("k") is not None

    stats = image.stat()
    image.write_bytes(b"neuer")
    os.utime(image, ns=(stats.st_atime_ns, stats.st_mtime_ns + 1_000_000))
    assert cache.get("k") is None


def test_image_that_appears_later_invalidates_the_entry(tmp_path):
    image = tmp_path / "fehlt.png"
    cache = PreviewPageCache()
    cache.put("k", _entry(dependencies=_collect(image)))
    assert cache.get("k") is not None

    image.write_bytes(b"da")
    assert cache.get("k") is None


def test_printing_reports_local_images_but_not_remote_ones(tmp_path, monkeypatch):
    from app.core import blatt_kern_io_pdf

    image = tmp_path / "bild.png"
    collector = FileDependencyCollector()
    html = f'<img src="{image.as_uri()}"><img src="https://example.org/x.png">'
    run_observed(lambda: blatt_kern_io_pdf._note_local_image_dependencies(html), collector)
    assert list(collector.dependencies) == [image]


def test_environment_stamp_notices_a_changed_operator_file(monkeypatch, tmp_path):
    monkeypatch.setattr("app.core.document_preview_build.OPERATOR_DATA_DIR", tmp_path)
    before = preview_environment_stamp()
    (tmp_path / "mathe.json").write_text("{}", encoding="utf-8")
    assert preview_environment_stamp() != before
    assert OPERATOR_DATA_DIR.name == "operatoren"


def _warning(code, message="m"):
    return BuildDiagnostic(code=code, message=message, severity="warning")


def _capture_warnings(monkeypatch):
    shown = []
    monkeypatch.setattr(
        "app.ui.blatt_ui_export_support.messagebox.showwarning",
        lambda title, text, **_kwargs: shown.append((title, text)),
    )
    return shown


def test_compile_warning_appears_once_per_state(monkeypatch):
    shown = _capture_warnings(monkeypatch)
    host = object.__new__(BlattwerkAppExportMixin)

    host._show_compile_overflow_warnings([_warning("PT002")], "Vorschau")
    host._show_compile_overflow_warnings([_warning("PT002")], "Vorschau")
    assert len(shown) == 1
    assert shown[0][1].startswith("Vorschau lief weiter")

    host._show_compile_overflow_warnings([_warning("PT002", "anders")], "Vorschau")
    assert len(shown) == 2


def test_formula_notice_is_filtered_outside_html_export():
    diagnostics = [_warning(code) for code in sorted(HTML_EXPORT_ONLY_CODES)] + [_warning("PT002")]
    assert [item.code for item in without_html_export_notices(diagnostics)] == ["PT002"]


class _NoAcknowledgements:
    def reconcile_acknowledged_warnings(self, _path, _identities):
        return set()


def test_warning_payload_shows_the_formula_notice_only_for_html_export(tmp_path):
    source = tmp_path / "blatt.abw"
    source.write_text("---\nTitel: T\nFach: M\nThema: X\n---\n:::task\n$x^2$\n:::\n", encoding="utf-8")

    plain = build_warning_payload(source, "Export", acknowledged_repo=_NoAcknowledgements())
    for_html = build_warning_payload(source, "Export", acknowledged_repo=_NoAcknowledgements(), html_export=True)
    assert "MJ001" not in plain["message"]
    assert "MJ001" in for_html["message"]


def test_word_bank_order_is_stable_and_still_shuffled():
    words = ["Apfel", "Birne", "Kirsche", "Pflaume", "Quitte", "Traube"]
    first = _shuffle_word_bank(words)
    assert first == _shuffle_word_bank(words)
    assert sorted(first) == sorted(words)
    assert first != words


def test_word_bank_order_follows_the_words():
    assert _shuffle_word_bank(["a", "b", "c", "d", "e", "f"]) != _shuffle_word_bank(["u", "v", "w", "x", "y", "z"])
