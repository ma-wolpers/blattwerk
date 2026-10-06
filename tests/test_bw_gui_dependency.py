"""Laufzeitabhängigkeit bw-gui: Nachbar-Repo `<blattwerk>/../bw-gui/src` (Invariante, siehe ARCHITEKTUR.md).

blattwerk pinnt bw-gui nicht (kein Submodul); es lädt immer den Nachbarordner.
Dieser Test läuft lokal und in der GitHub-CI auf einem frischen Checkout beider
Repos nebeneinander (`.github/workflows/quality-guardrails.yml`) und beweist
damit, dass die Abhängigkeit nicht nur zufällig auf einem Entwicklerrechner
funktioniert.
"""

from __future__ import annotations

from pathlib import Path

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_bw_gui_is_loaded_from_sibling_repo():
    resolved = ensure_bw_gui_on_path()

    assert resolved is not None, "bw-gui fehlt: als Nachbarordner neben blattwerk klonen (siehe README)"
    assert Path(resolved).resolve() == (REPO_ROOT.parent / "bw-gui" / "src").resolve()


def test_bw_gui_provides_widgets_blattwerk_needs():
    ensure_bw_gui_on_path()
    import bw_gui
    from bw_gui.widgets import CollapsibleSection

    assert Path(bw_gui.__file__).resolve().is_relative_to((REPO_ROOT.parent / "bw-gui" / "src").resolve())
    assert callable(CollapsibleSection.set_collapsed)
