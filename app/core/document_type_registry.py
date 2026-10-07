"""Dokumenttyp-Registry: reine Daten- und Capability-Beschreibung je Dokumenttyp.

Die Dateiendung ist die einzige Typidentität einer gespeicherten Datei
(Invariante I1, siehe `document_semantics.py`). Diese Registry beschreibt nur,
*was* ein Typ kann -- sie enthält bewusst keine Builder, keine Renderer und
keine UI-Importe (keine Importzyklen, kein God Object). Templates liegen in
`document_type_templates.py`, Renderer fragen hier nur Capabilities ab.

Typbedingtes Verhalten, das früher am Frontmatter-Feld `mode` hing
(`presentation`, `test`), steht ausschließlich hier als benannte Capability:

* `slide_layout` -- Folien-Layout (früher `mode: presentation`).
* `solutions_renderable` -- ob eine Lösungsfassung erzeugt werden kann
  (Präsentationen nie).
* `work_hints` -- ob Sozialform-Icons gerendert werden (früher fehlten sie
  bei `mode: test`; jetzt nur bei Klausuren).

`export_formats` beschreibt nur, welche Formate ein Typ unterstützt, in
UI-Reihenfolge. Das ist ausdrücklich **keine** Export-Format-Registry: die
Format-Implementierungen bleiben in den Exportdialogen.
"""

from __future__ import annotations

from dataclasses import dataclass

DOCUMENT_TYPE_WORKSHEET = "worksheet"
DOCUMENT_TYPE_PRESENTATION = "presentation"
DOCUMENT_TYPE_EXAM = "exam"
DOCUMENT_TYPE_KURZENTWURF = "kurzentwurf"
DOCUMENT_TYPE_SCHILD = "schild"
DOCUMENT_TYPE_MARKDOWN = "markdown"

PIPELINE_WORKSHEET = "worksheet"
PIPELINE_KURZENTWURF = "kurzentwurf"
PIPELINE_SCHILD = "schild"
PIPELINE_MARKDOWN = "markdown"


@dataclass(frozen=True)
class DocumentTypeSpec:
    """Daten und Capabilities eines Dokumenttyps.

    Attributes:
        id: Kanonischer Typname (auch kanonischer `document_type`-Wert).
        extension: Dateiendung inkl. Punkt, kleingeschrieben.
        label: Anzeigename in der UI.
        pipeline: Welche Render-/Validierungs-Pipeline zuständig ist.
        export_formats: Unterstützte Exportformate in UI-Reihenfolge.
        default_filename: Vorschlag im Neu-Dialog.
        new_document_title: Titel im Template eines neuen Dokuments.
        new_dialog_title: Titel des Speichern-Dialogs beim Neu-Anlegen.
        blocks: Ob `:::`-Blöcke und Kontrollmarker Blattwerk-Semantik haben.
        solutions_renderable: Ob eine Lösungsfassung erzeugt werden kann.
        slide_layout: Ob das Folien-Layout gilt.
        work_hints: Ob Sozialform-Icons gerendert werden.
        aid_split: Ob der Hilfsmittel-Trenner `--hm` wirkt.
        evaluation: Ob `:::evaluation` verfügbar ist.
        marker_required: Ob der Konsistenzmarker `document_type` Pflicht ist.
        expectation_horizon: Ob ein Erwartungshorizont exportiert werden kann.
        empty_answer_hint: Ob leere Antwortblöcke als Best-Practice-Hinweis
            (AN005) gemeldet werden. In Klausuren nicht: Antwortfelder sind dort
            absichtlich leer, die Lösung steht in `:::solution`.
        operator_legend: Ob `:::operators:::` eine Operatorentabelle rendert
            und fehlende Tabellen gemeldet werden (OPR004–OPR008). Sonst
            rendert der Block nichts und es gibt OPR007.
    """

    id: str
    extension: str
    label: str
    pipeline: str
    export_formats: tuple[str, ...]
    default_filename: str
    new_document_title: str
    new_dialog_title: str
    blocks: bool
    solutions_renderable: bool
    slide_layout: bool
    work_hints: bool
    aid_split: bool
    evaluation: bool
    marker_required: bool
    expectation_horizon: bool = False
    empty_answer_hint: bool = True
    operator_legend: bool = False


