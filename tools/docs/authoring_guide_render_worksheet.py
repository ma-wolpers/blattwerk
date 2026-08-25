"""Rendert die Arbeitsblatt-/Präsentations-Anleitung (`docs/ANLEITUNG_ARBEITSBLATT_PRAESENTATION.md`).

Verbraucht ausschließlich `MarkdownConventionCatalog`-Fakten
(`app/core/markdown_conventions.py`) und redaktionelle Prosa
(`authoring_guide_prose.PROSE_SECTIONS`, über `authoring_guide_render_shared._prose`)
-- erfindet selbst kein DSL-Wissen.
"""

from __future__ import annotations

import authoring_guide_prose

from app.core.blatt_validator_constants import MISSING
from app.core.document_types import (
    DOCUMENT_TYPE_PRESENTATION,
    DOCUMENT_TYPE_WORKSHEET,
    build_new_document_content,
)
from app.core.markdown_conventions import MarkdownConventionCatalog

from authoring_guide_coverage import _option_prose_keys
from authoring_guide_render_shared import _AUTOGEN_HEADER, _fenced, _prose


def _kind_label(kind: str) -> str:
    return {
        "enum": "Enum",
        "boolean": "Bool",
        "integer": "Ganzzahl",
        "number": "Zahl",
        "css_length": "CSS-Länge",
        "url": "URL",
        "text": "Text",
    }.get(kind, kind)


def _default_label(default: object) -> str:
    if default is MISSING:
        return "--"
    if default is None:
        return "*(keiner)*"
    return f"`{default}`"


def _option_explanation(catalog: MarkdownConventionCatalog, block_name: str, spec: object) -> str:
    key, allow_supplement = _option_prose_keys(catalog, block_name, spec)
    text = _prose(key)
    if not allow_supplement:
        return text

    supplement_key = f"block:{block_name}.{spec.name}"
    if supplement_key in authoring_guide_prose.PROSE_SECTIONS:
        text += f" *Besonderheit bei `{block_name}`:* {_prose(supplement_key)}"
    return text


def _render_frontmatter_table(catalog: MarkdownConventionCatalog) -> str:
    lines = ["| Feld | Pflicht | Art | Erlaubte Werte | Geprüft? |", "|---|---|---|---|---|"]
    for name in catalog.required_frontmatter_fields:
        lines.append(f"| `{name}` | ja | Text | -- | ja |")
    for field in catalog.optional_frontmatter_fields:
        allowed = ", ".join(f"`{v}`" for v in sorted(field.allowed_values)) if field.allowed_values else "--"
        lines.append(
            f"| `{field.name}` | nein | {field.kind} | {allowed} | {'ja' if field.validated else 'nein'} |"
        )
    return "\n".join(lines)


def _render_frontmatter_details(catalog: MarkdownConventionCatalog) -> str:
    parts = []
    for name in catalog.required_frontmatter_fields:
        parts.append(f"- **`{name}`** (Pflichtfeld): {_prose(f'frontmatter:{name}')}")
    for field in catalog.optional_frontmatter_fields:
        parts.append(f"- **`{field.name}`** (optional): {_prose(f'frontmatter:{field.name}')}")
    return "\n".join(parts)


def _render_option_table(catalog: MarkdownConventionCatalog, block) -> str:
    if not block.options:
        return "Keine Optionen."

    lines = [
        "| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |",
        "|---|---|---|---|---|---|",
    ]
    for spec in sorted(block.options, key=lambda s: s.name):
        allowed = ", ".join(f"`{v}`" for v in sorted(spec.allowed_values)) if spec.allowed_values else "--"
        explanation = _option_explanation(catalog, block.name, spec)
        lines.append(
            f"| `{spec.name}` | {_kind_label(spec.kind)} | {allowed} | "
            f"{'ja' if spec.validated else 'nein'} | {_default_label(spec.default)} | {explanation} |"
        )
    return "\n".join(lines)


def _render_block_insert_example(block) -> str:
    """Rendert das Ctrl+B-Beispiel eines Blocks als gefencten Codeblock, falls vorhanden.

    Entfernt den `\x01`-Cursor-Marker (nur für den Editor relevant) und gibt
    `""` zurück, wenn der Block keinen Ctrl+B-Menüeintrag hat.
    """
    if not block.insert_snippet:
        return ""
    cleaned = block.insert_snippet.replace("\x01", "")
    return "\n\n**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):\n\n" + _fenced(cleaned)


def _render_block_reference(catalog: MarkdownConventionCatalog) -> str:
    parts = []
    for block in catalog.blocks:
        parts.append(
            f"### `{block.name}`\n\n{_prose(f'block:{block.name}')}\n\n"
            + _render_option_table(catalog, block)
            + _render_block_insert_example(block)
        )
    return "\n\n".join(parts)


def _render_value_list(title: str, values: frozenset[str]) -> str:
    joined = ", ".join(f"`{value}`" for value in sorted(values))
    return f"**{title}:** {joined}"


def _render_control_marker_reference(catalog: MarkdownConventionCatalog) -> str:
    parts = []
    for marker in sorted(catalog.control_markers, key=lambda m: m.name):
        parts.append(f"- **{marker.name}**: {_prose(f'marker:{marker.name}')}")
    return "\n".join(parts)


