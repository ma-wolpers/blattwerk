"""Single-Instance-Übergabe ("Öffnen mit"): Protokoll, Server und GUI-seitige Verarbeitung.

Echte Loopback-Sockets (kein Fake): Zeitverhalten und Portbelegung sind der Kern der
Funktion. Die GUI-Seite wird mit Test-Doubles geprüft -- sie braucht kein echtes Tk.
"""

from __future__ import annotations

import queue
import socket
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()

import app.bootstrap.single_instance as single_instance
from app.bootstrap.single_instance import (
    InstanceServer,
    OpenRequest,
    forward_to_running_instance,
    startup_file_from_argv,
)
from app.ui import blatt_ui_external_open
from app.ui.blatt_ui_external_open import BlattwerkAppExternalOpenMixin
from app.ui.blatt_ui_persistence import BlattwerkAppPersistenceMixin


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture
def port() -> int:
    return _free_port()


@pytest.fixture
def server(port):
    instance = InstanceServer(port)
    assert instance.start()
    yield instance
    instance.stop()


@pytest.fixture
def fast_timeouts(monkeypatch):
    """Shrink the wait-for-GUI limits so 'GUI never comes alive' cases finish quickly."""
    monkeypatch.setattr(single_instance, "_ACCEPT_TIMEOUT_S", 0.4)
    monkeypatch.setattr(single_instance, "_CLIENT_REPLY_TIMEOUT_S", 2.0)


def test_startup_file_from_argv_returns_none_without_file_argument():
    assert startup_file_from_argv([]) is None
    assert startup_file_from_argv(["--verbose", "-x"]) is None


def test_startup_file_from_argv_resolves_first_non_option_argument(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    resolved = startup_file_from_argv(["--flag", "sub/blatt.md", "second.md"])

    assert resolved == str((tmp_path / "sub" / "blatt.md").resolve())


def test_forward_returns_false_when_nothing_listens(port):
    assert forward_to_running_instance("C:/x/a.md", port=port) is False


def test_forward_delivers_path_once_the_gui_is_alive(server, port):
    server.heartbeat()

    assert forward_to_running_instance("C:/x/a.md", port=port) is True

    assert server.requests.get(timeout=2).path == "C:/x/a.md"


def test_forward_without_path_sends_empty_path_to_only_raise_the_window(server, port):
    server.heartbeat()

    assert forward_to_running_instance(None, port=port) is True

    assert server.requests.get(timeout=2).path == ""


def test_forward_waits_for_a_gui_that_is_still_starting_up(server, port):
    """The first instance may still be importing: the client waits for its first heartbeat."""
    threading.Timer(0.5, server.heartbeat).start()

    started = time.monotonic()
    assert forward_to_running_instance("C:/x/a.md", port=port) is True

    assert time.monotonic() - started >= 0.4


def test_forward_returns_false_when_the_gui_never_comes_alive(server, port, fast_timeouts):
    """A frozen first instance must not swallow the file: the client falls back to a normal start."""
    assert forward_to_running_instance("C:/x/a.md", port=port) is False


def test_forward_returns_false_when_the_gui_heartbeat_has_gone_stale(server, port, fast_timeouts, monkeypatch):
    monkeypatch.setattr(single_instance, "_HEARTBEAT_FRESH_S", 0.1)
    server.heartbeat()
    time.sleep(0.3)

    assert forward_to_running_instance("C:/x/a.md", port=port) is False


def test_a_busy_gui_with_a_fresh_heartbeat_still_acknowledges_immediately(server, port):
    """Opening a document renders synchronously; the client must not wait for it (nor for the queue)."""
    server.heartbeat()
    started = time.monotonic()

    assert forward_to_running_instance("C:/x/a.md", port=port) is True

    assert time.monotonic() - started < 2.0
    assert server.requests.qsize() == 1, "acknowledged although nobody consumed it yet"


def test_parallel_clients_do_not_block_each_other(server, port):
    """Regression: 'Öffnen mit' on several files starts several clients at once."""
    server.heartbeat()
    results: list[bool] = []
    lock = threading.Lock()

    def client(index: int) -> None:
        outcome = forward_to_running_instance(f"C:/x/{index}.md", port=port)
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=client, args=(index,)) for index in range(8)]
    started = time.monotonic()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert results == [True] * 8
    assert time.monotonic() - started < 5.0
    assert sorted(server.requests.get_nowait().path for _ in range(8)) == sorted(f"C:/x/{i}.md" for i in range(8))


