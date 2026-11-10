"""Chromium über das DevTools-Protokoll steuern, per Pipe statt Port (nur Transport).

Warum eine Pipe: Ein Debug-Port wäre für jedes lokale Programm erreichbar, und ein
abgestürztes Blattwerk hinterließe einen laufenden Browser. Bei einer Pipe schließt das
Betriebssystem die Enden mit dem Prozess, und Chromium beendet sich von selbst.

Dieses Modul kennt nur Nachrichten: Start, `call`, `wait_event`, `close`. Was gedruckt wird,
steht in `pdf_printers`. Nachrichten sind JSON, getrennt durch ein Nullbyte. Ein Lese-Thread
legt jede Nachricht in eine Warteschlange, damit jedes Warten ein Zeitlimit hat und ein
hängender Browser nie die GUI blockiert.

GRENZE: Nur Windows. Unter POSIX müsste die Pipe auf die Dateideskriptoren 3 und 4 des
Kindprozesses gelegt werden; ohne Testrechner dafür meldet `pipe_supported` dort False,
und der Druck läuft über die Kommandozeile.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time

PIPE_SWITCH = "--remote-debugging-pipe"


class DevToolsError(RuntimeError):
    """Der Browser antwortet nicht, falsch oder gar nicht mehr."""


def pipe_supported() -> bool:
    """Ob dieses System den Pipe-Start kann (siehe GRENZE im Modul-Docstring)."""
    return sys.platform == "win32"


class PipeConnection:
    """Ein laufender Chromium-Prozess mit seiner DevTools-Pipe.

    Nicht threadsicher: Genau ein Aufrufer zugleich, das sichert `print_service` mit einem
    Lock. Ereignisse, die während eines `call` eintreffen, bleiben für `wait_event` liegen.
    """

    def __init__(self, process: subprocess.Popen, writer, reader) -> None:
        self._process = process
        self._writer = writer
        self._inbox: queue.Queue = queue.Queue()
        self._pending_events: list[dict] = []
        self._next_id = 0
        self._reader = threading.Thread(target=self._read_loop, args=(reader,), name="chromium-pipe", daemon=True)
        self._reader.start()

    @classmethod
    def launch(cls, browser: str, flags: list[str]) -> "PipeConnection":
        """Startet ``browser`` mit ``flags`` und verbindet die Pipe.

        Args:
            browser: Pfad der Chromium-Programmdatei.
            flags: Startschalter ohne Pipe-Schalter; die fügt diese Funktion an.

        Raises:
            DevToolsError: System ohne Pipe-Unterstützung oder Start gescheitert.
        """
        if not pipe_supported():
            raise DevToolsError("DevTools-Pipe wird auf diesem System nicht unterstützt.")
        import msvcrt

        to_browser_read, to_browser_write = os.pipe()
        from_browser_read, from_browser_write = os.pipe()
        browser_in = msvcrt.get_osfhandle(to_browser_read)
        browser_out = msvcrt.get_osfhandle(from_browser_write)
        os.set_handle_inheritable(browser_in, True)
        os.set_handle_inheritable(browser_out, True)
        startupinfo = subprocess.STARTUPINFO()
        # Nur diese beiden Handles erbt der Browser, keine anderen offenen Dateien.
        startupinfo.lpAttributeList = {"handle_list": [browser_in, browser_out]}
        command = [browser, *flags, PIPE_SWITCH, f"--remote-debugging-io-pipes={browser_in},{browser_out}", "about:blank"]
        try:
            process = subprocess.Popen(
                command,
                startupinfo=startupinfo,
                close_fds=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            for descriptor in (to_browser_read, to_browser_write, from_browser_read, from_browser_write):
                os.close(descriptor)
            raise DevToolsError(f"Browserstart gescheitert: {exc}") from exc
        # Die Kindseite gehört jetzt dem Browser. Bliebe sie hier offen, merkte der
        # Lese-Thread nie, dass der Browser beendet ist.
        os.close(to_browser_read)
        os.close(from_browser_write)
        return cls(process, os.fdopen(to_browser_write, "wb", buffering=0), os.fdopen(from_browser_read, "rb", buffering=0))

    @property
    def alive(self) -> bool:
        """Ob der Browserprozess noch läuft."""
        return self._process.poll() is None

    def _read_loop(self, reader) -> None:
        """Zerlegt den Datenstrom in Nachrichten; ein ``None`` meldet das Ende der Pipe."""
        buffer = bytearray()
        search_from = 0
        try:
            while True:
                chunk = reader.read(1 << 20)
                if not chunk:
                    break
                buffer += chunk
                while (end := buffer.find(b"\0", search_from)) != -1:
                    self._inbox.put(json.loads(bytes(buffer[:end])))
                    del buffer[: end + 1]
                    search_from = 0
                search_from = len(buffer)
        except (OSError, ValueError):
            pass
        finally:
            self._inbox.put(None)

    def _next_message(self, deadline: float) -> dict:
        """Wartet bis ``deadline`` (``time.monotonic``) auf die nächste Nachricht."""
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise DevToolsError("Zeitlimit beim Warten auf den Browser überschritten.")
        try:
            message = self._inbox.get(timeout=remaining)
        except queue.Empty:
            raise DevToolsError("Zeitlimit beim Warten auf den Browser überschritten.") from None
        if message is None:
            self._inbox.put(None)  # Weitere Aufrufer sollen das Ende ebenfalls sehen.
            raise DevToolsError("Der Browser hat die Verbindung beendet.")
        return message

    def call(self, method: str, params: dict | None = None, *, session_id: str | None = None, deadline: float) -> dict:
        """Sendet einen Befehl und liefert dessen ``result``.

        Args:
            method: DevTools-Methode, etwa ``Page.navigate``.
            params: Parameter des Befehls.
            session_id: Ziel-Sitzung (Tab); ``None`` spricht den Browser an.
            deadline: Spätester Zeitpunkt (``time.monotonic``) für die Antwort.

        Raises:
            DevToolsError: Zeitlimit, Verbindungsende oder Fehlerantwort.
        """
        self._next_id += 1
        message_id = self._next_id
        message: dict = {"id": message_id, "method": method, "params": params or {}}
        if session_id is not None:
            message["sessionId"] = session_id
        try:
            self._writer.write(json.dumps(message).encode("utf-8") + b"\0")
        except OSError as exc:
            raise DevToolsError(f"Senden an den Browser gescheitert: {exc}") from exc
        while True:
            reply = self._next_message(deadline)
            if reply.get("id") == message_id:
                if "error" in reply:
                    raise DevToolsError(f"{method}: {reply['error'].get('message', reply['error'])}")
                return reply.get("result", {})
            if "method" in reply:
                self._pending_events.append(reply)

    def wait_event(self, method: str, *, session_id: str, deadline: float) -> dict:
        """Wartet auf ein Ereignis ``method`` der Sitzung ``session_id``; ältere verfallen."""
        for index, event in enumerate(self._pending_events):
            if event.get("method") == method and event.get("sessionId") == session_id:
                del self._pending_events[: index + 1]
                return event
        self._pending_events.clear()
        while True:
            event = self._next_message(deadline)
            if event.get("method") == method and event.get("sessionId") == session_id:
                return event

    def close(self, timeout: float = 3.0) -> None:
        """Beendet den Browser: Pipe schließen, kurz warten, sonst hart beenden."""
        try:
            self._writer.close()
        except OSError:
            pass
        try:
            self._process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait(timeout=timeout)
