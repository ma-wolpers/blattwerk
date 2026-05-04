"""Startskript für die grafische Blattwerk-Anwendung."""

from __future__ import annotations

import sys

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()


def _show_start_error(message: str) -> None:
    """Zeigt Startfehler im Dialog (pythonw) und in der Konsole an."""
    try:
        from bw_gui.dialogs import MessageDialogService

        MessageDialogService().showerror("Blattwerk Startfehler", message)
    except Exception:
        pass
    print(message, file=sys.stderr)


def main() -> int:
    """Startet die GUI und behandelt fehlende Laufzeitabhängigkeiten sauber."""
    try:
        from app.ui.blatt_ui import run_gui
    except ModuleNotFoundError as exc:
        missing_name = str(getattr(exc, "name", "") or "").strip() or "unbekannt"
        _show_start_error(
            "Blattwerk konnte nicht gestartet werden, weil ein Python-Paket fehlt.\n\n"
            f"Fehlendes Paket: {missing_name}\n\n"
            "Bitte im Ordner Code/blattwerk die Abhängigkeiten installieren:\n"
            "1) .venv aktivieren\n"
            "2) pip install -r requirements.txt"
        )
        return 1

    run_gui()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