def test_forward_ignores_a_foreign_program_on_the_port(port):
    listener = socket.socket()
    listener.bind(("127.0.0.1", port))
    listener.listen(1)

    def foreign() -> None:
        connection, _ = listener.accept()
        with connection:
            connection.recv(1024)
            connection.sendall(b"HTTP/1.1 400 Bad Request\n")

    threading.Thread(target=foreign, daemon=True).start()
    try:
        assert forward_to_running_instance("C:/x/a.md", port=port) is False
    finally:
        listener.close()


def test_server_ignores_requests_with_wrong_magic(server, port):
    server.heartbeat()
    with socket.create_connection(("127.0.0.1", port), timeout=1) as connection:
        connection.sendall(b"SOMETHING-ELSE\nC:/x/a.md\n")
        connection.settimeout(1)
        assert connection.recv(64) == b""

    assert server.requests.empty()


def test_second_server_cannot_bind_the_same_port(server, port):
    assert InstanceServer(port).start() is False


def test_stop_releases_the_port(port):
    first = InstanceServer(port)
    assert first.start()
    first.stop()

    second = InstanceServer(port)
    try:
        assert second.start() is True
    finally:
        second.stop()


class _FakeRoot:
    """Records the Tk calls the mixin makes; ``after`` is captured, never run."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.scheduled: list[tuple[int, object]] = []

    def after(self, delay, callback=None):
        self.scheduled.append((delay, callback))

    def deiconify(self):
        self.calls.append("deiconify")

    def lift(self):
        self.calls.append("lift")

    def attributes(self, name, value):
        self.calls.append(f"attributes {name} {value}")

    def focus_force(self):
        self.calls.append("focus_force")


class _FakeServer:
    """Stand-in for ``InstanceServer`` on the GUI side: a queue plus a heartbeat log."""

    def __init__(self, events: list[str] | None = None) -> None:
        self.requests: queue.Queue[OpenRequest] = queue.Queue()
        self.beats = 0
        self._events = events

    def heartbeat(self) -> None:
        self.beats += 1
        if self._events is not None:
            self._events.append("heartbeat")


class _Host(BlattwerkAppExternalOpenMixin):
    def __init__(self) -> None:
        self.root = _FakeRoot()
        self.opened: list[tuple[Path, bool, bool]] = []

    def _open_input_path(self, path, add_recent=True, show_duplicate_message=True):
        self.opened.append((path, add_recent, show_duplicate_message))

    def rearmed(self) -> int:
        return len([cb for _delay, cb in self.root.scheduled if cb == self._poll_external_open_requests])


@pytest.fixture
def errors(monkeypatch):
    shown: list[tuple[str, str]] = []
    monkeypatch.setattr(
        blatt_ui_external_open,
        "messagebox",
        SimpleNamespace(showerror=lambda title, message: shown.append((title, message))),
    )
    return shown


def test_open_external_path_opens_existing_file_as_tab_without_duplicate_warning(tmp_path):
    document = tmp_path / "blatt.md"
    document.write_text("# x", encoding="utf-8")
    host = _Host()

    host.open_external_path(str(document), raise_window=True)

    assert host.opened == [(document, True, False)]
    assert "deiconify" in host.root.calls and "lift" in host.root.calls


def test_open_external_path_reports_missing_file_instead_of_opening_a_broken_tab(tmp_path, errors):
    host = _Host()

    host.open_external_path(str(tmp_path / "gone.md"), raise_window=False)

    assert host.opened == []
    assert errors and errors[0][0] == "Datei nicht gefunden"


def test_open_external_path_with_empty_path_only_raises_the_window():
    host = _Host()

    host.open_external_path("", raise_window=True)

    assert host.opened == []
    assert "focus_force" in host.root.calls


def test_poll_reports_liveness_opens_every_queued_request_and_rearms_the_timer(tmp_path):
    first = tmp_path / "a.md"
    second = tmp_path / "b.md"
    first.write_text("a", encoding="utf-8")
    second.write_text("b", encoding="utf-8")
    server = _FakeServer()
    server.requests.put(OpenRequest(str(first)))
    server.requests.put(OpenRequest(str(second)))
    host = _Host()
    host._instance_server = server

    host._poll_external_open_requests()

    assert [entry[0] for entry in host.opened] == [first, second]
    assert server.beats == 1
    assert host.rearmed() == 1


def test_poll_reports_liveness_even_when_nothing_is_queued():
    server = _FakeServer()
    host = _Host()
    host._instance_server = server

    host._poll_external_open_requests()
    host._poll_external_open_requests()

    assert server.beats == 2


def test_a_failing_open_is_reported_and_does_not_stop_the_poll_loop(tmp_path, errors):
    class _Broken(_Host):
        def _open_input_path(self, *args, **kwargs):
            raise RuntimeError("boom")

    document = tmp_path / "a.md"
    document.write_text("a", encoding="utf-8")
    server = _FakeServer()
    server.requests.put(OpenRequest(str(document)))
    host = _Broken()
    host._instance_server = server

    host._poll_external_open_requests()

    assert errors and "boom" in errors[0][1]
    assert host.rearmed() == 1


def test_startup_file_takes_precedence_over_start_with_last_file_and_is_not_opened_in_the_constructor():
    opened_recent: list[str] = []
    external: list[tuple[str, bool]] = []
    host = SimpleNamespace(
        _startup_file="C:/x/explicit.md",
        user_preferences={"start_with_last_file": True},
        recent_files=["C:/x/last.md"],
        open_external_path=lambda path, *, raise_window: external.append((path, raise_window)),
        _open_recent_file=opened_recent.append,
    )

    BlattwerkAppPersistenceMixin._maybe_apply_startup_file_preference(host)

    assert external == [], "must not render inside the constructor: parallel starts could not hand over yet"
    assert opened_recent == []


def test_first_poll_opens_the_startup_file_before_any_queued_request(tmp_path):
    startup = tmp_path / "startup.md"
    queued = tmp_path / "queued.md"
    startup.write_text("s", encoding="utf-8")
    queued.write_text("q", encoding="utf-8")
    server = _FakeServer()
    server.requests.put(OpenRequest(str(queued)))
    host = _Host()
    host._startup_file = str(startup)
    host.start_external_open_listener(server)

    assert host.root.scheduled[0][0] == 0
    host._poll_external_open_requests()

    assert [entry[0] for entry in host.opened] == [startup, queued]
    assert host._startup_file is None


def test_liveness_is_reported_before_the_slow_startup_file_is_opened(tmp_path):
    """Regression (found with three real parallel starts): the clients' acknowledgement must not
    wait for the startup file's synchronous rendering, or they time out and open windows of their own."""
    startup = tmp_path / "startup.md"
    startup.write_text("s", encoding="utf-8")
    events: list[str] = []

    class _Slow(_Host):
        def _open_input_path(self, path, add_recent=True, show_duplicate_message=True):
            events.append("open")

    host = _Slow()
    host._startup_file = str(startup)
    host.start_external_open_listener(_FakeServer(events))

    host._poll_external_open_requests()

    assert events == ["heartbeat", "open"]


def test_startup_file_is_opened_once_even_without_a_server_and_polling_then_stops(tmp_path):
    startup = tmp_path / "startup.md"
    startup.write_text("s", encoding="utf-8")
    host = _Host()
    host._startup_file = str(startup)
    host.start_external_open_listener(None)

    host._poll_external_open_requests()
    host._poll_external_open_requests()

    assert [entry[0] for entry in host.opened] == [startup]
    assert host.rearmed() == 1, "only the initial scheduling by start_external_open_listener, no re-arming"
