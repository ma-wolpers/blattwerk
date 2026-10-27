"""PDF-Druck der Kurzentwurf-Runtime: delegiert an den einen Chromium-Drucker von Blattwerk.

Frueher stand hier eine eigene Kopie von Browsersuche und ``--print-to-pdf``-Aufruf.
Seit Kurzentwurf Teil von Blattwerk ist (AGENTS.md Regel 9), gibt es nur noch
`app/core/blatt_kern_io_pdf.py`; dieses Modul bleibt als stabiler Importpfad der
Runtime (vom Guardrail `_check_integrated_kurzentwurf_runtime` gefordert).
"""

from __future__ import annotations

from ..blatt_kern_io_pdf import find_chromium_executable, write_pdf_from_html

__all__ = ["find_chromium_executable", "write_pdf_from_html"]
