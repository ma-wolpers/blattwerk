"""Charakterisierung: frühere Popup-Registry + Toplevel-Scan gegen den bw-gui-Overlay-Stack (echtes Tk).

Bis 2026-10-15 führte Blattwerk eine ``PopupPolicyRegistry``: Fenster meldeten sich per
``_track_popup_window`` an (Hilfe-Doku und Shortcut-Debug als ``dialog.non_blocking``,
der Dokumenttyp-Dialog modal), und vor jeder Prüfung ergänzte ein Scan jedes sichtbare
direkte Kind-Toplevel des Roots als ``dialog.modal`` (Export-Dialoge, Lernhilfen-Vorschau,
Konfliktdialog, Vervollständigungsliste, Menü-Popups, Farbprofil-Tooltip) bzw. entfernte
nicht mehr sichtbare. ``_has_dialog_context`` prüfte zusätzlich offene Menü-Popups;
Escape aus dem Hauptfenster schloss das zuletzt geöffnete Popup.

:class:`_FormerRegistry` konserviert diesen Ablauf. Jetzt liefern
``BlattwerkShortcutRuntimeMixin._has_dialog_context`` (``blocking(include_menus=True)``)
und ``bw_gui.runtime.topmost_window`` beides. Für jede Popup-Art und für Kombinationen
müssen alt und neu übereinstimmen -- mit einer bewussten Ausnahme: der Farbprofil-Tooltip
zählte nur zufällig als Dialog (sperrte beim Überfahren eines Farbfelds alle Kürzel) und
ist jetzt ``TRANSIENT``. Nur synthetische Fenster, keine Dokumente.
"""

from __future__ import annotations

import tkinter
from types import SimpleNamespace

import pytest

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.menu.custom_menu_bar import CustomMenuBar  # noqa: E402
from bw_gui.menu.menu_types import MenuItem  # noqa: E402
from bw_gui.runtime import create_root, topmost_window, ui  # noqa: E402
from bw_gui.runtime.overlay_stack import OverlayCategory, register_overlay, unregistered_visible_toplevels  # noqa: E402

from app.ui.blatt_ui_shortcut_runtime import BlattwerkShortcutRuntimeMixin  # noqa: E402


class _FormerRegistry:
    """Referenz: frühere Registry (Öffnungsreihenfolge) + Scan + Menü-Prüfung."""

    def __init__(self, root):
        self.root = root
        self.menu_bar = None
        self.stack: list[tuple[str, bool]] = []  # (popup_id, blocks)

    def track(self, window, *, blocks: bool = True) -> None:
        if all(pid != str(window) for pid, _ in self.stack):
            self.stack.append((str(window), blocks))

    def sync(self) -> None:
        visible = set()
        for child in self.root.winfo_children():
            if not isinstance(child, ui.Toplevel) or str(child.state()).lower() == "withdrawn":
                continue
            visible.add(str(child))
            self.track(child)
        self.stack = [(pid, blocks) for pid, blocks in self.stack if pid in visible]

    def dialog_open(self) -> bool:
        self.sync()
        if self.menu_bar is not None and bool(self.menu_bar._popup_stack):
            return True
        return any(blocks for _pid, blocks in self.stack)

    def escape_target(self) -> str | None:
        self.sync()
        return self.stack[-1][0] if self.stack else None


@pytest.fixture(scope="module")
def root():
    """Sichtbarer Root (transiente Popups eines versteckten Masters blieben versteckt)."""
    for attempt in range(3):
        try:
            instance = create_root()
            break
        except tkinter.TclError as exc:
            if not any(m in str(exc) for m in ("usable", "tcl_findLibrary", "init.tcl")) or attempt == 2:
                raise
    instance.geometry("300x200+30+30")
    instance.update()
    yield instance
    instance.destroy()


