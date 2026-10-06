"""Inhalte neuer Dokumente je Dokumenttyp (getrennt von der reinen Daten-Registry).

Jedes Blattwerk-Template schreibt den kanonischen Konsistenzmarker
`document_type` (Invariante I2) -- schlichtes Markdown bekommt keinen. Ein
Frontmatter-Feld `mode` gibt es nicht mehr (I3): ob z. B. Sozialform-Icons
erscheinen oder das Folien-Layout gilt, folgt allein aus dem Typ.
"""

from __future__ import annotations

from typing import Callable, Mapping

from .document_type_registry import (
    DOCUMENT_TYPE_EXAM,
    DOCUMENT_TYPE_KURZENTWURF,
    DOCUMENT_TYPE_MARKDOWN,
    DOCUMENT_TYPE_PRESENTATION,
    DOCUMENT_TYPE_WORKSHEET,
    spec_for_type,
)


def get_new_document_title(document_type: str, preferences: Mapping[str, object] | None = None) -> str:
    """Titel eines neuen Dokuments, optional mit dem Präfix aus den Einstellungen."""
    user_preferences = preferences if isinstance(preferences, Mapping) else {}
    title_prefix = str(user_preferences.get("new_doc_title_prefix", "") or "").strip()
    base_title = spec_for_type(document_type).new_document_title
    if title_prefix:
        return f"{title_prefix} {base_title}".strip()
    return base_title


def build_new_document_content(document_type: str, preferences: Mapping[str, object] | None = None) -> str:
    """Startinhalt eines neuen Dokuments des gegebenen (kanonischen) Typs."""
    user_preferences = preferences if isinstance(preferences, Mapping) else {}
    return TEMPLATE_BUILDERS[spec_for_type(document_type).id](user_preferences)


def get_new_document_dialog_defaults(document_type: str) -> tuple[str, str]:
    """Titel des Speichern-Dialogs und vorgeschlagener Dateiname (mit Typ-Endung)."""
    spec = spec_for_type(document_type)
    return spec.new_dialog_title, spec.default_filename


def _common_metadata_lines(document_type: str, preferences: Mapping[str, object]) -> list[str]:
    """Gemeinsamer Frontmatter-Kopf der Arbeitsblatt-Pipeline-Typen."""
    default_subject = str(preferences.get("default_subject", "") or "").strip() or "Fach eintragen"
    lines = [
        "---",
        f"document_type: {document_type}",
        f"Titel: {get_new_document_title(document_type, preferences)}",
        f"Fach: {default_subject}",
        "Thema: Thema eintragen",
    ]
    for pref_key, meta_key in (
        ("default_document_author", "Autor"),
        ("default_school_name", "Schule"),
        ("default_grade_level", "Klassenstufe"),
    ):
        value = str(preferences.get(pref_key, "") or "").strip()
        if value:
            lines.append(f"{meta_key}: {value}")
    return lines


def _build_worksheet_template(preferences: Mapping[str, object]) -> str:
    metadata_lines = _common_metadata_lines(DOCUMENT_TYPE_WORKSHEET, preferences)
    for pref_key, meta_key in (
        ("language_variant", "Sprache"),
        ("date_format", "Datumsformat"),
        ("worksheet_label", "LabelAufgaben"),
    ):
        value = str(preferences.get(pref_key, "") or "").strip()
        if value:
            metadata_lines.append(f"{meta_key}: {value}")
    metadata_lines.append("---")
    return (
        "\n".join(metadata_lines)
        + "\n\n"
        + ":::material title=\"Hinweis\"\n"
        + "Arbeite sauber und lies jede Aufgabe genau.\n"
        + ":::\n\n"
        + ":::task points=2 work=single action=read\n"
        + "Formuliere hier deine erste Aufgabe.\n"
        + ":::\n"
    )


