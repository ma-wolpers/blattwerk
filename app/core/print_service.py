"""Wählt den Druckweg und hält den Dauerbrowser über die ganze Sitzung (ein Zustandsautomat).

Zustände:

- **schnell** (Start): Drucke laufen über `DevToolsPrinter`. Fällt er aus, startet der
  Dienst den Browser einmal neu und versucht denselben Druck erneut.
- **Rückfall**: Scheitert auch der Neustart, meldet der Dienst einmal eine Warnung über
  `set_fallback_listener` und druckt für den Rest der Sitzung über `CommandLinePrinter`.
  Ein neuer Start von Blattwerk versucht den schnellen Weg wieder.

Auf Systemen ohne DevTools-Pipe (`chromium_pipe.pipe_supported`) beginnt der Dienst still im
Rückfall: Das ist dort der normale Weg, keine Störung.

Ein Lock reiht alle Drucke hintereinander. Die GUI druckt ohnehin nur aus dem Tk-Thread;
der Lock schützt vor allem das Vorwärmen (`prewarm`, eigener Thread) beim App-Start.
"""

from __future__ import annotations

import atexit
import logging
import threading
from collections.abc import Callable

from .chromium_pipe import DevToolsError, pipe_supported
from .pdf_printers import CommandLinePrinter, DevToolsPrinter, PdfPrinter

_LOG = logging.getLogger(__name__)

FALLBACK_WARNING = (
    "Der schnelle PDF-Druck über den Browser ist ausgefallen ({reason}).\n\n"
    "Blattwerk druckt in dieser Sitzung auf dem langsameren Weg weiter, mit rund 2 bis 3 "
    "Sekunden je Vorschau oder Export. Beim nächsten Start von Blattwerk wird der schnelle "
    "Weg wieder versucht."
)


def _log_warning(message: str) -> None:
    """Standard-Empfänger ohne GUI (CLI, Tests): ins Log."""
    _LOG.warning(message)


_fallback_listener: Callable[[str], None] = _log_warning


def set_fallback_listener(listener: Callable[[str], None] | None) -> None:
    """Legt fest, wer die Rückfall-Warnung erhält; ``None`` stellt das Log wieder her.

    Der Empfänger läuft in dem Thread, der gerade druckt (in der GUI also im Tk-Thread).
    """
    global _fallback_listener
    _fallback_listener = listener or _log_warning


class PrintService:
    """Druckt über den schnellen Weg, mit einem Neustart und danach dem Rückfall.

    Args:
        browser: Pfad der Chromium-Programmdatei.
        fast_factory: Erzeugt den schnellen Drucker; wirft `DevToolsError`, wenn das scheitert.
        fallback: Drucker für den Rückfall.
        fast_available: False beginnt still im Rückfall (System ohne Pipe, Messvarianten).
    """

    def __init__(
        self,
        browser: str,
        *,
        fast_factory: Callable[[str], PdfPrinter] = DevToolsPrinter,
        fallback: PdfPrinter | None = None,
        fast_available: bool | None = None,
    ) -> None:
        self._browser = browser
        self._fast_factory = fast_factory
        self._fallback = fallback or CommandLinePrinter(browser)
        self._fast: PdfPrinter | None = None
        self._in_fallback = not (pipe_supported() if fast_available is None else fast_available)
        self._lock = threading.Lock()

    @property
    def in_fallback(self) -> bool:
        """Ob der Dienst auf dem langsamen Weg druckt."""
        return self._in_fallback

    def prewarm(self) -> None:
        """Startet den schnellen Drucker im Hintergrund, damit schon der erste Druck schnell ist.

        Ein Fehler hier warnt nicht: Der nächste Druck versucht den Start ohnehin erneut.
        """
        if self._in_fallback or self._fast is not None:
            return
        threading.Thread(target=self._prewarm_now, name="print-prewarm", daemon=True).start()

    def _prewarm_now(self) -> None:
        with self._lock:
            if self._in_fallback or self._fast is not None:
                return
            try:
                self._fast = self._fast_factory(self._browser)
            except DevToolsError as exc:
                _LOG.info("Vorwärmen des Druckbrowsers gescheitert: %s", exc)

    def print_pdf(self, html_uri: str, out_pdf_path: str) -> None:
        """Druckt ``html_uri`` nach ``out_pdf_path`` über den aktuell gültigen Weg."""
        with self._lock:
            if not self._in_fallback:
                last_error: DevToolsError | None = None
                for _attempt in range(2):
                    try:
                        if self._fast is None:
                            self._fast = self._fast_factory(self._browser)
                        self._fast.print_pdf(html_uri, out_pdf_path)
                        return
                    except DevToolsError as exc:
                        last_error = exc
                        self._discard_fast()
                self._in_fallback = True
                _fallback_listener(FALLBACK_WARNING.format(reason=last_error))
            self._fallback.print_pdf(html_uri, out_pdf_path)

    def _discard_fast(self) -> None:
        """Gibt einen gestörten schnellen Drucker frei; der nächste Versuch startet neu."""
        printer, self._fast = self._fast, None
        if printer is not None:
            try:
                printer.close()
            except Exception as exc:  # Aufräumen darf den Neustart nicht verhindern.
                _LOG.info("Gestörten Druckbrowser nicht sauber beendet: %s", exc)

    def close(self) -> None:
        """Beendet den Dauerbrowser; der Dienst bleibt nutzbar und startet ihn bei Bedarf neu."""
        with self._lock:
            self._discard_fast()


_default_service: PrintService | None = None
_default_lock = threading.Lock()
_shutdown_registered = False


def default_print_service(browser: str) -> PrintService:
    """Der Dienst dieser Sitzung; beim ersten Aufruf angelegt und für das Beenden angemeldet."""
    global _default_service, _shutdown_registered
    with _default_lock:
        if _default_service is None:
            _default_service = PrintService(browser)
        if not _shutdown_registered:
            atexit.register(shutdown_default_print_service)
            _shutdown_registered = True
        return _default_service


def replace_default_print_service(service: PrintService | None) -> PrintService | None:
    """Tauscht den Sitzungsdienst aus (Messskript, Tests) und liefert den bisherigen.

    Der bisherige Dienst wird nicht beendet; das bleibt Sache des Aufrufers.
    """
    global _default_service
    with _default_lock:
        previous, _default_service = _default_service, service
        return previous


def shutdown_default_print_service() -> None:
    """Beendet den Dauerbrowser der Sitzung; mehrfacher Aufruf ist harmlos."""
    service = replace_default_print_service(None)
    if service is not None:
        service.close()
