"""Rendert die Schilder-Anleitung (`docs/nutzer/ANLEITUNG_SCHILD.md`).

Schilder (`.sbw`) haben keinen Blockdialekt, deshalb steht die Prosa hier
direkt statt in `authoring_guide_prose.PROSE_SECTIONS`. Alle *Fakten* --
erlaubte Werte, Standardwerte, Schnellstart -- kommen aber aus dem Code
(`schild_render`, `document_type_templates`), damit die Anleitung nicht
veralten kann: `generate_authoring_guides.py --check` schlägt an, sobald sich
dort etwas ändert.
"""

from __future__ import annotations

from app.core.document_type_registry import DOCUMENT_TYPE_SCHILD
from app.core.document_type_templates import build_new_document_content
from app.core.markdown_conventions import MarkdownConventionCatalog
from app.core.schild_render import FONT_SIZE_MODES, MAX_MARGIN_MM, ORIENTATIONS, SEPARATOR, SchildOptions

from authoring_guide_render_shared import _AUTOGEN_HEADER, _fenced


def _values(values: tuple[str, ...]) -> str:
    """Formatiert erlaubte Werte als `a` / `b` (ein `|` bräche die Tabelle)."""
    return " / ".join(f"`{value}`" for value in values)


def _options_table() -> str:
    """Tabelle der Frontmatter-Optionen mit Standardwerten aus `SchildOptions`."""
    defaults = SchildOptions()
    rows = [
        ("ausrichtung", _values(ORIENTATIONS), f"`{defaults.ausrichtung}`", "A4 hochkant oder quer."),
        ("fett", "`ja` / `nein`", "`ja`" if defaults.fett else "`nein`", "Schrift fett oder normal."),
        ("rand", f"Zahl in mm (0–{MAX_MARGIN_MM:g})", f"`{defaults.rand_mm:g}`", "Abstand zum Blattrand auf allen Seiten."),
        (
            "schriftgroesse",
            _values(FONT_SIZE_MODES),
            f"`{defaults.schriftgroesse}`",
            "`einheitlich`: alle Schilder gleich groß – so groß, dass auch das längste passt. "
            "`maximal`: jedes Schild für sich so groß wie möglich.",
        ),
    ]
    header = "| Option | Werte | Standard | Wirkung |\n| --- | --- | --- | --- |\n"
    return header + "\n".join(f"| `{key}` | {values} | {default} | {effect} |" for key, values, default, effect in rows)


def render_schild_guide(catalog: MarkdownConventionCatalog) -> str:
    """Rendert die Schilder-Anleitung, deterministisch.

    Args:
        catalog: Wird nicht gebraucht (Schilder nutzen keine Katalogfakten);
            Signatur wie bei den anderen Anleitungs-Renderern.
    """
    del catalog
    example = build_new_document_content(DOCUMENT_TYPE_SCHILD, {})
    sections = [
        "# Schilder erstellen\n\n"
        "Ein Schilder-Dokument (`.sbw`) macht aus jedem Schild eine eigene A4-Seite, auf der nur "
        "der Text steht – mittig und so groß wie möglich. Typisch: Begriffe für eine Sortier- oder "
        "Zuordnungsaufgabe, Stationsschilder, Tafelüberschriften.",
        "## 1. Schnellstart\n\n" + _fenced(example),
        "## 2. Schilder trennen\n\n"
        f"Schilder werden durch eine Zeile getrennt, die nur `{SEPARATOR}` enthält. Leerzeilen um "
        "den Trenner sind egal. Ein Zeilenumbruch *innerhalb* eines Schilds bleibt als Umbruch "
        "erhalten; sonst bricht Blattwerk nur zwischen Wörtern um – Wörter werden nie getrennt. "
        "Der Text wird nicht als Markdown gelesen: `**`, `#` usw. erscheinen wörtlich.",
        "## 3. Optionen im Frontmatter\n\n" + _options_table() + "\n\n"
        "Ungültige Werte gelten als Standardwert und werden gemeldet (`SBW003`).",
        "## 4. Wie die Schriftgröße bestimmt wird\n\n"
        "Blattwerk probiert für jedes Schild aus, wie groß der Text werden kann, ohne über den Rand "
        "zu laufen. Begrenzt wird das meist vom längsten einzelnen Wort (es muss in eine Zeile "
        "passen) oder bei langen Texten von der Seitenhöhe. Vorschau und PDF sind dabei identisch.",
        "## 5. Warnungen\n\n"
        "- `SBW001`: Das Dokument enthält kein Schild.\n"
        f"- `SBW002`: Leeres Schild – meist ein doppeltes oder abschließendes `{SEPARATOR}`.\n"
        "- `SBW003`: Ungültige Option im Frontmatter.",
    ]
    return _AUTOGEN_HEADER + "\n\n" + "\n\n".join(sections) + "\n"
