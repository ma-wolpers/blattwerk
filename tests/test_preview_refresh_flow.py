"""Ablauf der echten `refresh_preview`: wann gedruckt wird und wann der Cache reicht."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.core.render_job import note_file_dependency
from app.ui.blatt_ui_preview import BlattwerkAppPreviewMixin
from app.ui.preview_page_cache import PreviewPageCache


class _Var:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _Host(BlattwerkAppPreviewMixin):
    """Echte `refresh_preview`, nur Oberfläche und Druck sind ersetzt."""

    def __init__(self, path: Path, image: Path | None = None):
        self.path = path
        self.image = image
        self.renders = []
        self.warnings = []
        self.help_refreshes = 0
        self.tab = {"path": str(path), "current_page_index": 0, "zoom_percent": 100}
        self.help_preview_window = None
        self.preview_images = []
        self.current_page_index = 0
        self.zoom_percent = 100
        self._last_preview_input_path = None
        self._preview_page_cache = PreviewPageCache()
        self.status_var = _Var()
        self.preview_mode_var = _Var("worksheet")
        self.preview_page_format_var = _Var("a4_portrait")
        self.preview_contrast_var = _Var("standard")
        self.preview_black_screen_var = _Var("none")
        self.preview_section_separator_var = _Var("dot")
        self.preview_hide_future_sections_var = _Var(False)
        self.preview_help_appendix_var = _Var("none")
        self.user_preferences = {}
        self.copyright = "alt"
        self.root = type("Root", (), {"update_idletasks": staticmethod(lambda: None)})()
        canvas = type("Canvas", (), {"xview": staticmethod(lambda: (0.0, 1.0)), "yview": staticmethod(lambda: (0.0, 1.0))})
        self.preview_canvas = canvas()

    def _validate_input(self):
        return self.path

    def _read_document_type(self, _path):
        return "worksheet"

    def _active_document_tab_state(self):
        return self.tab

    def _worksheet_design_options(self):
        return "design"

    def _copyright_text_from_preferences(self):
        return self.copyright

    def _render_pdf_pages(self, input_path, include_solutions, page_format, contrast_profile, preview_variant="worksheet"):
        self.renders.append(preview_variant)
        if self.image is not None:
            note_file_dependency(self.image)
        return [Image.new("RGB", (10, 10))], []

    def _show_compile_overflow_warnings(self, diagnostics, context):
        self.warnings.append((tuple(diagnostics), context))

    def _refresh_help_preview(self, *_args):
        self.help_refreshes += 1

    def _show_document_diagnostics(self, *_args):
        pass

    def _apply_preview_mode_controls(self, *_args):
        pass

    def _apply_preview_page_format_controls(self, *_args):
        pass

    def _show_current_page(self, **_kwargs):
        pass

    def _refresh_zoom_label(self):
        pass

    def _update_nav_buttons(self):
        pass


@pytest.fixture
def host(tmp_path):
    path = tmp_path / "blatt.abw"
    path.write_text("Inhalt", encoding="utf-8")
    return _Host(path)


def test_second_refresh_comes_from_the_cache(host):
    host.refresh_preview()
    host.refresh_preview()
    assert host.renders == ["worksheet"]
    assert host.status_var.get() == "Vorschau aus Cache geladen"


def test_switching_a_view_back_needs_no_new_print(host):
    host.refresh_preview()
    host.preview_page_format_var.set("a5_landscape")
    host.refresh_preview()
    host.preview_page_format_var.set("a4_portrait")
    host.refresh_preview()
    assert len(host.renders) == 2


def test_forced_rebuild_prints_again(host):
    host.refresh_preview()
    host.refresh_preview(force_rebuild=True)
    assert len(host.renders) == 2


def test_saving_identical_content_stays_a_hit(host):
    host.refresh_preview()
    host.path.write_text("Inhalt", encoding="utf-8")
    host.refresh_preview()
    assert len(host.renders) == 1


def test_changed_content_prints_again(host):
    host.refresh_preview()
    host.path.write_text("Neu", encoding="utf-8")
    host.refresh_preview()
    assert len(host.renders) == 2


def test_changed_copyright_prints_again(host):
    """Regression: Copyright und Metadaten-Vorgaben fehlten im Schlüssel."""
    host.refresh_preview()
    host.copyright = "neu"
    host.refresh_preview()
    assert len(host.renders) == 2


def test_image_that_appears_later_prints_again(tmp_path):
    path = tmp_path / "blatt.abw"
    path.write_text("Inhalt", encoding="utf-8")
    image = tmp_path / "bild.png"
    host = _Host(path, image)
    host.refresh_preview()
    host.refresh_preview()
    assert len(host.renders) == 1
    image.write_bytes(b"da")
    host.refresh_preview()
    assert len(host.renders) == 2


def test_warnings_also_run_on_a_cache_hit(host):
    host.refresh_preview()
    host.refresh_preview()
    assert len(host.warnings) == 2


def test_open_help_window_is_only_refreshed_on_change(host):
    host.help_preview_window = type("Window", (), {"winfo_exists": staticmethod(lambda: True)})()
    host.refresh_preview()
    host.refresh_preview()
    assert host.help_refreshes == 1
    host.refresh_preview(force_rebuild=True)
    assert host.help_refreshes == 2
    host.path.write_text("Neu", encoding="utf-8")
    host.refresh_preview()
    assert host.help_refreshes == 3
