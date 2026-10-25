"""Rendert die Klausur-Anleitung (`docs/nutzer/ANLEITUNG_KLAUSUR.md`).

Klausuren (`.kbw`) nutzen den Blockdialekt der Arbeitsblätter; diese Anleitung
beschreibt nur die Klausur-spezifischen Teile. Fakten kommen aus dem Template
(`document_type_templates`), dem Erwartungstyp-Katalog (`expectation_kinds`)
und der redaktionellen Prosa (`authoring_guide_prose.PROSE_SECTIONS`) --
dieselben Texte, die auch die Completion, der Erwartungshorizont und die
Arbeitsblatt-Anleitung nutzen.
"""

from __future__ import annotations

from app.core.document_type_registry import DOCUMENT_TYPE_EXAM
from app.core.document_type_templates import build_new_document_content
from app.core.expectation_kinds import EXPECTATION_KINDS
from app.core.markdown_conventions import MarkdownConventionCatalog

from authoring_guide_render_shared import _AUTOGEN_HEADER, _fenced, _prose


def render_exam_guide(catalog: MarkdownConventionCatalog) -> str:
    """Rendert die Klausur-Anleitung, deterministisch."""
    del catalog  # Katalogfakten stehen in der Arbeitsblatt-Anleitung; hier nur die Klausur-Zusätze.
    example = build_new_document_content(DOCUMENT_TYPE_EXAM, {})
    sections = [
        "# Klausur erstellen\n\n" + _prose("exam:intro"),
        "## 1. Schnellstart\n\n" + _fenced(example),
        "## 2. Punkte und Teilpunkte\n\n" + _prose("option:points") + "\n\n" + _prose("block:solution"),
        "## 3. Erwartungstypen\n\n" + _prose("exam:expectation_kinds") + "\n\n" + _expectation_kinds_table(),
        "## 4. Anforderungsbereiche (`afb`)\n\n" + _prose("option:afb"),
        "## 5. Hilfsmittelfreier Teil (`--hm`)\n\n" + _prose("marker:aidsplit"),
        "## 6. Wahlteile (`--w`)\n\n" + _prose("marker:choicesplit"),
        "## 7. Bewertungstabelle\n\n" + _prose("block:evaluation") + "\n\n"
        "- `level`: " + _prose("block:evaluation.level") + "\n"
        "- `parts`: " + _prose("block:evaluation.parts") + "\n"
        "- `grade`: " + _prose("block:evaluation.grade"),
        "## 8. Operatorentabelle\n\n" + _prose("block:operators") + "\n\n"
        "- `scope`: " + _prose("block:operators.scope"),
        "## 9. Klausur-Übersicht\n\n" + _prose("exam:overview"),
        "## 10. Erwartungshorizont\n\n" + _prose("exam:expectation_horizon"),
    ]
    return _AUTOGEN_HEADER + "\n\n" + "\n\n".join(sections) + "\n"


def _expectation_kinds_table() -> str:
    """Markdown-Tabelle aller Erwartungstypen in Katalog- bzw. Legendenreihenfolge.

    Die Spalte „Bedeutung“ ist `ExpectationKind.description` -- derselbe Satz,
    den die Legende im Erwartungshorizont (`exam_expectation_horizon._kinds_legend`)
    und das Detailfeld der Editor-Completion zeigen. Weitere erlaubte
    Schreibweisen (Aliasse) stehen als „auch: …“ hinter dem Namen, damit die
    Tabelle alle Tokens nennt, die `resolve_expectation_kind` akzeptiert.
    """
    rows = ["| Symbol | Typ | Kürzel | Bedeutung |", "| --- | --- | --- | --- |"]
    for kind in EXPECTATION_KINDS:
        name = kind.label + (f" (auch: {', '.join(kind.aliases)})" if kind.aliases else "")
        rows.append(f"| {kind.symbol} | {name} | `{kind.abbreviation}` | {kind.description} |")
    return "\n".join(rows)
