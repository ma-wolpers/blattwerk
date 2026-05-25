from app.ui.blatt_ui_preview import BlattwerkAppPreviewMixin


class _DummyPreview(BlattwerkAppPreviewMixin):
    def __init__(self, user_preferences=None):
        self.user_preferences = dict(user_preferences or {})
        self.force_rebuild_calls = []

    def refresh_preview(self, force_rebuild=False):
        self.force_rebuild_calls.append(bool(force_rebuild))


def test_tab_switch_preview_refresh_defaults_to_force_rebuild():
    dummy = _DummyPreview()

    dummy._refresh_preview_for_active_tab()

    assert dummy.force_rebuild_calls == [True]


def test_tab_switch_preview_refresh_can_use_cache_when_disabled():
    dummy = _DummyPreview({"preview_auto_refresh_on_tab_switch": False})

    dummy._refresh_preview_for_active_tab()

    assert dummy.force_rebuild_calls == [False]


def test_tab_switch_preview_refresh_accepts_truthy_string():
    dummy = _DummyPreview({"preview_auto_refresh_on_tab_switch": "ja"})

    dummy._refresh_preview_for_active_tab()

    assert dummy.force_rebuild_calls == [True]
