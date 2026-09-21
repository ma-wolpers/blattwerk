"""Single-instance handoff: a second Blattwerk start passes its file to the running window.

Why this exists: Windows "Öffnen mit" (see ``docs/nutzer/OEFFNEN_MIT_EINRICHTEN.md``)
starts a *new process* per file. Blattwerk manages several documents as tabs of
one window, so a second process should not open a second window but hand the
file over to the first one.

Mechanism (stdlib only, no Tk, no third-party dependency):

* A start first claims a TCP port on ``127.0.0.1`` (loopback only, never
  reachable from the network) via :meth:`InstanceServer.start`. Exactly one
  process wins; it serves a tiny line protocol from a daemon thread.
* A start that loses the port calls :func:`forward_to_running_instance`. If a
  Blattwerk answers with the expected acknowledgement it exits without building
  a window.
* The server thread never touches Tk: it only queues :class:`OpenRequest`
  objects. The GUI thread polls the queue (Tkinter is not thread-safe) and
  reports it is alive through :meth:`InstanceServer.heartbeat` on every poll.
* The server acknowledges a client as soon as the request is queued *and* the GUI
  heartbeat is fresh. It deliberately does not wait for the file to be opened
  (rendering a preview takes seconds, and several parallel starts queue up behind
  each other) - only for proof that the event loop is alive. A first instance
  that never comes alive, or has been unresponsive for longer than
  ``_HEARTBEAT_FRESH_S``, is never acknowledged: the client times out and starts
  normally instead of silently losing its file.

Protocol (UTF-8, one request per connection)::

    client -> BLATTWERK-OPEN-V1\\n<absolute path or empty>\\n
    server -> BLATTWERK-OK\\n            (request queued, GUI known to be alive)

The magic line prevents mistaking an unrelated program that happens to own the
port for a Blattwerk instance. An empty path means "just bring the window to
the front".
"""

from __future__ import annotations

import queue
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path

SINGLE_INSTANCE_HOST = "127.0.0.1"
SINGLE_INSTANCE_PORT = 47653
"""Arbitrary, unregistered high port. Changing it needs no migration: instances of
different versions simply stop seeing each other and both open a window."""

_MAGIC = "BLATTWERK-OPEN-V1"
_ACK = "BLATTWERK-OK"
_CONNECT_TIMEOUT_S = 1.0
_ACCEPT_TIMEOUT_S = 30.0
"""How long a client waits for the GUI to come alive. Generous on purpose: a first
instance that is still starting up (several parallel cold starts share the CPU) must
not be mistaken for a frozen one, which would make the client start a second window.
A first instance that never comes alive costs the user this wait."""
_HEARTBEAT_FRESH_S = 60.0
"""How recent the last GUI poll must be for the GUI to count as alive. Opening a
document renders synchronously and blocks polling for a while; this covers that."""
_CLIENT_REPLY_TIMEOUT_S = _ACCEPT_TIMEOUT_S + 1.0
_MAX_MESSAGE_BYTES = 128 * 1024


def startup_file_from_argv(argv: list[str]) -> str | None:
    """Return the absolute path of the first non-option argument, or ``None``.

    Deliberately not ``argparse``: under ``pythonw.exe`` there is no
    ``sys.stderr``, and argparse's error path would crash instead of reporting.
    The path is resolved here (against the *caller's* working directory)
    because the running instance has a different one.

    Args:
        argv: Arguments without the program name (``sys.argv[1:]``).

    Returns:
        Absolute path string, or ``None`` if no file argument was given.
    """
    for argument in argv:
        if argument and not argument.startswith("-"):
            return str(Path(argument).expanduser().resolve())
    return None


def _read_lines(connection: socket.socket, line_count: int) -> list[str] | None:
    """Read exactly *line_count* newline-terminated UTF-8 lines, or ``None`` on EOF/oversize."""
    buffer = b""
    while buffer.count(b"\n") < line_count:
        if len(buffer) > _MAX_MESSAGE_BYTES:
            return None
        chunk = connection.recv(4096)
        if not chunk:
            return None
        buffer += chunk
    text = buffer.decode("utf-8", errors="replace")
    return text.split("\n")[:line_count]


