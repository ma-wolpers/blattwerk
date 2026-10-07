"""Rendert die Klausur-Anleitung (`docs/nutzer/ANLEITUNG_KLAUSUR.md`).

Klausuren (`.kbw`) nutzen den Blockdialekt der Arbeitsblätter; diese Anleitung
beschreibt nur die Klausur-spezifischen Teile. Fakten kommen aus dem Template
(`document_type_templates`) und der redaktionellen Prosa
(`authoring_guide_prose.PROSE_SECTIONS`) -- dieselben Texte, die auch die
Completion und die Arbeitsblatt-Anleitung nutzen.
"""

from __future__ import annotations

from app.core.document_type_registry import DOCUMENT_TYPE_EXAM
from app.core.document_type_templates import build_new_document_content
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
        "## 3. Anforderungsbereiche (`afb`)\n\n" + _prose("option:afb"),
        "## 4. Hilfsmittelfreier Teil (`--hm`)\n\n" + _prose("marker:aidsplit"),
        "## 5. Bewertungstabelle\n\n" + _prose("block:evaluation") + "\n\n"
        "- `level`: " + _prose("block:evaluation.level") + "\n"
        "- `parts`: " + _prose("block:evaluation.parts") + "\n"
        "- `grade`: " + _prose("block:evaluation.grade"),
        "## 6. Operatorentabelle\n\n" + _prose("block:operators") + "\n\n"
        "- `scope`: " + _prose("block:operators.scope"),
        "## 7. Klausur-Übersicht\n\n" + _prose("exam:overview"),
        "## 8. Erwartungshorizont\n\n" + _prose("exam:expectation_horizon"),
    ]
    return _AUTOGEN_HEADER + "\n\n" + "\n\n".join(sections) + "\n"
