#!/usr/bin/env python3
"""Generiert die Blattwerk-Autoren-Anleitungen aus `app.core.markdown_conventions`.

Trennt strikt zwei Verantwortlichkeiten:
- **Katalog-Fakten** (`MarkdownConventionCatalog`, siehe `markdown_conventions.py`):
  deterministisch aus dem Code abgeleitet, niemals hier erfunden.
- **Redaktionelle Prosa** (`PROSE_SECTIONS`, `authoring_guide_prose.py`):
  von Hand gepflegte Erklärungen, ohne die die Anleitung nur eine trockene
  Optionsliste wäre.

`assert_prose_coverage()` verhindert, dass ein neues DSL-Element (neuer
Blocktyp, neues Frontmatter-Feld, neuer Control-Marker, neue Geometry-
Sektion) unbemerkt ohne redaktionelle Erklärung in die generierte
Anleitung rutscht.

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

from app.core.document_types import (  # noqa: E402
    DOCUMENT_TYPE_KURZENTWURF,
    DOCUMENT_TYPE_PRESENTATION,
    DOCUMENT_TYPE_WORKSHEET,
    build_new_document_content,
)
from app.core.blatt_validator_constants import MISSING  # noqa: E402
from app.core.markdown_conventions import (  # noqa: E402
    MarkdownConventionCatalog,
    collect_markdown_conventions,
)

from authoring_guide_prose import PROSE_SECTIONS  # noqa: E402

WORKSHEET_PRESENTATION_GUIDE_PATH = ROOT / "docs" / "ANLEITUNG_ARBEITSBLATT_PRAESENTATION.md"
KURZENTWURF_GUIDE_PATH = ROOT / "docs" / "ANLEITUNG_KURZENTWURF.md"

_AUTOGEN_HEADER = (
    "<!--\n"
    "Automatisch generiert aus app/core/markdown_conventions.py.\n"
    "NICHT VON HAND BEARBEITEN.\n"
    "Neu erzeugen: python tools/docs/generate_authoring_guides.py\n"
    "-->\n\n"
)


class ProseCoverageError(Exception):
    """Ein Katalogeintrag hat keine zugehörige Prosa-Erklärung in `PROSE_SECTIONS`."""


def _option_variant_key(spec: object) -> tuple:
    """Fakten, die entscheiden, ob zwei Blöcke 'dieselbe' Option meinen (Default zählt nicht mit)."""
    return (spec.kind, spec.allowed_values, spec.validated)


def _majority_variant_by_option_name(catalog: MarkdownConventionCatalog) -> dict[str, tuple]:
    """Für jeden Optionsnamen: die von den meisten Blöcken geteilte Variante (kind/allowed_values/validated).

    Nur wenn diese "Mehrheitsvariante" von **mindestens zwei** Blöcken
    geteilt wird, gilt die Option als generisches, block-übergreifendes
    Konzept (`option:<name>`-Prosa reicht). Bei genau einem Nutzer pro
    Variante (z. B. `alignment` bei `qrcode` vs. `table` -- zwei völlig
    verschiedene Bedeutungen) gibt es keine Mehrheit; jeder Block braucht
    dann eine eigene `block:<block>.<name>`-Erklärung, keine generische.
    """
    from collections import Counter

    counters: dict[str, Counter] = {}
    for block in catalog.blocks:
        for spec in block.options:
            counters.setdefault(spec.name, Counter())[_option_variant_key(spec)] += 1

    majority: dict[str, tuple] = {}
    for name, counter in counters.items():
        variant, count = counter.most_common(1)[0]
        if count >= 2:
            majority[name] = variant
    return majority


def _option_prose_keys(catalog: MarkdownConventionCatalog, block_name: str, spec: object) -> tuple[str, bool]:
    """Liefert (bevorzugter Prosa-Key, ob zusätzlich noch ein Shared-Key existieren darf) für eine Option.

    Rückgabe `(key, allow_shared_supplement)`: wenn die Option des Blocks
    der Mehrheitsvariante entspricht, ist `key` der generische
    `option:<name>`-Key (ein optionales `block:<block>.<name>`-Supplement
    darf zusätzlich existieren). Weicht der Block von der Mehrheit ab
    (oder gibt es gar keine Mehrheit), ist `key` der block-eigene
    `block:<block>.<name>`-Key, der dann **alleinstehend** gilt (kein
    Shared-Text, der inhaltlich falsch wäre).
    """
    majority = _majority_variant_by_option_name(catalog)
    generic_key = f"option:{spec.name}"
    specific_key = f"block:{block_name}.{spec.name}"

    if majority.get(spec.name) == _option_variant_key(spec):
        return generic_key, True
    return specific_key, False


def _geometry_prose_keys() -> tuple[str, ...]:
    return (
        "geometry:block_options",
        "geometry:points",
        "geometry:sequence",
        "geometry:pairs",
        "geometry:functions",
    )


def _kurzentwurf_prose_keys() -> tuple[str, ...]:
    return (
        "kurzentwurf:phases",
        "kurzentwurf:identity_meta",
        "kurzentwurf:legacy_detection_only",
        "kurzentwurf:markers",
    )


def assert_prose_coverage(catalog: MarkdownConventionCatalog) -> None:
    """Wirft `ProseCoverageError`, wenn ein Katalogeintrag keine Prosa-Erklärung hat.

    Prüft auf zwei Ebenen: jeder Blocktyp braucht `block:<name>` (die
    einleitende Blockbeschreibung); jede Option jedes Blocks braucht
    *mindestens* die von `_option_prose_keys` bestimmte Erklärung (generisch
    `option:<name>` für Mehrheitsvarianten, sonst zwingend die block-eigene
    `block:<block>.<name>`) -- ein block-spezifisches Supplement zusätzlich
    zum generischen Text ist immer erlaubt, aber nie Pflicht.
    """
    required_keys: list[str] = []
    required_keys.extend(f"block:{block.name}" for block in catalog.blocks)
    required_keys.extend(f"frontmatter:{name}" for name in catalog.required_frontmatter_fields)
    required_keys.extend(f"frontmatter:{field.name}" for field in catalog.optional_frontmatter_fields)
    required_keys.extend(f"marker:{marker.name}" for marker in catalog.control_markers)
    required_keys.extend(_geometry_prose_keys())
    required_keys.extend(_kurzentwurf_prose_keys())

    missing = [key for key in required_keys if key not in PROSE_SECTIONS]

    for block in catalog.blocks:
        for spec in block.options:
            key, _allow_supplement = _option_prose_keys(catalog, block.name, spec)
            if key not in PROSE_SECTIONS:
                missing.append(key)

    if missing:
        raise ProseCoverageError(
            "Fehlende Prosa-Abschnitte in tools/docs/authoring_guide_prose.py: "
            + ", ".join(sorted(set(missing)))
        )


def _prose(key: str) -> str:
    return PROSE_SECTIONS[key]


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
    if supplement_key in PROSE_SECTIONS:
        text += f" *Besonderheit bei `{block_name}`:* {_prose(supplement_key)}"
    return text


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


def _render_block_reference(catalog: MarkdownConventionCatalog) -> str:
    parts = []
    for block in catalog.blocks:
        parts.append(
            f"### `{block.name}`\n\n{_prose(f'block:{block.name}')}\n\n"
            + _render_option_table(catalog, block)
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


def _fenced(content: str) -> str:
    return f"```markdown\n{content.strip()}\n```"


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
        "Validator selbst zur Prüfung verwendet.",
        "## 1. Grundidee\n\n"
        "Ein Blattwerk-Dokument besteht aus YAML-Frontmatter (Pflicht) gefolgt von einer Folge "
        "semantischer `:::blocktyp ...` ... `:::`-Blöcke. Ob ein Dokument als Arbeitsblatt oder "
        "als Präsentation gerendert wird, entscheidet allein das Frontmatter-Feld `mode` -- der "
        "Blockdialekt selbst ist identisch. Sichtbarkeit pro Block wird über `mode=worksheet|"
        "solution` gesteuert (Standard: in beiden Ausgaben sichtbar).",
        "## 2. Schnellstart: Arbeitsblatt\n\n" + _fenced(worksheet_example),
        "## 3. Schnellstart: Präsentation\n\n" + _fenced(presentation_example)
        + "\n\n`--#` setzt den Abschnittsnamen für die Footer-Navigation, `-+` erzeugt einen "
        "neuen Frame, der den bisherigen Folieninhalt beibehält -- siehe Control-Marker-"
        "Referenz unten.",
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


def render_kurzentwurf_guide(catalog: MarkdownConventionCatalog) -> str:
    """Rendert die Kurzentwurf-Anleitung, deterministisch."""
    kurzentwurf_example = build_new_document_content(DOCUMENT_TYPE_KURZENTWURF, {})

    identity_keys = ", ".join(f"`{key}`" for key in sorted(catalog.kurzentwurf.identity_meta_keys))
    legacy_keys = ", ".join(f"`{key}`" for key in sorted(catalog.kurzentwurf.legacy_detection_only_keys))
    phases = "\n".join(f"- `{phase}`" for phase in catalog.kurzentwurf.phases)

    sections = [
        "# Kurzentwurf erstellen\n\n"
        "Kurzentwurf ist ein eigener Blattwerk-Dokumenttyp mit einer **eigenen DSL** -- nicht dem "
        "`:::`-Blockdialekt aus der Arbeitsblatt-/Präsentations-Anleitung. Diese Anleitung wird "
        "automatisch aus dem Code erzeugt (`app/core/markdown_conventions.py`).",
        "## 1. Schnellstart\n\n" + _fenced(kurzentwurf_example),
        "## 2. Frontmatter/Identitäts-Metadaten\n\n"
        + _prose("kurzentwurf:identity_meta")
        + f"\n\nAkzeptierte Schlüssel (alle gleichwertig, case-insensitiv): {identity_keys}.",
        "## 3. Phasen\n\n" + _prose("kurzentwurf:phases") + "\n\nZulässige Phasennamen:\n\n" + phases,
        "## 4. Zeilenmarker innerhalb einer Phase\n\n" + _prose("kurzentwurf:markers"),
        "## 5. Legacy-Erkennungs-Felder (nicht aktiv verwenden)\n\n"
        + _prose("kurzentwurf:legacy_detection_only")
        + f"\n\nBetroffene Felder: {legacy_keys}.",
    ]

    return _AUTOGEN_HEADER + "\n\n".join(sections) + "\n"


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
