"""Zwei Wege, eine HTML-Datei mit Chromium als PDF zu drucken, hinter einem Protocol.

- `DevToolsPrinter`: Ein Browser läuft dauerhaft, jeder Druck ist ein neuer Tab über die
  DevTools-Pipe (`chromium_pipe`). Rund 0,3 s je Druck ohne Formeln.
- `CommandLinePrinter`: Ein Browserprozess je Druck (``--print-to-pdf``). Langsam, aber
  ohne Protokoll; Rückfall, wenn der erste Weg ausfällt.

Warum zwei Wege (Messung 2026-11-09, Edge 157): Allein der Start eines Browsers kostet
1,5 bis 4 s, je nach Profil. Der Druck selbst dauert nur Zehntelsekunden.

Beide Wege nutzen dieselben Startschalter (`browser_flags`), dasselbe Zeitbudget und
dieselbe Wartereihenfolge wie Chromiums eigener ``--print-to-pdf``: erst Load-Ereignis,
dann virtuelle Zeit bis das Budget verbraucht ist (Netzabrufe halten sie an), dann Druck.
`tests/test_pdf_printers.py` prüft, dass beide Wege pixelgleiche PDFs liefern.
"""

from __future__ import annotations

import base64
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Protocol

from .chromium_pipe import DevToolsError, PipeConnection

VIRTUAL_TIME_BUDGET_MS = 5000
"""Virtuelle Wartezeit nach dem Load-Ereignis; läuft ohne offene Abrufe sofort ab."""

PRINT_TIMEOUT_SECONDS = 60.0
"""Echte Höchstdauer eines Drucks, auf beiden Wegen."""

STARTUP_TIMEOUT_SECONDS = 20.0
"""Höchstdauer, bis ein neu gestarteter Dauerbrowser antwortet."""

BACKGROUND_SERVICE_FLAGS = (
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--disable-sync",
    "--disable-background-networking",
    "--disable-component-update",
)
"""Dienste, die ein frisches Profil beim Start sonst anwirft; sie tragen nichts zum Druck bei."""

_PRINT_PARAMS = {"printBackground": True, "preferCSSPageSize": True, "displayHeaderFooter": False}
"""Entspricht ``--print-to-pdf`` mit ``--no-pdf-header-footer``."""


class PdfPrinter(Protocol):
    """Druckt eine lokale HTML-Seite als PDF."""

    def print_pdf(self, html_uri: str, out_pdf_path: str) -> None:
        """Schreibt die Seite ``html_uri`` (``file://``) nach ``out_pdf_path``."""

    def close(self) -> None:
        """Gibt Browser und Profil frei; danach ist der Drucker unbrauchbar."""


def browser_flags(profile_dir: Path) -> list[str]:
    """Startschalter für beide Wege. Eigene Funktion, damit Messskript und Tests sie abwandeln.

    Ein eigenes Profil ist Pflicht: Mit Edges Standardprofil kostete schon der Start einer
    leeren Seite rund 4,1 s statt 1,6 s (Messung 2026-11-09, Edge 157).

    Args:
        profile_dir: Ordner, den nur dieser Browserprozess als Profil nutzt.
    """
    return [
        "--headless=new",
        "--disable-gpu",
        "--allow-file-access-from-files",
        f"--user-data-dir={profile_dir}",
        *BACKGROUND_SERVICE_FLAGS,
    ]