DOCUMENT_TYPE_SPECS: tuple[DocumentTypeSpec, ...] = (
    DocumentTypeSpec(
        id=DOCUMENT_TYPE_WORKSHEET,
        extension=".abw",
        label="Arbeitsblatt",
        pipeline=PIPELINE_WORKSHEET,
        export_formats=("pdf", "html", "png", "pngzip"),
        default_filename="arbeitsblatt.abw",
        new_document_title="Neues Arbeitsblatt",
        new_dialog_title="Neues Aufgabenblatt anlegen",
        blocks=True,
        solutions_renderable=True,
        slide_layout=False,
        work_hints=True,
        aid_split=False,
        evaluation=True,
        marker_required=True,
        operator_legend=True,
    ),
    DocumentTypeSpec(
        id=DOCUMENT_TYPE_PRESENTATION,
        extension=".pbw",
        label="Präsentation",
        pipeline=PIPELINE_WORKSHEET,
        export_formats=("pdf", "html", "png", "pngzip", "pptx"),
        default_filename="praesentation.pbw",
        new_document_title="Neue Praesentation",
        new_dialog_title="Neue Praesentation anlegen",
        blocks=True,
        solutions_renderable=False,
        slide_layout=True,
        work_hints=True,
        aid_split=False,
        evaluation=False,
        marker_required=True,
    ),
    DocumentTypeSpec(
        id=DOCUMENT_TYPE_EXAM,
        extension=".kbw",
        label="Klausur",
        pipeline=PIPELINE_WORKSHEET,
        export_formats=("pdf", "html", "png", "pngzip"),
        default_filename="klausur.kbw",
        new_document_title="Neue Klausur",
        new_dialog_title="Neue Klausur anlegen",
        blocks=True,
        solutions_renderable=True,
        slide_layout=False,
        work_hints=False,
        aid_split=True,
        evaluation=True,
        marker_required=True,
        expectation_horizon=True,
        empty_answer_hint=False,
        operator_legend=True,
    ),
    DocumentTypeSpec(
        id=DOCUMENT_TYPE_KURZENTWURF,
        extension=".ebw",
        label="Kurzentwurf",
        pipeline=PIPELINE_KURZENTWURF,
        export_formats=("pdf", "html", "png", "pngzip"),
        default_filename="kurzentwurf.ebw",
        new_document_title="Neuer Kurzentwurf",
        new_dialog_title="Neuen Kurzentwurf anlegen",
        blocks=False,
        solutions_renderable=False,
        slide_layout=False,
        work_hints=True,
        aid_split=False,
        evaluation=False,
        marker_required=True,
    ),
    DocumentTypeSpec(
        id=DOCUMENT_TYPE_SCHILD,
        extension=".sbw",
        label="Schilder",
        pipeline=PIPELINE_SCHILD,
        export_formats=("pdf", "html", "png", "pngzip"),
        default_filename="schilder.sbw",
        new_document_title="Neue Schilder",
        new_dialog_title="Neue Schilder anlegen",
        blocks=False,
        solutions_renderable=False,
        slide_layout=False,
        work_hints=False,
        aid_split=False,
        evaluation=False,
        marker_required=True,
    ),
    DocumentTypeSpec(
        id=DOCUMENT_TYPE_MARKDOWN,
        extension=".md",
        label="Markdown",
        pipeline=PIPELINE_MARKDOWN,
        export_formats=("pdf", "html", "png", "pngzip"),
        default_filename="dokument.md",
        new_document_title="Neues Dokument",
        new_dialog_title="Neues Markdown-Dokument anlegen",
        blocks=False,
        solutions_renderable=False,
        slide_layout=False,
        work_hints=True,
        aid_split=False,
        evaluation=False,
        marker_required=False,
    ),
)

_SPECS_BY_ID = {spec.id: spec for spec in DOCUMENT_TYPE_SPECS}
_SPECS_BY_EXTENSION = {spec.extension: spec for spec in DOCUMENT_TYPE_SPECS}

KNOWN_DOCUMENT_TYPES: tuple[str, ...] = tuple(spec.id for spec in DOCUMENT_TYPE_SPECS)
BLATTWERK_DOCUMENT_TYPES: tuple[str, ...] = tuple(
    spec.id for spec in DOCUMENT_TYPE_SPECS if spec.marker_required
)
"""Die fünf Blattwerk-Typen (alle außer schlichtem Markdown), in UI-Reihenfolge."""
BLATTWERK_EXTENSIONS: tuple[str, ...] = tuple(
    spec.extension for spec in DOCUMENT_TYPE_SPECS if spec.marker_required
)


def spec_for_type(document_type: str) -> DocumentTypeSpec:
    """Liefert die Spec eines kanonischen Typnamens.

    Raises:
        KeyError: bei unbekanntem Typ -- Aufrufer müssen kanonische Typen
            aus `document_semantics` übergeben, nie Rohwerte.
    """
    return _SPECS_BY_ID[document_type]


def spec_for_extension(extension: str) -> DocumentTypeSpec | None:
    """Liefert die Spec zu einer Dateiendung (ohne Rücksicht auf Groß/Klein) oder ``None``."""
    return _SPECS_BY_EXTENSION.get(str(extension or "").lower())


def has_slide_layout(document_type: str) -> bool:
    """Ob für den Typ das Folien-Layout gilt (unbekannte Typen: nein)."""
    spec = _SPECS_BY_ID.get(document_type)
    return bool(spec and spec.slide_layout)


def shows_work_hints(document_type: str) -> bool:
    """Ob Sozialform-Icons gerendert werden (unbekannte Typen: ja, wie Arbeitsblatt)."""
    spec = _SPECS_BY_ID.get(document_type)
    return True if spec is None else spec.work_hints


def shows_empty_answer_hint(document_type: str | None) -> bool:
    """Ob leere Antwortblöcke gemeldet werden (AN005; unbekannte Typen: ja, wie Arbeitsblatt)."""
    spec = _SPECS_BY_ID.get(document_type)
    return True if spec is None else spec.empty_answer_hint


def shows_operator_legend(document_type: str | None) -> bool:
    """Ob `:::operators:::` eine Operatorentabelle rendert (unbekannte Typen: nein)."""
    spec = _SPECS_BY_ID.get(document_type)
    return bool(spec and spec.operator_legend)


def solutions_renderable(document_type: str) -> bool:
    """Ob eine Lösungsfassung erzeugt werden kann (unbekannte Typen: ja)."""
    spec = _SPECS_BY_ID.get(document_type)
    return True if spec is None else spec.solutions_renderable
