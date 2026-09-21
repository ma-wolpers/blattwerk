"""Files handed over from outside: the command line and later Blattwerk starts."""

from __future__ import annotations

import queue
from pathlib import Path

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()

from .dialog_services import messagebox

_EXTERNAL_OPEN_POLL_MS = 250
_RAISE_TOPMOST_MS = 200


class BlattwerkAppExternalOpenMixin:
    """Öffnet Dateien aus Kommandozeile und Folgestarts im bestehenden Fenster."""

    def start_external_open_listener(self, server) -> None:
        """Open the startup file and begin draining *server*'s request queue on the Tk thread.

        Called once before the event loop starts. The first poll runs as soon as the
        loop does, opens the startup file (command line) *before* any queued request
        (deterministic tab order), then keeps polling. The server thread must never
        touch Tk, so requests are polled here (``after``) instead of being pushed.

        Args:
            server: A started ``InstanceServer``, or ``None`` when this instance could
                not claim the port; the startup file is then opened once and no
                further polling happens.
        """
        self._instance_server = server
        self.root.after(0, self._poll_external_open_requests)

    def _open_external_path_reporting_errors(self, path_text: str, *, raise_window: bool) -> None:
        """Open a path; show a dialog instead of raising so the poll loop survives a bad file."""
        try:
            self.open_external_path(path_text, raise_window=raise_window)
        except Exception as exc:
            messagebox.showerror("Datei konnte nicht geöffnet werden", f"{path_text}\n\n{exc}")

    @staticmethod
    def _drain_queued_requests(server) -> list:
        """Return every queued request in arrival order (empty without a server)."""
        drained = []
        while server is not None:
            try:
                drained.append(server.requests.get_nowait())
            except queue.Empty:
                break
        return drained

    def _poll_external_open_requests(self) -> None:
        """Report liveness, open the startup file once, then the queued requests; re-arm the timer.

        The heartbeat comes first: waiting clients are acknowledged on liveness alone, not
        after their file is open - opening renders a preview and can take many seconds
        (and several parallel starts queue up behind each other).
        """
        server = getattr(self, "_instance_server", None)
        if server is not None:
            server.heartbeat()
        requests = self._drain_queued_requests(server)
        startup_file = getattr(self, "_startup_file", None)
        if startup_file:
            self._startup_file = None
            self._open_external_path_reporting_errors(startup_file, raise_window=False)
        for request in requests:
            self._open_external_path_reporting_errors(request.path, raise_window=True)
        if server is not None:
            self.root.after(_EXTERNAL_OPEN_POLL_MS, self._poll_external_open_requests)

    def open_external_path(self, path_text: str, *, raise_window: bool) -> None:
        """Open *path_text* as a tab (or focus its existing tab) and optionally raise the window.

        Args:
            path_text: Absolute path from the command line or another start;
                empty means "only raise the window".
            raise_window: Bring the window to the front. Windows may refuse to
                steal the foreground; the taskbar button then flashes instead.
        """
        if raise_window:
            self._raise_main_window()
        if not path_text:
            return
        path = Path(path_text)
        if not path.is_file():
            messagebox.showerror("Datei nicht gefunden", f"Die Datei existiert nicht:\n{path}")
            return
        self._open_input_path(path, add_recent=True, show_duplicate_message=False)

    def _raise_main_window(self) -> None:
        """Best-effort: restore from minimized and bring the window to the front."""
        root = self.root
        root.deiconify()
        root.lift()
        root.attributes("-topmost", True)
        root.after(_RAISE_TOPMOST_MS, lambda: root.attributes("-topmost", False))
        root.focus_force()
