from pathlib import Path

from app.ui.export_dialog import PresentationExportDialog


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


def _make_dialog(*, ignore_framebreaks):
    dialog = object.__new__(PresentationExportDialog)
    dialog.input_path = Path("C:/docs/praesentation.md")
    dialog.window = _FakeWindow()
    dialog.result = None
    dialog.format_var = _FakeVar("pdf")
    dialog.black_screen_var = _FakeVar("none")
    dialog.output_var = _FakeVar("C:/tmp/praesentation.pdf")
    dialog.ignore_framebreaks_var = _FakeVar(ignore_framebreaks)
    return dialog


def test_confirm_defaults_ignore_framebreaks_to_false():
    dialog = _make_dialog(ignore_framebreaks=False)

    dialog._confirm()

    assert dialog.result["ignore_framebreaks"] is False


def test_confirm_carries_ignore_framebreaks_when_checked():
    dialog = _make_dialog(ignore_framebreaks=True)

    dialog._confirm()

    assert dialog.result["ignore_framebreaks"] is True