def _render_geometry_section(catalog: MarkdownConventionCatalog) -> str:
    geometry = catalog.geometry
    line_styles = ", ".join(f"`{style}`" for style in sorted(geometry.line_styles))
    parts = [
        f"### Blockoptionen\n\n{_prose('geometry:block_options')}\n\nErlaubte `line`-Werte: {line_styles}."
    ]
    for entry in sorted(geometry.entries, key=lambda e: e.section):
        keys = ", ".join(f"`{key}`" for key in sorted(entry.allowed_keys))
        parts.append(f"### `{entry.section}`\n\n{_prose(f'geometry:{entry.section}')}\n\nErlaubte Keys: {keys}.")

    example = (
        "```markdown\n"
        ":::geometry rows=20 cols=20 axis=true origin=\"10,10\"\n"
        "points:\n"
        "  - {x: 2, y: 3, label: \"A\", color: \"#2563eb\", thickness: 2}\n"
        "pairs:\n"
        "  - {x1: 0, y1: 0, x2: 4, y2: 4, line: dashed, label: \"Strecke g\"}\n"
        "functions:\n"
        "  - {expr: \"x^2\", domain: \"-3:3\", label: \"f(x) = x^2\", color: \"#dc2626\", thickness: 1.5}\n"
        ":::\n"
        "```"
    )
    parts.append(
        "### Repräsentatives Beispiel\n\n"
        + example
        + "\n\nFlow-Style-YAML (`{key: value, ...}` auf einer Zeile) ist die in den "
        "Blattwerk-Beispielen übliche Schreibweise für Geometry-Einträge -- Block-Style "
        "(`key:` mit eingerückten Folgezeilen) ist gleichwertig und wird identisch geparst. "
        "`axis=true` **und** ein gültiges `origin` sind zusammen nötig, damit `functions` "
        "überhaupt gerendert wird und `points`/`pairs` als Mathe-Koordinaten statt "
        "Rasterkoordinaten interpretiert werden (siehe Besonderheit bei `axis`/`origin` oben)."
    )
    return "\n\n".join(parts)


def render_worksheet_presentation_guide(catalog: MarkdownConventionCatalog) -> str:
    """Rendert die kombinierte Arbeitsblatt-/Präsentations-Anleitung, deterministisch."""
    worksheet_example = build_new_document_content(DOCUMENT_TYPE_WORKSHEET, {})
    presentation_example = build_new_document_content(DOCUMENT_TYPE_PRESENTATION, {})

    sections = [
        "# Arbeitsblatt & Präsentation erstellen\n\n"
        "Diese Anleitung ist die normative Referenz für den Blattwerk-Markdown-Dialekt, "
        "den Arbeitsblätter und Präsentationen gemeinsam nutzen (dieselben `:::`-Blöcke, "
        "dasselbe Frontmatter). Sie wird automatisch aus dem Code erzeugt "
        "(`app/core/markdown_conventions.py`) -- Blocktypen, Optionen und Frontmatter-Felder "
        "können hier nicht veralten, weil sie direkt aus den Konstanten stammen, die der "
        "Validator selbst zur Prüfung verwendet. Reine Stilpräferenzen (keine Korrektheitsregeln) "
        "stehen separat in [`docs/EMPFEHLUNGEN_STIL_ARBEITSBLATT_PRAESENTATION.md`]"
        "(EMPFEHLUNGEN_STIL_ARBEITSBLATT_PRAESENTATION.md).",
        "## 1. Grundidee\n\n"
        "Ein Blattwerk-Dokument besteht aus YAML-Frontmatter (Pflicht) gefolgt von einer Folge "
        "semantischer `:::blocktyp ...` ... `:::`-Blöcke. Ob ein Dokument als Arbeitsblatt oder "
        "als Präsentation gerendert wird, entscheidet allein das Frontmatter-Feld `mode` -- der "
        "Blockdialekt selbst ist identisch. Sichtbarkeit pro Block wird über `mode=worksheet|"
        "solution` gesteuert (Standard: in beiden Ausgaben sichtbar).\n\n"
        + _prose("blocks:closing_rule")
        + "\n\n"
        + _prose("markdown:math_formulas"),
        "## 2. Schnellstart: Arbeitsblatt\n\n" + _fenced(worksheet_example),
        "## 3. Schnellstart: Präsentation\n\n" + _fenced(presentation_example)
        + "\n\n`--#` setzt den Abschnittsnamen für die Footer-Navigation, `--!` erzwingt eine neue "
        "Folie -- siehe Control-Marker-Referenz unten für alle Marker (inkl. `-+`, das im "
        "Gegensatz zu `--!` **keine** neue Folie erzeugt, siehe dortige Warnung).\n\n"
        "### Sichtbarkeit in Präsentationen\n\n"
        + _prose("presentation:visibility"),
        "## 4. Frontmatter-Referenz\n\n" + _render_frontmatter_table(catalog)
        + "\n\n" + _render_frontmatter_details(catalog),
        "## 5. Blockreferenz\n\n" + _render_block_reference(catalog),
        "## 6. Wertlisten für `work`/`action`/`hint`\n\n"
        + _render_value_list("work (Arbeitsform bei task/subtask)", catalog.work_values)
        + "\n\n"
        + _render_value_list("action (Tätigkeits-Hinweis bei task)", catalog.action_values)
        + "\n\n"
        + _render_value_list("hint (Lernhinweis bei task)", catalog.hint_values),
        "## 7. Control-Marker-Referenz\n\n" + _render_control_marker_reference(catalog),
        "## 8. Geometry im Detail (`:::geometry`)\n\n" + _render_geometry_section(catalog),
        "## 9. Sichtbarkeitsmarker in Antwortinhalten\n\n"
        "Für textbasierte Antwort-Blocktypen (`lines`, `grid`, ...) steuern Zeilenmarker "
        "`§`/`%`/`&` (am Zeilenanfang) bzw. Inline-Token `§{...}`/`%{...}`/`&{...}` "
        "(mitten in der Zeile), ob ein Textteil nur im Arbeitsblatt, nur in der Lösung oder in "
        "beiden erscheint. Text ohne Marker ist standardmäßig in beiden Modi sichtbar.",
    ]

    return _AUTOGEN_HEADER + "\n\n".join(sections) + "\n"