@pytest.fixture
def scene(root):
    host = SimpleNamespace(root=root)
    former = _FormerRegistry(root)
    opened: list[object] = []

    class Scene:
        def modal(self, *, tracked: bool):
            """Dokumenttyp (früher getrackt) bzw. Export/Vorschau/Konflikt (früher nur gescannt)."""
            window = ui.Toplevel(root)
            window.transient(root)
            BlattwerkShortcutRuntimeMixin._register_popup_window(host, window)
            if tracked:
                former.track(window)
            opened.append(window)
            return window

        def tool_window(self):
            """Hilfe-Doku / Shortcut-Debug."""
            window = ui.Toplevel(root)
            BlattwerkShortcutRuntimeMixin._register_popup_window(host, window, blocking_shortcuts=False)
            former.track(window, blocks=False)
            opened.append(window)
            return window

        def completion(self):
            """Vervollständigungsliste: einmal erzeugt, dann gezeigt/versteckt (wie im Editor)."""
            popup = ui.Toplevel(root)
            popup.withdraw()
            popup.overrideredirect(True)
            popup.transient(root)
            state = {"overlay": None}

            def show():
                popup.deiconify()
                if state["overlay"] is None or not state["overlay"].active:
                    state["overlay"] = register_overlay(popup, OverlayCategory.MENU, toplevel=popup)

            def hide():
                popup.withdraw()
                if state["overlay"] is not None:
                    state["overlay"].remove()

            opened.append(popup)
            return popup, show, hide

        def swatch_tooltip(self):
            tooltip = ui.Toplevel(root)
            register_overlay(tooltip, OverlayCategory.TRANSIENT, toplevel=tooltip)
            tooltip.overrideredirect(True)
            opened.append(tooltip)
            return tooltip

        def menu(self):
            bar = CustomMenuBar(root, (), theme_key="mono_day")
            former.menu_bar = bar
            anchor = ui.Frame(root, width=40, height=20)
            anchor.place(x=10, y=10)
            root.update_idletasks()
            # Fokus-Watchdog für die Szene aussetzen (sonst schliesst er das Popup, sobald
            # Testfenster den Fokus zurückholen; wie bw-gui test_menu_popup_placement).
            suspended = bar._focus_watchdog_suspended()
            suspended.__enter__()
            bar.open_popup(anchor, (MenuItem(type="command", label="Eins"),), 0, "datei")
            opened.append((bar, anchor, suspended))
            return bar._popup_stack[0]

        def new(self):
            root.update()
            target = topmost_window(root)
            return BlattwerkShortcutRuntimeMixin._has_dialog_context(host), (str(target) if target is not None else None)

        def old(self):
            root.update()
            return former.dialog_open(), former.escape_target()

        def check(self):
            new = self.new()
            assert new == self.old()
            assert unregistered_visible_toplevels(root) == []
            return new

    yield Scene()
    for item in reversed(opened):
        try:
            if isinstance(item, tuple):
                bar, anchor, suspended = item
                bar.close_popups_from_level(0)
                suspended.__exit__(None, None, None)
                anchor.destroy()
            else:
                item.destroy()
        except tkinter.TclError:
            pass
    root.update()


def test_nothing_open(scene):
    assert scene.check() == (False, None)


def test_modal_dialogs_tracked_or_scanned(scene):
    first = scene.modal(tracked=True)
    assert scene.check() == (True, str(first))
    second = scene.modal(tracked=False)
    assert scene.check() == (True, str(second))


def test_tool_windows_do_not_block(scene):
    tool = scene.tool_window()
    assert scene.check() == (False, str(tool))


def test_completion_list_blocks_only_while_visible(scene):
    popup, show, hide = scene.completion()
    assert scene.check() == (False, None)
    show()
    assert scene.check() == (True, str(popup))
    hide()
    assert scene.check() == (False, None)
    show()
    assert scene.check() == (True, str(popup))


def test_menu_popup_blocks(scene):
    popup = scene.menu()
    assert scene.check() == (True, str(popup))


def test_swatch_tooltip_is_a_deliberate_change(scene):
    """Früher sperrte der Farbprofil-Tooltip (sichtbares Root-Kind) alle Kürzel; jetzt TRANSIENT."""
    scene.swatch_tooltip()
    old_open, old_target = scene.old()
    assert old_open is True and old_target is not None
    assert scene.new() == (False, None)


def test_combinations_and_closing(scene):
    tool = scene.tool_window()
    modal = scene.modal(tracked=False)
    popup, show, _hide = scene.completion()
    show()
    assert scene.check() == (True, str(popup))
    popup.destroy()
    assert scene.check() == (True, str(modal))
    modal.destroy()
    assert scene.check() == (False, str(tool))
