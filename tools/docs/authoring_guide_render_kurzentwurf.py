"""Rendert die Kurzentwurf-Anleitung (`docs/nutzer/ANLEITUNG_KURZENTWURF.md`).

Verbraucht ausschließlich `MarkdownConventionCatalog.kurzentwurf`-Fakten
(`app/core/markdown_conventions.py`) und redaktionelle Prosa
(`authoring_guide_prose.PROSE_SECTIONS`, über `authoring_guide_render_shared._prose`)
-- erfindet selbst kein DSL-Wissen.
"""

from __future__ import annotations

from app.core.document_types import DOCUMENT_TYPE_KURZENTWURF, build_new_document_content
from app.core.markdown_conventions import MarkdownConventionCatalog

from authoring_guide_render_shared import _AUTOGEN_HEADER, _fenced, _prose


def _render_kurzentwurf_phase_table(catalog: MarkdownConventionCatalog) -> str:
    """Rendert die Phasen-Tabelle (Anzeigename/Hashtag/Zeitpflicht) aus `PHASE_SPECS`."""
    lines = ["| Anzeigename | Hashtag | Braucht `t=`? |", "|---|---|---|"]
    for spec in catalog.kurzentwurf.phase_specs:
        lines.append(
            f"| `{spec.display_name}` | `#{spec.hashtag}` | "
            f"{'ja' if spec.requires_explicit_time else 'nein'} |"
        )
    return "\n".join(lines)


def _render_kurzentwurf_line_marker_reference(catalog: MarkdownConventionCatalog) -> str:
    """Rendert eine Bullet-Liste mit einer Prosa-Erklärung pro Zeilenmarker aus `LINE_MARKER_SPECS`."""
    parts = []
    for spec in catalog.kurzentwurf.line_markers:
        parts.append(f"- **`{spec.token}`**: {_prose(f'kurzentwurf:marker:{spec.token}')}")
    return "\n".join(parts)


def _render_kurzentwurf_legacy_field_details(catalog: MarkdownConventionCatalog) -> str:
    """Rendert eine Bullet-Liste mit einer Erklärung pro Legacy-Erkennungsfeld."""
    parts = []
    for name in sorted(catalog.kurzentwurf.legacy_detection_only_keys):
        parts.append(f"- **`{name}`**: {_prose(f'kurzentwurf:legacy:{name}')}")
    return "\n".join(parts)


def render_kurzentwurf_guide(catalog: MarkdownConventionCatalog) -> str:
    """Rendert die Kurzentwurf-Anleitung, deterministisch."""
    kurzentwurf_example = build_new_document_content(DOCUMENT_TYPE_KURZENTWURF, {})

    identity_keys = ", ".join(f"`{key}`" for key in sorted(catalog.kurzentwurf.identity_meta_keys))

    sections = [
        "# Kurzentwurf erstellen\n\n"
        "Kurzentwurf ist ein eigener Blattwerk-Dokumenttyp mit einer **eigenen DSL** -- nicht dem "
        "`:::`-Blockdialekt aus der Arbeitsblatt-/Präsentations-Anleitung. Diese Anleitung wird "
        "automatisch aus dem Code erzeugt (`app/core/markdown_conventions.py`). Fehlermeldungen tragen "
        "stabile Codes wie `KZF011`/`KZF152` -- die vollständige Liste steht in "
        "[`docs/nutzer/VALIDATOR.md`](VALIDATOR.md#kurzentwurf-dsl-kzf). Reine Schreibkonventionen und "
        "didaktische Empfehlungen (keine Korrektheitsregeln) stehen separat in "
        "[`docs/nutzer/EMPFEHLUNGEN_STIL_KURZENTWURF.md`](EMPFEHLUNGEN_STIL_KURZENTWURF.md).",
        "## 1. Schnellstart\n\n" + _fenced(kurzentwurf_example),
        "## 2. Frontmatter/Identitäts-Metadaten\n\n"
        + _prose("kurzentwurf:identity_meta")
        + f"\n\nAkzeptierte Schlüssel (alle gleichwertig, case-insensitiv): {identity_keys}.",
        "## 3. Phasen\n\n"
        + _prose("kurzentwurf:phases")
        + "\n\n"
        + _render_kurzentwurf_phase_table(catalog),
        "## 4. Zeilenmarker innerhalb einer Phase\n\n"
        + _prose("kurzentwurf:markers")
        + "\n\n"
        + _render_kurzentwurf_line_marker_reference(catalog),
        "## 5. Legacy-Erkennungs-Felder (nicht aktiv verwenden)\n\n"
        + _prose("kurzentwurf:legacy_detection_only")
        + "\n\n"
        + _render_kurzentwurf_legacy_field_details(catalog),
    ]

    return _AUTOGEN_HEADER + "\n\n".join(sections) + "\n"
