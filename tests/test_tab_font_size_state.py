from pathlib import Path

from app.ui.blatt_ui_base import BlattwerkAppBase


class _Var:
    def __init__(self, value=None):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _DummyBase:
    _normalize_document_path = staticmethod(BlattwerkAppBase._normalize_document_path)
    _build_document_tab_state = BlattwerkAppBase._build_document_tab_state
    _persist_active_document_tab_state = BlattwerkAppBase._persist_active_document_tab_state
    _apply_document_tab_state = BlattwerkAppBase._apply_document_tab_state

    def __init__(self):
        self.input_var = _Var("")
        self.preview_mode_var = _Var("worksheet")
        self.preview_page_format_var = _Var("a4_portrait")
        self.preview_section_separator_var = _Var("dot")
        self.preview_hide_future_sections_var = _Var(False)
        self.preview_contrast_var = _Var("standard")
        self.design_color_profile_var = _Var("indigo")
        self.design_font_profile_var = _Var("segoe")
        self.design_font_size_profile_var = _Var("normal")
        self.preview_fit_mode_var = _Var("fit_width")
        self.preview_layout_mode_var = _Var("single")
        self.status_var = _Var("")
        self.zoom_percent = 100
        self.current_page_index = 0
        self.preview_canvas = None
        self.document_tabs = {}
        self._active_document_tab_id = None
        self._tab_switch_in_progress = False

    @staticmethod
    def _clean_path_text(value: str) -> str:
        return str(value or "").strip()

    def _sync_font_profile_combo(self):
        return None

    def _sync_font_size_profile_combo(self):
        return None

    def _refresh_color_profile_swatches(self):
        return None

    def _load_editor_content(self, _path: Path):
        return None

    def _warn_if_bw_mode_has_color_mentions(self):
        return None

    def _refresh_preview_for_active_tab(self):
        return None


def test_new_document_tab_state_does_not_store_font_size_profile(tmp_path):
    dummy = _DummyBase()
    md_file = tmp_path / "doc.md"
    md_file.write_text("# x\n", encoding="utf-8")

    tab_state = dummy._build_document_tab_state(md_file)

    assert "font_size_profile" not in tab_state


def test_apply_document_tab_state_ignores_legacy_font_size_profile(tmp_path):
    dummy = _DummyBase()
    md_file = tmp_path / "doc.md"
    md_file.write_text("# x\n", encoding="utf-8")
    normalized = dummy._normalize_document_path(md_file)

    dummy.design_font_size_profile_var.set("large")
    dummy.document_tabs["tab-1"] = {
        "path": normalized,
        "preview_mode": "worksheet",
        "page_format": "a4_portrait",
        "section_separator": "dot",
        "hide_future_sections": False,
        "contrast": "standard",
        "color_profile": "indigo",
        "font_profile": "segoe",
        "font_size_profile": "small",
        "fit_mode": "fit_width",
        "layout_mode": "single",
        "zoom_percent": 110,
        "current_page_index": 0,
    }

    dummy._apply_document_tab_state("tab-1")

    assert dummy.design_font_size_profile_var.get() == "large"


def test_persist_active_tab_state_does_not_rewrite_legacy_font_size_profile(tmp_path):
    dummy = _DummyBase()
    md_file = tmp_path / "doc.md"
    md_file.write_text("# x\n", encoding="utf-8")
    normalized = dummy._normalize_document_path(md_file)

    dummy.input_var.set(str(md_file))
    dummy._active_document_tab_id = "tab-1"
    dummy.document_tabs["tab-1"] = {
        "path": normalized,
        "font_size_profile": "small",
    }
    dummy.design_font_size_profile_var.set("large")

    dummy._persist_active_document_tab_state()

    assert dummy.document_tabs["tab-1"].get("font_size_profile") == "small"
