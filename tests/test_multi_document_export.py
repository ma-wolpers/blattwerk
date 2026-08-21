import zipfile
from pathlib import Path

import pytest

from app.ui.blatt_ui_export import BlattwerkAppExportMixin
from app.ui.blatt_ui_export_multi import BlattwerkAppExportMultiMixin


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _DummyDesignOptions:
    color_profile = "indigo"
    font_profile = "segoe"
    font_size_profile = "normal"


class _DummyMultiExportApp(BlattwerkAppExportMultiMixin, BlattwerkAppExportMixin):
    def __init__(self, document_tabs):
        self.document_tabs = document_tabs
        self._document_tab_order = list(document_tabs.keys())
        self.preview_mode_var = _Var("worksheet")
        self.status_var = _Var("")
        self._editor_has_unsaved_changes = False
        self.save_calls = 0

    def _worksheet_design_options(self):
        return _DummyDesignOptions()

    def _save_editor_content(self):
        self.save_calls += 1
        self._editor_has_unsaved_changes = False


def _write_doc(tmp_path, name, *, with_lernhilfe=True):
    if with_lernhilfe:
        text = (
            "---\nTitel: T\nFach: M\nThema: X\n---\n"
            ":::help title='Hilfe'\nInhalt\n:::\n"
        )
    else:
        text = "---\nTitel: T\nFach: M\nThema: X\n---\nEinfacher Text ohne Lernhilfe.\n"
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _fake_build_help_cards_from_request(request):
    output_path = request.output_path
    output_path.write_bytes(b"%PDF-FAKE")
    return output_path


@pytest.fixture(autouse=True)
def _patch_build(monkeypatch):
    monkeypatch.setattr(
        "app.ui.blatt_ui_export_multi.build_help_cards_from_request",
        _fake_build_help_cards_from_request,
    )


def test_exports_all_open_tabs_into_one_zip(tmp_path):
    doc_a = _write_doc(tmp_path, "a.md")
    doc_b = _write_doc(tmp_path, "b.md")
    app = _DummyMultiExportApp({"tab1": {"path": str(doc_a)}, "tab2": {"path": str(doc_b)}})

    output_zip = tmp_path / "out" / "bundle.zip"
    result = app._export_help_cards_for_multiple_documents(
        [doc_a, doc_b], output_zip, "a4_portrait", "standard"
    )

    assert result == [output_zip]
    assert output_zip.exists()
    with zipfile.ZipFile(output_zip) as archive:
        names = archive.namelist()
    assert "a_lernhilfen.pdf" in names
    assert "b_lernhilfen.pdf" in names


def test_flushes_active_tab_unsaved_changes_before_exporting(tmp_path):
    doc_a = _write_doc(tmp_path, "a.md")
    app = _DummyMultiExportApp({"tab1": {"path": str(doc_a)}})
    app._editor_has_unsaved_changes = True

    app._export_help_cards_for_multiple_documents(
        [doc_a], tmp_path / "out.zip", "a4_portrait", "standard"
    )

    assert app.save_calls == 1


def test_duplicate_tabs_pointing_to_same_file_are_not_deduplicated(tmp_path):
    doc_a = _write_doc(tmp_path, "a.md")
    app = _DummyMultiExportApp({"tab1": {"path": str(doc_a)}, "tab2": {"path": str(doc_a)}})

    output_zip = tmp_path / "out.zip"
    app._export_help_cards_for_multiple_documents([doc_a, doc_a], output_zip, "a4_portrait", "standard")

    with zipfile.ZipFile(output_zip) as archive:
        names = archive.namelist()
    assert names == ["a_lernhilfen.pdf", "a_lernhilfen_2.pdf"]


def test_document_without_lernhilfen_is_skipped_and_reported(tmp_path):
    doc_a = _write_doc(tmp_path, "a.md", with_lernhilfe=True)
    doc_plain = _write_doc(tmp_path, "plain.md", with_lernhilfe=False)
    app = _DummyMultiExportApp({"tab1": {"path": str(doc_a)}, "tab2": {"path": str(doc_plain)}})

    output_zip = tmp_path / "out.zip"
    app._export_help_cards_for_multiple_documents(
        [doc_a, doc_plain], output_zip, "a4_portrait", "standard"
    )

    with zipfile.ZipFile(output_zip) as archive:
        names = archive.namelist()
    assert names == ["a_lernhilfen.pdf"]
    assert "1 Dokument(e) exportiert" in app.status_var.get()
    assert "1 ohne Lernhilfen übersprungen" in app.status_var.get()


def test_all_documents_without_lernhilfen_raises_clear_error(tmp_path):
    doc_plain = _write_doc(tmp_path, "plain.md", with_lernhilfe=False)
    app = _DummyMultiExportApp({"tab1": {"path": str(doc_plain)}})

    with pytest.raises(ValueError, match="Lernhilfen"):
        app._export_help_cards_for_multiple_documents(
            [doc_plain], tmp_path / "out.zip", "a4_portrait", "standard"
        )


def test_unbuildable_document_aborts_entire_export_with_no_partial_zip(tmp_path, monkeypatch):
    doc_a = _write_doc(tmp_path, "a.md")
    doc_broken = _write_doc(tmp_path, "broken.md")

    def _failing_build(request):
        if "broken" in str(request.input_path):
            raise ValueError("Dokument enthaelt kritische Fehler und kann nicht gebaut werden")
        return _fake_build_help_cards_from_request(request)

    monkeypatch.setattr("app.ui.blatt_ui_export_multi.build_help_cards_from_request", _failing_build)

    app = _DummyMultiExportApp({"tab1": {"path": str(doc_a)}, "tab2": {"path": str(doc_broken)}})
    output_zip = tmp_path / "out" / "bundle.zip"

    with pytest.raises(RuntimeError, match="broken.md"):
        app._export_help_cards_for_multiple_documents(
            [doc_a, doc_broken], output_zip, "a4_portrait", "standard"
        )

    assert not output_zip.exists()
    assert not output_zip.parent.exists()


def test_collect_open_document_paths_preserves_tab_order_without_dedup():
    app = _DummyMultiExportApp(
        {
            "tab1": {"path": "/a/one.md"},
            "tab2": {"path": "/a/two.md"},
            "tab3": {"path": "/a/one.md"},
        }
    )

    paths = app._collect_open_document_paths()

    assert paths == [Path("/a/one.md"), Path("/a/two.md"), Path("/a/one.md")]
