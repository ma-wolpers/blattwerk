"""Beobachter eines Render-Laufs, für den Core ohne Parameterkette erreichbar.

Stufenmeldungen und Dateiabhängigkeiten entstehen tief in der Aufrufkette
(`write_pdf_with_bottom_legends` -> `render=` -> `write_pdf_from_html`). Sie als Parameter
durchzureichen, würde jede Signatur dazwischen ändern, auch die von Tests ersetzten
`render=`-Funktionen. Deshalb hält ein `ContextVar` den Beobachter.

Regeln:

- Nur `run_observed` bindet. Die aufrufende Schicht bindet, der Core meldet nur.
- Ohne gebundenen Beobachter passiert nichts: CLI und Tests verhalten sich wie zuvor.
- Der `ContextVar` trägt nur den Beobachter, nie Cache oder Optionen. Was das Ergebnis
  beeinflusst, bleibt ein sichtbarer Parameter.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import TypeVar

from .render_stages import RENDER_STAGES

T = TypeVar("T")


class RenderObserver:
    """Empfänger der Meldungen eines Laufs; Unterklassen überschreiben, was sie brauchen."""

    def stage_entered(self, key: str) -> None:
        """Eine Stufe beginnt; Stufen dürfen geschachtelt sein."""

    def stage_left(self, key: str) -> None:
        """Die Stufe endet, auch bei einer Ausnahme."""

    def file_dependency(self, path: Path) -> None:
        """Das Ergebnis hängt von dieser lokalen Datei ab; sie darf auch fehlen."""


_observer: ContextVar[RenderObserver | None] = ContextVar("blattwerk_render_observer", default=None)


def run_observed(work: Callable[[], T], observer: RenderObserver) -> T:
    """Führt ``work`` mit gebundenem Beobachter aus und stellt danach den alten Zustand her.

    Args:
        work: Die Arbeit ohne Argumente.
        observer: Empfänger der Meldungen.

    Returns:
        Das Ergebnis von ``work``.

    Example:
        >>> run_observed(lambda: 42, RenderObserver())
        42
    """
    token = _observer.set(observer)
    try:
        return work()
    finally:
        _observer.reset(token)


@contextmanager
def stage(key: str):
    """Markiert eine Render-Stufe.

    Args:
        key: Schlüssel aus `render_stages`. Unbekannte Schlüssel werfen `KeyError`, auch
            ohne Beobachter, damit ein Tippfehler schon in Tests auffällt.

    Example:
        >>> from app.core.render_stages import STAGE_PRINT
        >>> with stage(STAGE_PRINT):
        ...     pass
    """
    if key not in RENDER_STAGES:
        raise KeyError(key)
    observer = _observer.get()
    if observer is None:
        yield
        return
    observer.stage_entered(key)
    try:
        yield
    finally:
        observer.stage_left(key)


def note_file_dependency(path: Path) -> None:
    """Meldet eine lokale Datei, von der das Ergebnis abhängt; ohne Beobachter wirkungslos."""
    observer = _observer.get()
    if observer is not None:
        observer.file_dependency(path)
