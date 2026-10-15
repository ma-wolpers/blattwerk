"""Regressionstest: Hauptfenster-Kürzel über den bw-gui-``WindowShortcutBinder`` (KeySpec, exakt).

Früher band ``ShortcutManager`` Tk-Sequenzen und wertete ``state & 0x0008`` als
"Alt gedrückt" -- unter Windows ist das das NumLock-Bit, weshalb Einbuchstaben-
Kürzel bei eingeschaltetem NumLock nicht auslösten. Jetzt bindet
``_install_window_shortcuts`` die Registry-Definitionen an einen bw-gui-Binder; die
Modifier-Deutung liegt vollständig im Contract. Tastendrücke laufen ohne OS-Fokus
über ``bw_gui.testing.keys.press_key``; die Zustandswerte sind die gemessenen
win32-Werte.
"""

from __future__ import annotations

import tkinter

import pytest

from app.ui.blatt_ui_shortcut_runtime import BlattwerkShortcutRuntimeMixin
from app.ui.ui_constants import EDITOR_VIEW_PREVIEW_ONLY
from bw_gui.contracts.hsm import build_ui_hsm_contract
from bw_gui.contracts.key_spec import KeySpec
from bw_gui.contracts.keybinding import UI_MODE_DIALOG, UI_MODE_GLOBAL, KeyBindingDefinition, KeybindingRegistry
from bw_gui.runtime import create_root, ui
from bw_gui.testing.keys import press_key

SHIFT, CAPSLOCK, CONTROL, NUMLOCK, ALT_WIN32 = 0x0001, 0x0002, 0x0004, 0x0008, 0x20000


@pytest.fixture(scope="module")
def root():
    """Ein zurückgezogener Tk-Root mit bw-gui-Router (Retry bei der Tcl-Init-Race unter Windows)."""
    for attempt in range(3):
        try:
            instance = create_root()
            break
        except tkinter.TclError as exc:
            if "usable" not in str(exc) or attempt == 2:
                raise
    instance.withdraw()
    yield instance
    instance.destroy()


class _Host(BlattwerkShortcutRuntimeMixin):
    """Minimaler Host: echte Binder-Installation, eigene kleine Registry."""

    def __init__(self, root) -> None:
        self.root = root
        self.calls: list[str] = []
        self.keybinding_registry = KeybindingRegistry()
        modes = (UI_MODE_GLOBAL, UI_MODE_DIALOG)
        self.keybinding_registry.register_many(
            [
                KeyBindingDefinition("global.open_recent", KeySpec.parse("Z"), "global.open_recent", (UI_MODE_GLOBAL,),
                                     handler=lambda: self.calls.append("z")),
                KeyBindingDefinition("global.help_preview", KeySpec.parse("Ctrl+Shift+H"), "global.help_preview", modes,
                                     allow_when_text_input=True, handler=lambda: self.calls.append("help")),
            ]
        )
        self.hsm_contract = build_ui_hsm_contract(intents=[d.intent for d in self.keybinding_registry.all()])
        self.shortcut_debug_offline_var = ui.BooleanVar(root, value=False)
        self.editor_view_mode_var = ui.StringVar(root, value=EDITOR_VIEW_PREVIEW_ONLY)

    def _has_dialog_context(self) -> bool:
        return False

    def _record_laufkern_intent_dispatch(self, intent: str, *, success: bool) -> None:
        self.calls.append(f"track:{intent}:{success}")


@pytest.fixture
def host(root):
    instance = _Host(root)
    instance._install_window_shortcuts()
    yield instance
    instance._window_shortcut_binder.dispose()


def test_plain_letter_fires_with_numlock_and_capslock_and_is_blocked_by_ctrl_alt(host, root):
    for state in (0, NUMLOCK, CAPSLOCK):
        assert press_key(root, "z", char="z", state=state) is True
    for state in (CONTROL, ALT_WIN32, SHIFT):
        press_key(root, "Z" if state == SHIFT else "z", state=state)
    assert [c for c in host.calls if not c.startswith("track")] == ["z", "z", "z"]


def test_ctrl_shift_letter_fires_without_capslock_and_is_exact(host, root):
    assert press_key(root, "H", state=CONTROL | SHIFT | NUMLOCK) is True
    press_key(root, "H", state=CONTROL | SHIFT | ALT_WIN32)
    assert [c for c in host.calls if not c.startswith("track")] == ["help"]
    assert "track:global.help_preview:True" in host.calls
