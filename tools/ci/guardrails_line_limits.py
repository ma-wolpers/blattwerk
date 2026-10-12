"""Zeilenlimit-Guardrail: hoechstens 300 ausfuehrbare Zeilen je beruehrter Python-Datei.

Die Zaehlregel, der Datenmodul-Marker ``# line-limit: data-only`` und das Lesen der
begruendeten Ausnahmen stammen aus dem gemeinsamen bw-gui-Werkzeug
``bw_gui.testing.line_limits`` -- dieselbe Implementierung fuer alle Repos. Hier wird
es nur mit Blattwerks Architektur-Dokument verdrahtet.

"Beruehrt" heisst: gegenueber ``HEAD`` geaenderte (gestagt oder nicht) und neue,
nicht ignorierte Dateien, inklusive Tests; bei sauberem Arbeitsbaum (CI) die Dateien
des letzten Commits. Unberuehrte Altlasten ueber 300 Zeilen werden nicht gemeldet.
"""

from __future__ import annotations

from guardrails_config import ROOT

LINE_LIMIT_ARCH_DOC = "docs/intern/ARCHITEKTUR.md"


def _check_line_limits(errors: list[str]) -> None:
    """Meldet beruehrte Dateien ueber dem Limit und Ausnahmen ohne Begruendung.

    bw-gui wird wie zur Laufzeit ueber den Geschwister-Checkout gefunden
    (``bw_libs.shared_gui_core.ensure_bw_gui_on_path``); fehlt er, ist das selbst
    ein Fehler, weil der Check sonst still entfiele.
    """
    from bw_libs.shared_gui_core import ensure_bw_gui_on_path

    ensure_bw_gui_on_path()
    try:
        from bw_gui.testing.line_limits import check_repo
    except ImportError as exc:
        errors.append(f"line-limit check unavailable: bw_gui.testing.line_limits not importable ({exc})")
        return
    errors.extend(check_repo(ROOT, LINE_LIMIT_ARCH_DOC))
