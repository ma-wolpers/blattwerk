#!/usr/bin/env python3
"""Generiert die Blattwerk-Autoren-Anleitungen aus `app.core.markdown_conventions`.

Trennt strikt zwei Verantwortlichkeiten:
- **Katalog-Fakten** (`MarkdownConventionCatalog`, siehe `markdown_conventions.py`):
  deterministisch aus dem Code abgeleitet, niemals hier erfunden.
- **Redaktionelle Prosa** (`PROSE_SECTIONS`, `authoring_guide_prose.py`):
  von Hand gepflegte Erklärungen, ohne die die Anleitung nur eine trockene
  Optionsliste wäre.

Dieses Modul ist nur noch der schlanke Einstiegspunkt (CLI + Orchestrierung);
die eigentliche Logik lebt in fokussierten Geschwister-Modulen (300-Zeilen-
Konvention):
- `authoring_guide_coverage.py`: `assert_prose_coverage()`/`ProseCoverageError`.
- `authoring_guide_render_shared.py`: Autogen-Header, `_prose()`, `_fenced()`.
- `authoring_guide_render_worksheet.py`: Arbeitsblatt-/Präsentations-Anleitung.
- `authoring_guide_render_kurzentwurf.py`: Kurzentwurf-Anleitung.

Aufruf: `python tools/docs/generate_authoring_guides.py [--check]`
(`--check` schreibt nichts, vergleicht nur mit den vorhandenen Dateien und
liefert Exit-Code 1 bei Abweichung/fehlender Coverage -- Grundlage für den
CI-Guardrail-Check in `tools/ci/check_ai_guardrails.py`.)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from app.core.blatt_validator_constants import MISSING  # noqa: E402
from app.core.markdown_conventions import collect_markdown_conventions  # noqa: E402

from authoring_guide_coverage import ProseCoverageError, assert_prose_coverage  # noqa: E402
from authoring_guide_render_kurzentwurf import render_kurzentwurf_guide  # noqa: E402
from authoring_guide_render_worksheet import render_worksheet_presentation_guide  # noqa: E402

__all__ = [
    "MISSING",
    "ProseCoverageError",
    "assert_prose_coverage",
    "render_kurzentwurf_guide",
    "render_worksheet_presentation_guide",
    "generate_guides",
    "main",
]

WORKSHEET_PRESENTATION_GUIDE_PATH = ROOT / "docs" / "ANLEITUNG_ARBEITSBLATT_PRAESENTATION.md"
KURZENTWURF_GUIDE_PATH = ROOT / "docs" / "ANLEITUNG_KURZENTWURF.md"


def generate_guides() -> dict[Path, str]:
    """Rendert beide Anleitungen frisch aus dem aktuellen Katalogstand."""
    catalog = collect_markdown_conventions()
    assert_prose_coverage(catalog)
    return {
        WORKSHEET_PRESENTATION_GUIDE_PATH: render_worksheet_presentation_guide(catalog),
        KURZENTWURF_GUIDE_PATH: render_kurzentwurf_guide(catalog),
    }


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    check_only = "--check" in args

    try:
        guides = generate_guides()
    except ProseCoverageError as error:
        print(f"Fehler: {error}")
        return 1

    if check_only:
        mismatched = []
        for path, content in guides.items():
            existing = path.read_text(encoding="utf-8") if path.exists() else None
            if existing != content:
                mismatched.append(str(path))
        if mismatched:
            print("Generierte Anleitungen sind veraltet: " + ", ".join(mismatched))
            print("Neu erzeugen: python tools/docs/generate_authoring_guides.py")
            return 1
        print("Generierte Anleitungen sind aktuell.")
        return 0

    for path, content in guides.items():
        path.write_text(content, encoding="utf-8")
        print(f"Geschrieben: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