def forward_to_running_instance(path: str | None, *, port: int = SINGLE_INSTANCE_PORT) -> bool:
    """Ask a running Blattwerk to open *path*; return ``True`` if it confirmed.

    ``False`` for every failure mode (nothing listening, foreign program on the
    port, no acknowledgement in time) - the caller then simply starts a normal
    instance. Nothing is raised: this runs before any GUI exists, where an
    exception would have no place to be shown.

    Args:
        path: Absolute file path, or ``None`` to merely raise the running window.
        port: Loopback port; only tests use a value other than the default.
    """
    try:
        with socket.create_connection((SINGLE_INSTANCE_HOST, port), timeout=_CONNECT_TIMEOUT_S) as connection:
            connection.settimeout(_CLIENT_REPLY_TIMEOUT_S)
            connection.sendall(f"{_MAGIC}\n{path or ''}\n".encode("utf-8"))
            reply = _read_lines(connection, 1)
    except OSError:
        return False
    return reply is not None and reply[0] == _ACK


@dataclass
class OpenRequest:
    """One "open this file" request received from a later start.

    Attributes:
        path: Absolute path text; empty means "only raise the window".
    """

    path: str


class InstanceServer:
    """Listens on loopback and queues :class:`OpenRequest` objects for the GUI thread.

    Usage::

        server = InstanceServer()
        if server.start():
            ...  # GUI thread, on every poll: server.heartbeat(); drain server.requests
        server.stop()

    Attributes:
        requests: Thread-safe queue drained by the GUI thread.
    """

    def __init__(self, port: int = SINGLE_INSTANCE_PORT) -> None:
        self._port = port
        self.requests: queue.Queue[OpenRequest] = queue.Queue()
        self._socket: socket.socket | None = None
        self._stopping = threading.Event()
        self._last_heartbeat: float | None = None

    def heartbeat(self) -> None:
        """Report that the GUI thread is alive (call at the start of every poll)."""
        self._last_heartbeat = time.monotonic()

    def _gui_is_alive(self) -> bool:
        """Return True if the GUI polled within ``_HEARTBEAT_FRESH_S``."""
        last = self._last_heartbeat
        return last is not None and time.monotonic() - last < _HEARTBEAT_FRESH_S

    def start(self) -> bool:
        """Bind the port and start serving; ``False`` if it is already taken.

        A taken port means another instance won the (rare) startup race or a
        foreign program owns it; the caller then runs without a server and
        simply is not reachable for handoffs.
        """
        candidate = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                candidate.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            candidate.bind((SINGLE_INSTANCE_HOST, self._port))
            candidate.listen(8)
            candidate.settimeout(0.5)
        except OSError:
            candidate.close()
            return False
        self._socket = candidate
        threading.Thread(target=self._serve, name="blattwerk-instance-server", daemon=True).start()
        return True

    def stop(self) -> None:
        """Stop serving and release the port (idempotent)."""
        self._stopping.set()
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None

    def _serve(self) -> None:
        """Accept loop (daemon thread): each connection is handled on its own short-lived thread.

        One thread per connection keeps a client that waits for the GUI to come alive
        from blocking the requests of the others (parallel starts).
        """
        while not self._stopping.is_set():
            listener = self._socket
            if listener is None:
                return
            try:
                connection, _address = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            threading.Thread(target=self._handle, args=(connection,), name="blattwerk-instance-request", daemon=True).start()

    def _handle(self, connection: socket.socket) -> None:
        """Validate one request, queue it, and acknowledge once the GUI is known to be alive."""
        with connection:
            try:
                connection.settimeout(_CONNECT_TIMEOUT_S)
                lines = _read_lines(connection, 2)
                if lines is None or lines[0] != _MAGIC:
                    return
                self.requests.put(OpenRequest(path=lines[1].strip()))
                deadline = time.monotonic() + _ACCEPT_TIMEOUT_S
                while not self._gui_is_alive():
                    if time.monotonic() >= deadline or self._stopping.is_set():
                        return
                    time.sleep(0.1)
                connection.sendall(f"{_ACK}\n".encode("utf-8"))
            except OSError:
                return
