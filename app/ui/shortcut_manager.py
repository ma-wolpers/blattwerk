"""Generische Verwaltung von Tastaturkürzeln für Tkinter-Views."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable
import tkinter as tk


@dataclass(frozen=True)
class ShortcutBinding:
    """Definition eines Shortcuts inkl. optionaler Menübeschriftung."""

    sequence: str
    action: Callable[[], None]
    menu_label: str | None = None
    ignore_when_text_input: bool = True
    allow_modifiers: bool = False
    binding_id: str = ""
    can_execute: Callable[[], tuple[bool, str]] | None = None


class ShortcutManager:
    """Bindet Shortcuts robust und liefert deduplizierte Menülabels."""

    def __init__(self, root: tk.Misc):
        self.root = root

    def bind_all(self, bindings: Iterable[ShortcutBinding]):
        for binding in bindings:
            self.root.bind(
                binding.sequence,
                lambda event, definition=binding: self._dispatch(definition, event),
            )

    @staticmethod
    def iter_menu_labels(bindings: Iterable[ShortcutBinding]):
        seen = set()
        for binding in bindings:
            label = binding.menu_label
            if not label or label in seen:
                continue
            seen.add(label)
            yield label

    def _dispatch(self, binding: ShortcutBinding, event):
        if self._has_modifier_keys(event) and not binding.allow_modifiers:
            return None

        if binding.ignore_when_text_input and self._is_text_input_widget(
            getattr(event, "widget", None)
        ):
            return None

        if binding.can_execute is not None:
            can_execute, _reason = binding.can_execute()
            if not can_execute:
                return None

        binding.action()
        return "break"

    @staticmethod
    def _is_text_input_widget(widget):
        if widget is None:
            return False

        widget_class = widget.winfo_class().lower()
        return widget_class in {
            "entry",
            "ttk::entry",
            "text",
            "spinbox",
            "ttk::combobox",
        }

    @staticmethod
    def _has_modifier_keys(event):
        state = int(getattr(event, "state", 0))
        control_pressed = bool(state & 0x0004)
        alt_pressed = bool(state & 0x0008)
        return control_pressed or alt_pressed
