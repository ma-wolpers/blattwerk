"""Der laufende Render-Job, für den Core ohne Parameterkette erreichbar.

Abbruch-Prüfpunkte und Stufenmeldungen sitzen tief in der Aufrufkette
(`write_pdf_with_bottom_legends` -> `render=` -> `write_pdf_from_html`). Sie als Parameter
durchzureichen, würde jede Signatur dazwischen ändern, auch die von Tests ersetzten
`render=`-Funktionen. Deshalb hält ein `ContextVar` den Job.

Regeln:

- Genau `run_bound` bindet. Die aufrufende Schicht bindet nur, der Core liest nur.
- Ohne gebundenen Job tut nichts hier etwas: CLI und Tests verhalten sich wie zuvor.
- Der `ContextVar` trägt nur Job-Kontext und Stufen-Empfänger, nie Cache oder Optionen.
  Was das Ergebnis beeinflusst, bleibt ein sichtbarer Parameter.

Dieses Modul kennt weder Tk noch bw-gui. Das Protocol `RenderJobContext` beschreibt nur,
was der Core braucht; bw-guis `TaskContext` erfüllt es ohne Wrapper.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import ContextManager, Protocol, TypeVar

from .render_stages import stage_label

T = TypeVar("T")


class RenderJobContext(Protocol):
    """Was der Core vom laufenden Job braucht."""

    @property
    def cancelled(self) -> bool:
        """True, sobald der Abbruch angefordert wurde."""

    def report(self, text: str, *, fraction: float | None = None) -> None:
        """Meldet den aktuellen Stand; ``fraction`` 0..1 oder None für unbestimmt."""

    def check_cancelled(self) -> None:
        """Wirft die Abbruch-Ausnahme des Jobs, falls ein Abbruch angefordert wurde."""

    def commit(self) -> ContextManager[None]:
        """Unkündbarer Abschnitt, z. B. das Veröffentlichen einer Datei."""


class StageSink(Protocol):
    """Empfänger der Stufenmeldungen (Zeitmessung oder Fortschrittsmodell)."""

    def stage_entered(self, key: str) -> None:
        """Eine Stufe beginnt; Stufen dürfen geschachtelt sein."""

    def stage_progress(self, fraction: float) -> None:
        """Fortschritt innerhalb der innersten Stufe, 0..1."""

    def stage_left(self, key: str) -> None:
        """Die Stufe endet, auch bei einer Ausnahme."""


@dataclass(frozen=True)
class _Binding:
    context: RenderJobContext | None
    sink: StageSink | None


_binding: ContextVar[_Binding | None] = ContextVar("blattwerk_render_job", default=None)


def run_bound(
    context: RenderJobContext | None,
    work: Callable[[], T],
    *,
    sink: StageSink | None = None,
) -> T:
    """Führt ``work`` mit gebundenem Job aus und stellt danach den alten Zustand her.

    Args:
        context: Der laufende Job; None, wenn nur Stufen gemessen werden.
        work: Die Arbeit ohne Argumente.
        sink: Empfänger der Stufenmeldungen; None ohne Empfänger.

    Returns:
        Das Ergebnis von ``work``.

    Example:
        >>> run_bound(None, lambda: 42)
        42
    """
    token = _binding.set(_Binding(context, sink))
    try:
        return work()
    finally:
        _binding.reset(token)


def check_cancelled() -> None:
    """Prüfpunkt: wirft die Abbruch-Ausnahme des Jobs, ohne Job passiert nichts."""
    binding = _binding.get()
    if binding is not None and binding.context is not None:
        binding.context.check_cancelled()


def is_cancelled() -> bool:
    """True, wenn der gebundene Job abgebrochen wurde; für Warteschleifen ohne Ausnahme."""
    binding = _binding.get()
    return binding is not None and binding.context is not None and binding.context.cancelled


@contextmanager
def commit_section():
    """Unkündbarer Abschnitt des Jobs; ohne Job ein leerer Block.

    Direkt davor gehört ein `check_cancelled()`: Nach dem Betreten gilt die Arbeit als
    fertig, auch wenn während des Abschnitts ein Abbruch ankommt.
    """
    binding = _binding.get()
    if binding is None or binding.context is None:
        yield
        return
    with binding.context.commit():
        yield


@contextmanager
def stage(key: str):
    """Markiert eine Render-Stufe: Prüfpunkt am Anfang, Meldung an den Empfänger.

    Args:
        key: Schlüssel aus `render_stages`. Unbekannte Schlüssel werfen `KeyError`, auch
            ohne gebundenen Job, damit ein Tippfehler schon in Tests auffällt.

    Example:
        >>> from app.core.render_stages import STAGE_PRINT
        >>> with stage(STAGE_PRINT):
        ...     pass
    """
    stage_label(key)
    binding = _binding.get()
    sink = binding.sink if binding is not None else None
    check_cancelled()
    if sink is None:
        yield
        return
    sink.stage_entered(key)
    try:
        yield
    finally:
        sink.stage_left(key)


def stage_progress(done: int, total: int) -> None:
    """Meldet ``done`` von ``total`` in der innersten Stufe, mit Prüfpunkt.

    Für Schleifen, etwa das Rastern je Seite. Bei ``total <= 0`` wird nichts gemeldet.
    """
    check_cancelled()
    binding = _binding.get()
    if binding is None or binding.sink is None or total <= 0:
        return
    binding.sink.stage_progress(min(1.0, max(0.0, done / total)))
