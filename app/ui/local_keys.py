"""Fenster- und widgetlokale Kürzel sowie Mausrad-Logik über die bw-gui-Contracts.

Blattwerk bindet keine Tk-Sequenzen mehr (``widget.bind("<Left>", ...)``):

* :func:`bind_actions` bindet parameterlose Aktionen an einen ``WindowShortcutBinder``
  (Toplevel-Tag eines Dialogs/Fensters) oder ``WidgetShortcutBinder``; eine
  ausgeführte Aktion verbraucht die Taste (``HANDLED``), wie früher ``"break"``.
* :func:`scroll_or_zoom` ist die gemeinsame Mausrad-Regel der Vorschauen: Strg
  zoomt, Shift scrollt horizontal, sonst vertikal -- in ganzen Rasten
  (``WheelEvent.whole_steps``; kleine Touchpad-Deltas sammeln sich).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.contracts import KeyModifiers
from bw_gui.contracts.events import EventResult
from bw_gui.contracts.key_spec import KeySpec
from bw_gui.contracts.pointer import Axis, WheelEvent, wheel_axis

KeyRow = tuple[KeySpec | list[KeySpec], str, Callable[[], object]]


def bind_actions(binder: Any, rows: Iterable[KeyRow], *, text: bool, prefix: str) -> None:
    """Bindet jede Zeile ``(keys, binding_id, action)`` an *binder*.

    Args:
        binder: ``WindowShortcutBinder`` oder ``WidgetShortcutBinder``.
        rows: Tasten (eine Spec oder Alternativen), ID-Suffix, parameterlose Aktion.
        text: Auch aktiv, während ein Texteingabe-Widget den Fokus hat.
        prefix: Präfix für Binding-ID und Intent (``f"{prefix}.{binding_id}"``).
    """
    for keys, binding_id, action in rows:

        def _run(_event, action=action) -> EventResult:
            action()
            return EventResult.HANDLED

        full_id = f"{prefix}.{binding_id}"
        binder.bind(keys, _run, binding_id=full_id, intent=full_id, allow_when_text_input=text)


def scroll_or_zoom(event: WheelEvent, canvas: Any, change_zoom: Callable[[int], object]) -> bool:
    """Wendet ein Mausrad-Ereignis auf eine Vorschau an.

    Args:
        event: bw-gui-``WheelEvent`` (positiv = zum Inhaltsende).
        canvas: Der zu scrollende Canvas.
        change_zoom: ``change_zoom(delta_percent)``; Rad hoch mit Strg = +10 %.

    Returns:
        ``True``, wenn gescrollt wurde (nicht bei Zoom oder Bruchteil einer Raste).
    """
    steps = event.whole_steps
    if steps == 0:
        return False
    modifiers = event.modifiers if isinstance(event.modifiers, KeyModifiers) else None
    if modifiers is not None and modifiers.control:
        for _ in range(abs(steps)):
            change_zoom(-10 if steps > 0 else 10)
        return False
    if wheel_axis(event) is Axis.HORIZONTAL:
        canvas.xview_scroll(steps, "units")
    else:
        canvas.yview_scroll(steps, "units")
    return True
