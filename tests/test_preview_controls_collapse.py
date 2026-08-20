from app.ui.blatt_ui_build import BlattwerkAppBuildMixin


class _FakeVar:
    def __init__(self, value=False):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _FakeFrame:
    def __init__(self):
        self.packed = True  # frisch gebaut ist es sichtbar
        self.pack_calls = []

    def pack(self, **kwargs):
        self.packed = True
        self.pack_calls.append(kwargs)

    def pack_forget(self):
        self.packed = False


class _FakeButton:
    def __init__(self):
        self.text = "▾"

    def configure(self, text):
        self.text = text


class _DummyPreviewControlsApp(BlattwerkAppBuildMixin):
    def __init__(self):
        self.preview_controls_collapsed_var = _FakeVar(False)
        self._preview_controls_frame = _FakeFrame()
        self.preview_controls_toggle_btn = _FakeButton()
        self._preview_controls_after_anchor = object()
        self.save_calls = 0

    def _save_ui_settings(self):
        self.save_calls += 1


def test_initial_state_is_expanded():
    app = _DummyPreviewControlsApp()

    app._apply_preview_controls_collapsed_state()

    assert app._preview_controls_frame.packed is True
    assert app.preview_controls_toggle_btn.text == "▾"


def test_toggle_collapses_the_frame_and_flips_chevron():
    app = _DummyPreviewControlsApp()

    app._toggle_preview_controls_collapsed()

    assert app.preview_controls_collapsed_var.get() is True
    assert app._preview_controls_frame.packed is False
    assert app.preview_controls_toggle_btn.text == "▸"


def test_toggle_twice_returns_to_expanded():
    app = _DummyPreviewControlsApp()

    app._toggle_preview_controls_collapsed()
    app._toggle_preview_controls_collapsed()

    assert app.preview_controls_collapsed_var.get() is False
    assert app._preview_controls_frame.packed is True
    assert app.preview_controls_toggle_btn.text == "▾"


def test_toggle_persists_ui_settings():
    app = _DummyPreviewControlsApp()

    app._toggle_preview_controls_collapsed()

    assert app.save_calls == 1


def test_apply_state_is_noop_before_widgets_exist():
    app = _DummyPreviewControlsApp()
    app._preview_controls_frame = None
    app.preview_controls_toggle_btn = None

    # Darf nicht abstuerzen, wenn _build_ui die Widgets noch nicht erzeugt hat.
    app._apply_preview_controls_collapsed_state()
