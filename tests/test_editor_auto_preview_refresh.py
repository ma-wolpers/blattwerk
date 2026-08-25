from app.ui.blatt_ui_editor import BlattwerkAppEditorMixin


class _FakeRoot:
    def __init__(self):
        self.after_calls = []
        self.after_cancel_calls = []

    def after(self, delay_ms, callback):
        timer_id = f"timer-{len(self.after_calls) + 1}"
        self.after_calls.append((delay_ms, callback, timer_id))
        return timer_id

    def after_cancel(self, timer_id):
        self.after_cancel_calls.append(timer_id)


class _DummyEditor(BlattwerkAppEditorMixin):
    def __init__(self):
        self.root = _FakeRoot()
        self.editor_widget = object()
        self._preview_auto_refresh_after_id = None
        self._preview_auto_refresh_on_edit_idle_enabled = False
        self._preview_auto_refresh_on_edit_idle_delay_ms = 1200
        self._editor_save_after_id = None
        self._editor_has_unsaved_changes = False
        self.refresh_calls = []
        self.save_calls = []
        self._save_sets_unsaved_false = True

    def refresh_preview(self, force_rebuild=False):
        self.refresh_calls.append(bool(force_rebuild))

    def _save_editor_content(self):
        self.save_calls.append(True)
        if self._save_sets_unsaved_false:
            self._editor_has_unsaved_changes = False


def test_queue_editor_auto_preview_refresh_disabled_cancels_pending_timer():
    app = _DummyEditor()
    app._preview_auto_refresh_after_id = "timer-old"

    app._queue_editor_auto_preview_refresh()

    assert app.root.after_cancel_calls == ["timer-old"]
    assert app._preview_auto_refresh_after_id is None
    assert app.root.after_calls == []


def test_queue_editor_auto_preview_refresh_enabled_reschedules_timer():
    app = _DummyEditor()
    app._preview_auto_refresh_on_edit_idle_enabled = True
    app._preview_auto_refresh_on_edit_idle_delay_ms = 1500
    app._preview_auto_refresh_after_id = "timer-old"

    app._queue_editor_auto_preview_refresh()

    assert app.root.after_cancel_calls == ["timer-old"]
    assert len(app.root.after_calls) == 1
    assert app.root.after_calls[0][0] == 1500
    assert app._preview_auto_refresh_after_id == "timer-1"


def test_run_editor_auto_preview_refresh_saves_and_rebuilds_preview():
    app = _DummyEditor()
    app._preview_auto_refresh_on_edit_idle_enabled = True
    app._editor_save_after_id = "save-1"
    app._editor_has_unsaved_changes = True

    app._run_editor_auto_preview_refresh()

    assert app.root.after_cancel_calls == ["save-1"]
    assert app.save_calls == [True]
    assert app.refresh_calls == [True]


def test_run_editor_auto_preview_refresh_skips_preview_when_save_fails():
    app = _DummyEditor()
    app._preview_auto_refresh_on_edit_idle_enabled = True
    app._editor_has_unsaved_changes = True
    app._save_sets_unsaved_false = False

    app._run_editor_auto_preview_refresh()

    assert app.save_calls == [True]
    assert app.refresh_calls == []


def test_compile_now_cancels_pending_idle_auto_refresh_timer():
    # This is the exact bug being fixed: manual compile must cancel the
    # pending debounce timer, not let it fire again redundantly afterward.
    app = _DummyEditor()
    app._preview_auto_refresh_after_id = "timer-old"

    app._compile_now()

    assert "timer-old" in app.root.after_cancel_calls
    assert app._preview_auto_refresh_after_id is None


def test_compile_now_flushes_unsaved_changes_before_building():
    app = _DummyEditor()
    app._editor_save_after_id = "save-1"
    app._editor_has_unsaved_changes = True

    app._compile_now()

    assert "save-1" in app.root.after_cancel_calls
    assert app._editor_save_after_id is None
    assert app.save_calls == [True]
    assert app.refresh_calls == [False]


def test_compile_now_skips_build_when_save_fails():
    app = _DummyEditor()
    app._editor_has_unsaved_changes = True
    app._save_sets_unsaved_false = False

    app._compile_now()

    assert app.save_calls == [True]
    assert app.refresh_calls == []


def test_compile_now_defaults_to_cache_aware_rebuild():
    app = _DummyEditor()

    app._compile_now()

    assert app.refresh_calls == [False]


def test_compile_now_forwards_force_rebuild_flag():
    app = _DummyEditor()

    app._compile_now(force_rebuild=True)

    assert app.refresh_calls == [True]


def test_compile_now_without_pending_timer_still_builds():
    app = _DummyEditor()
    app._preview_auto_refresh_after_id = None

    app._compile_now()

    assert app.refresh_calls == [False]