class CommandLinePrinter:
    """Ein Browserprozess je Druck, mit frischem Profil im Temp-Ordner."""

    def __init__(self, browser: str) -> None:
        self._browser = browser

    def command(self, html_uri: str, out_pdf_path: str, profile_dir: Path) -> list[str]:
        """Der vollständige Aufruf eines Drucks."""
        return [
            self._browser,
            *browser_flags(profile_dir),
            f"--virtual-time-budget={VIRTUAL_TIME_BUDGET_MS}",
            "--no-pdf-header-footer",
            "--print-to-pdf-no-header",
            f"--print-to-pdf={out_pdf_path}",
            html_uri,
        ]

    def print_pdf(self, html_uri: str, out_pdf_path: str) -> None:
        """Druckt über ``--print-to-pdf``.

        Raises:
            RuntimeError: Der Browser meldet einen Fehler.
        """
        with tempfile.TemporaryDirectory(prefix="blattwerk-cli-print-") as profile_dir:
            result = subprocess.run(
                self.command(html_uri, out_pdf_path, Path(profile_dir)),
                capture_output=True,
                text=True,
                timeout=PRINT_TIMEOUT_SECONDS,
                encoding="utf-8",
                errors="replace",
            )
        if result.returncode != 0:
            details = (result.stderr or result.stdout or "Unbekannter Fehler").strip()
            raise RuntimeError(f"PDF-Erstellung fehlgeschlagen: {details}")

    def close(self) -> None:
        """Nichts zu tun; jeder Druck räumt selbst auf."""


class DevToolsPrinter:
    """Ein dauerhaft laufender Browser; jeder Druck öffnet und schließt einen eigenen Tab.

    Der Konstruktor startet den Browser und wartet, bis er antwortet.

    Raises:
        DevToolsError: Start gescheitert (auch: System ohne Pipe, siehe `chromium_pipe`).
    """

    def __init__(self, browser: str, *, launch=PipeConnection.launch) -> None:
        self._profile_dir = Path(tempfile.mkdtemp(prefix="blattwerk-print-"))
        try:
            self._connection = launch(browser, browser_flags(self._profile_dir))
            self._connection.call("Browser.getVersion", deadline=time.monotonic() + STARTUP_TIMEOUT_SECONDS)
        except DevToolsError:
            self.close()
            raise

    def print_pdf(self, html_uri: str, out_pdf_path: str) -> None:
        """Druckt in einem neuen Tab; Ablauf wie ``--print-to-pdf`` (siehe Modul-Docstring).

        Raises:
            DevToolsError: Browser hängt, ist beendet oder meldet einen Fehler.
        """
        connection = self._connection
        deadline = time.monotonic() + PRINT_TIMEOUT_SECONDS
        target = connection.call("Target.createTarget", {"url": "about:blank"}, deadline=deadline)["targetId"]
        try:
            attached = connection.call("Target.attachToTarget", {"targetId": target, "flatten": True}, deadline=deadline)
            session = attached["sessionId"]
            connection.call("Page.enable", session_id=session, deadline=deadline)
            navigated = connection.call("Page.navigate", {"url": html_uri}, session_id=session, deadline=deadline)
            if navigated.get("errorText"):
                raise DevToolsError(f"Seite nicht geladen: {navigated['errorText']}")
            connection.wait_event("Page.loadEventFired", session_id=session, deadline=deadline)
            connection.call(
                "Emulation.setVirtualTimePolicy",
                {"policy": "pauseIfNetworkFetchesPending", "budget": VIRTUAL_TIME_BUDGET_MS},
                session_id=session,
                deadline=deadline,
            )
            connection.wait_event("Emulation.virtualTimeBudgetExpired", session_id=session, deadline=deadline)
            data = connection.call("Page.printToPDF", _PRINT_PARAMS, session_id=session, deadline=deadline)["data"]
        except BaseException:
            self._close_target_quietly(target)
            raise
        connection.call("Target.closeTarget", {"targetId": target}, deadline=deadline)
        Path(out_pdf_path).write_bytes(base64.b64decode(data))

    def _close_target_quietly(self, target: str) -> None:
        """Schließt den Tab nach einem Fehler; ein zweiter Fehler verdeckt den ersten nicht."""
        try:
            self._connection.call("Target.closeTarget", {"targetId": target}, deadline=time.monotonic() + 2.0)
        except DevToolsError:
            pass

    def close(self) -> None:
        """Beendet den Browser und löscht das Profil.

        GRENZE: Nach einem Absturz von Blattwerk bleibt der Profilordner (rund 7 MB) im
        Temp-Ordner liegen; Windows räumt ihn mit der Speicheroptimierung weg.
        """
        connection = getattr(self, "_connection", None)
        if connection is not None:
            connection.close()
        shutil.rmtree(self._profile_dir, ignore_errors=True)
