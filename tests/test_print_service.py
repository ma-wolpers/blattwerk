"""Zustandsautomat des Druckdienstes: Neustart, Rückfall mit einer Warnung, Vorwärmen."""

from __future__ import annotations

import threading

import pytest

from app.core import print_service
from app.core.chromium_pipe import DevToolsError
from app.core.print_service import PrintService


class FakePrinter:
    """Protokolliert Drucke; wirft so oft wie in ``failures`` angegeben."""

    def __init__(self, log: list[str], name: str, failures: int = 0) -> None:
        self.log, self.name, self.failures, self.closed = log, name, failures, False

    def print_pdf(self, html_uri: str, out_pdf_path: str) -> None:
        if self.failures:
            self.failures -= 1
            raise DevToolsError(f"{self.name} kaputt")
        self.log.append(f"{self.name}:{html_uri}")

    def close(self) -> None:
        self.closed = True


class FastFactory:
    """Liefert der Reihe nach Drucker; ``"start"`` steht für einen gescheiterten Start."""

    def __init__(self, log: list[str], plan: list) -> None:
        self.log, self.plan, self.made = log, list(plan), []

    def __call__(self, browser: str) -> FakePrinter:
        step = self.plan.pop(0)
        if step == "start":
            raise DevToolsError("Start gescheitert")
        printer = FakePrinter(self.log, f"schnell{len(self.made)}", failures=step)
        self.made.append(printer)
        return printer


@pytest.fixture
def warnings(monkeypatch):
    received: list[str] = []
    print_service.set_fallback_listener(received.append)
    yield received
    print_service.set_fallback_listener(None)


def _service(log, plan, **kwargs):
    factory = FastFactory(log, plan)
    service = PrintService("edge", fast_factory=factory, fallback=FakePrinter(log, "cli"), fast_available=True, **kwargs)
    return service, factory


def test_browser_stays_running_across_prints(warnings):
    log: list[str] = []
    service, factory = _service(log, [0])
    service.print_pdf("a", "a.pdf")
    service.print_pdf("b", "b.pdf")
    assert log == ["schnell0:a", "schnell0:b"]
    assert len(factory.made) == 1 and warnings == []


def test_failed_print_restarts_once_and_retries_the_same_page(warnings):
    log: list[str] = []
    service, factory = _service(log, [1, 0])
    service.print_pdf("a", "a.pdf")
    assert log == ["schnell1:a"]
    assert factory.made[0].closed
    assert warnings == [] and not service.in_fallback


def test_failed_restart_warns_once_and_stays_on_command_line(warnings):
    log: list[str] = []
    service, _factory = _service(log, [1, "start"])
    service.print_pdf("a", "a.pdf")
    service.print_pdf("b", "b.pdf")
    assert log == ["cli:a", "cli:b"]
    assert len(warnings) == 1 and "Start gescheitert" in warnings[0]
    assert service.in_fallback


def test_system_without_pipe_uses_command_line_silently(warnings):
    log: list[str] = []
    service = PrintService("edge", fast_factory=FastFactory(log, []), fallback=FakePrinter(log, "cli"), fast_available=False)
    service.print_pdf("a", "a.pdf")
    service.prewarm()
    assert log == ["cli:a"] and warnings == []


def test_prewarm_starts_the_browser_in_the_background(warnings):
    log: list[str] = []
    started = threading.Event()

    def factory(browser):
        started.set()
        return FakePrinter(log, "warm")

    service = PrintService("edge", fast_factory=factory, fallback=FakePrinter(log, "cli"), fast_available=True)
    service.prewarm()
    assert started.wait(5)
    service.print_pdf("a", "a.pdf")  # wartet über den Lock, bis das Vorwärmen fertig ist
    assert log == ["warm:a"]


def test_failed_prewarm_does_not_warn_and_the_next_print_starts_again(warnings):
    log: list[str] = []
    service, factory = _service(log, ["start", 0])
    service._prewarm_now()
    assert warnings == []
    service.print_pdf("a", "a.pdf")
    assert log == ["schnell0:a"]


def test_close_ends_the_browser_and_a_later_print_starts_a_new_one(warnings):
    log: list[str] = []
    service, factory = _service(log, [0, 0])
    service.print_pdf("a", "a.pdf")
    service.close()
    service.print_pdf("b", "b.pdf")
    assert factory.made[0].closed
    assert log == ["schnell0:a", "schnell1:b"]
