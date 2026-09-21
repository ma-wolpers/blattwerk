"""Startskript für die grafische Blattwerk-Anwendung."""

from __future__ import annotations

import atexit
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


def _report_missing_package(exc: ModuleNotFoundError) -> int:
    """Zeigt den Installationshinweis für ein fehlendes Python-Paket und liefert den Exit-Code."""
    missing_name = str(getattr(exc, "name", "") or "").strip() or "unbekannt"
    _show_start_error(
        "Blattwerk konnte nicht gestartet werden, weil ein Python-Paket fehlt.\n\n"
        f"Fehlendes Paket: {missing_name}\n\n"
        "Bitte im Ordner Code/blattwerk die Abhängigkeiten installieren:\n"
        "1) .venv aktivieren\n"
        "2) pip install -r requirements.txt"
    )
    return 1


def main() -> int:
    """Startet die GUI (oder übergibt die Datei an ein laufendes Fenster).

    Reihenfolge ist Absicht: Port belegen bzw. Datei an die laufende Instanz übergeben
    passiert *vor* dem Import der schweren GUI-Module -- die Übergabe eines Folgestarts
    (z. B. "Öffnen mit") soll sich sofort anfühlen, und es entsteht kein zweites Fenster.
    """
    try:
        from app.bootstrap.single_instance import InstanceServer, forward_to_running_instance, startup_file_from_argv
    except ModuleNotFoundError as exc:
        return _report_missing_package(exc)

    startup_file = startup_file_from_argv(sys.argv[1:])

    # Claim the port *before* the slow GUI import: "Öffnen mit" on several files starts
    # several processes at once, and all of them must see the same single winner. Binding
    # first (instead of probing with a connection) also costs nothing: Windows needs ~1 s
    # to refuse a connection to a port nobody listens on.
    server: InstanceServer | None = InstanceServer()
    if not server.start():
        # Someone else holds the port: hand the file over (if it is a Blattwerk that answers).
        if forward_to_running_instance(startup_file):
            return 0
        server = None

    try:
        from app.ui.blatt_ui import run_gui
    except ModuleNotFoundError as exc:
        if server is not None:
            server.stop()
        return _report_missing_package(exc)

    from app.core.block_computation_cache import cleanup_session_caches

    atexit.register(cleanup_session_caches)

    run_gui(startup_file=startup_file, instance_server=server)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
