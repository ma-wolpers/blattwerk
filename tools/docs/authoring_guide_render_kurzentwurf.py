"""Rendert die Kurzentwurf-Anleitung (`docs/nutzer/ANLEITUNG_KURZENTWURF.md`).

Verbraucht ausschließlich `MarkdownConventionCatalog.kurzentwurf`-Fakten
(`app/core/markdown_conventions.py`) und redaktionelle Prosa
(`authoring_guide_prose.PROSE_SECTIONS`, über `authoring_guide_render_shared._prose`)
-- erfindet selbst kein DSL-Wissen.
"""

from __future__ import annotations

from app.core.document_type_registry import DOCUMENT_TYPE_KURZENTWURF
from app.core.document_type_templates import build_new_document_content
from app.core.kurzentwurf_runtime.model import (
    PHASE_PLACEMENT_AFTER_LESSON,
    PHASE_PLACEMENT_BUFFER,
    PHASE_PLACEMENT_REGULAR,
)
from app.core.markdown_conventions import MarkdownConventionCatalog

from authoring_guide_render_shared import _AUTOGEN_HEADER, _fenced, _prose, _render_inline_marks_section


_PLACEMENT_LABELS = {
    PHASE_PLACEMENT_REGULAR: "beliebig",
    PHASE_PLACEMENT_BUFFER: "chronologisch im Verlauf, nie am Ende (`KZF049`)",
    PHASE_PLACEMENT_AFTER_LESSON: "nach der Stunde",
}
"""Anzeigetext je `PhaseSpec.placement`; ein fehlender Wert lässt die Generierung scheitern."""


def _render_kurzentwurf_phase_table(catalog: MarkdownConventionCatalog) -> str:
    """Rendert die Phasen-Tabelle (Anzeigename/Hashtag/Zeitpflicht/Platz) aus `PHASE_SPECS`."""
    lines = ["| Anzeigename | Hashtag | Braucht `t=`? | Platz im Verlauf |", "|---|---|---|---|"]
    for spec in catalog.kurzentwurf.phase_specs:
        lines.append(
            f"| `{spec.display_name}` | `#{spec.hashtag}` | "
            f"{'ja' if spec.requires_explicit_time else 'nein'} | {_PLACEMENT_LABELS[spec.placement]} |"
        )
    return "\n".join(lines)


def _render_kurzentwurf_line_marker_reference(catalog: MarkdownConventionCatalog) -> str:
    """Rendert eine Bullet-Liste mit einer Prosa-Erklärung pro Zeilenmarker aus `LINE_MARKER_SPECS`."""
    parts = []
    for spec in catalog.kurzentwurf.line_markers:
        parts.append(f"- **`{spec.token}`**: {_prose(f'kurzentwurf:marker:{spec.token}')}")
    return "\n".join(parts)


def _render_kurzentwurf_social_form_table(catalog: MarkdownConventionCatalog) -> str:
    """Rendert die Sozialform-Tabelle (Kürzel/Bedeutung/Schreibweisen/Gespräch) aus `SOCIAL_FORM_SPECS`."""
    lines = [
        "| Kürzel | Bedeutung | Weitere Schreibweisen | Unterrichtsgespräch (`ant<` erwartet) |",
        "|---|---|---|---|",
    ]
    for spec in catalog.kurzentwurf.social_forms:
        aliases = ", ".join(f"`{alias}`" for alias in spec.aliases) or "--"
        lines.append(
            f"| `{spec.abbreviation}` | {spec.meaning} | {aliases} | {'ja' if spec.conversation else 'nein'} |"
        )
    return "\n".join(lines)


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
        + _render_kurzentwurf_line_marker_reference(catalog)
        + "\n\n### Sozialformen in `U>`\n\n"
        + _prose("kurzentwurf:social_forms")
        + "\n\n"
        + _render_kurzentwurf_social_form_table(catalog),
        "## 5. Legacy-Erkennungs-Felder (nicht aktiv verwenden)\n\n"
        + _prose("kurzentwurf:legacy_detection_only")
        + "\n\n"
        + _render_kurzentwurf_legacy_field_details(catalog),
        "## 6. Inline-Formatierung in Zellentext\n\n"
        "Innerhalb von Zelleninhalten (Schritte/Aktivitäten/Umgebung) gilt dieselbe zentrale "
        "Inline-Formatierung wie im Arbeitsblatt-Editor -- Text markieren und eine Marker-Taste "
        "drücken. Die Hervorhebungsfarbe (`==...==`) ist in Kurzentwurf-Dokumenten fest, da "
        "Kurzentwurf kein eigenes Farbprofil hat.\n\n"
        + _render_inline_marks_section(catalog, "kurzentwurf"),
        "## 7. Zeilenumbrüche und Formeln in Zellen\n\n"
        + _prose("kurzentwurf:line_breaks")
        + "\n\n"
        + _prose("kurzentwurf:math_formulas"),
    ]

    return _AUTOGEN_HEADER + "\n\n".join(sections) + "\n"