def _build_presentation_template(preferences: Mapping[str, object]) -> str:
    metadata_lines = _common_metadata_lines(DOCUMENT_TYPE_PRESENTATION, preferences)
    metadata_lines.insert(2, "presentation_layout: presentation_16_9")
    metadata_lines.append("---")
    return (
        "\n".join(metadata_lines)
        + "\n\n"
        + "--# Einstieg\n"
        + ":::task title=\"Einstieg\"\n"
        + "Starte hier mit der ersten Folie.\n"
        + ":::\n\n"
        + "--!\n"
        + ":::task title=\"Weiterfuehrung\"\n"
        + "Fuehre hier den naechsten Gedanken aus.\n"
        + ":::\n"
    )


def _build_exam_template(preferences: Mapping[str, object]) -> str:
    metadata_lines = _common_metadata_lines(DOCUMENT_TYPE_EXAM, preferences)
    metadata_lines.extend(["Datum: Datum eintragen", "Dauer: 90 Minuten", "Hilfsmittel: Hilfsmittel eintragen"])
    metadata_lines.append("---")
    return (
        "\n".join(metadata_lines)
        + "\n\n"
        + ":::task points=4 afb=1\n"
        + "Formuliere hier die erste Aufgabe.\n"
        + ":::\n\n"
        + ":::solution\n"
        + "1. Erwarteter Lösungsschritt (2P)\n"
        + "2. Zweiter Lösungsschritt (2P)\n"
        + ":::\n"
    )


def _build_kurzentwurf_template(preferences: Mapping[str, object]) -> str:
    default_grade = str(preferences.get("default_grade_level", "") or "").strip()
    default_subject = str(preferences.get("default_subject", "") or "").strip()

    learner_group = default_grade or "Klasse eintragen"
    if default_subject:
        learner_group = f"{default_subject} {learner_group}".strip()

    metadata_lines = [
        "---",
        f"document_type: {DOCUMENT_TYPE_KURZENTWURF}",
        f"Stundenthema: {get_new_document_title(DOCUMENT_TYPE_KURZENTWURF, preferences)}",
        f"Lerngruppe: {learner_group}",
        "start: 08:00",
        "Material:",
        "    - Material eintragen",
        "---",
    ]

    return (
        "\n".join(metadata_lines)
        + "\n\n"
        + "#einstieg t=10\n"
        + "S> Leitfrage präsentieren\n"
        + "A>\n"
        + "s< formulieren erste Vermutungen zur Leitfrage.\n"
        + 'ant< - "Ich vermute, dass ..."\n'
        + '      - "Das liegt bestimmt an ..."\n'
        + "U> LSG; Tafel\n\n"
        + "#erarbeitung t=20\n"
        + "S> Arbeitsauftrag erteilen\n"
        + "A>\n"
        + "s< bearbeiten die Leitfrage mithilfe des Materials.\n"
        + 'ant< "Im Material steht, dass ..."\n'
        + "U> GA; Arbeitsblatt eintragen\n\n"
        + "---\n"
        + "S> Zwischenergebnisse vergleichen lassen\n"
        + "A>\n"
        + "s< vergleichen ihre Ergebnisse mit einer Nachbargruppe.\n"
        + 'ant< "Wir haben das anders gelöst, weil ..."\n'
    )


def _build_markdown_template(preferences: Mapping[str, object]) -> str:
    return f"# {get_new_document_title(DOCUMENT_TYPE_MARKDOWN, preferences)}\n\nText eintragen.\n"


TEMPLATE_BUILDERS: dict[str, Callable[[Mapping[str, object]], str]] = {
    DOCUMENT_TYPE_WORKSHEET: _build_worksheet_template,
    DOCUMENT_TYPE_PRESENTATION: _build_presentation_template,
    DOCUMENT_TYPE_EXAM: _build_exam_template,
    DOCUMENT_TYPE_KURZENTWURF: _build_kurzentwurf_template,
    DOCUMENT_TYPE_MARKDOWN: _build_markdown_template,
}
