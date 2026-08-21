from pathlib import Path

from app.ui.export_dialog import LernhilfenExportDialog


class _FakeVar:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _FakeWindow:
    def __init__(self):
        self.destroyed = False

    def destroy(self):
        self.destroyed = True


def _make_dialog(*, allow_all_tabs_export, export_all_tabs, output="C:/tmp/out.pdf", fmt="pdf"):
    dialog = object.__new__(LernhilfenExportDialog)
    dialog.input_path = Path("C:/docs/blatt.md")
    dialog.window = _FakeWindow()
    dialog.result = None
    dialog.format_var = _FakeVar(fmt)
    dialog.output_var = _FakeVar(output)
    dialog.allow_all_tabs_export = allow_all_tabs_export
    dialog.export_all_tabs_var = _FakeVar(export_all_tabs)
    return dialog


def test_extension_is_zip_when_all_tabs_export_selected():
    dialog = _make_dialog(allow_all_tabs_export=True, export_all_tabs=True, fmt="pdf")

    assert dialog._extension() == ".zip"


def test_extension_follows_format_when_all_tabs_export_not_selected():
    dialog = _make_dialog(allow_all_tabs_export=True, export_all_tabs=False, fmt="png")

    assert dialog._extension() == ".png"


def test_confirm_sets_export_all_tabs_flag_and_forces_zip_suffix():
    dialog = _make_dialog(
        allow_all_tabs_export=True,
        export_all_tabs=True,
        output="C:/tmp/blatt_lernhilfen.pdf",
        fmt="pdf",
    )

    dialog._confirm()

    assert dialog.result["export_all_tabs"] is True
    assert dialog.result["output_path"].suffix == ".zip"
    assert dialog.result["format"] == "pdf"
    assert dialog.window.destroyed is True


def test_confirm_without_all_tabs_export_keeps_normal_single_document_behavior():
    dialog = _make_dialog(
        allow_all_tabs_export=True,
        export_all_tabs=False,
        output="C:/tmp/blatt_lernhilfen.pdf",
        fmt="pdf",
    )

    dialog._confirm()

    assert dialog.result["export_all_tabs"] is False
    assert dialog.result["output_path"].suffix == ".pdf"


def test_confirm_when_all_tabs_export_not_allowed_defaults_to_false():
    dialog = _make_dialog(
        allow_all_tabs_export=False,
        export_all_tabs=False,
        output="C:/tmp/blatt_lernhilfen.pdf",
        fmt="pdf",
    )

    dialog._confirm()

    assert dialog.result["export_all_tabs"] is False
