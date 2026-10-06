"""Regressionstest: ShortcutManager wertet Modifier über den bw-gui-Contract aus (NumLock-Fix).

Früher galt ``state & 0x0008`` als "Alt gedrückt" -- unter Windows ist das aber das
NumLock-Bit, weshalb Einbuchstaben-Kürzel bei eingeschaltetem NumLock nicht
auslösten. Die Zustandswerte hier sind die live gemessenen win32-Werte; das Backend
wird auf win32 fixiert, damit der Test auf jeder Plattform dasselbe prüft.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import bw_gui.contracts.key_modifiers as key_modifiers
from app.ui.shortcut_manager import ShortcutBinding, ShortcutManager

NUMLOCK, CONTROL, ALT_WIN32 = 0x0008, 0x0004, 0x20000


class _FakeRoot:
    """Zeichnet ``bind`` auf; ``fire`` ruft das gebundene Skript mit einem Event auf."""

    def __init__(self) -> None:
        self.scripts = {}

    def bind(self, sequence, func):
        """Speichert das Skript für *sequence*."""
        self.scripts[sequence] = func

    def fire(self, sequence, state):
        """Löst *sequence* mit dem Zustand *state* aus."""
        return self.scripts[sequence](SimpleNamespace(state=state, widget=None))


@pytest.fixture(autouse=True)
def _win32_backend(monkeypatch):
    monkeypatch.setattr(key_modifiers.sys, "platform", "win32")


def _manager_with(binding_kwargs):
    root = _FakeRoot()
    calls = []
    ShortcutManager(root).bind_all([ShortcutBinding(action=lambda: calls.append(1), **binding_kwargs)])
    return root, calls


def test_plain_letter_fires_with_numlock_and_is_blocked_by_ctrl_alt_unknown():
    root, calls = _manager_with({"sequence": "<KeyPress-z>"})
    results = [root.fire("<KeyPress-z>", state) for state in (0, NUMLOCK, CONTROL, ALT_WIN32, "??")]
    assert calls == [1, 1]
    assert results == ["break", "break", None, None, None]


def test_allow_modifiers_bindings_still_fire_with_ctrl():
    root, calls = _manager_with({"sequence": "<Control-e>", "allow_modifiers": True})
    root.fire("<Control-e>", CONTROL | NUMLOCK)
    assert calls == [1]
