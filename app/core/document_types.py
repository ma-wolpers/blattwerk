"""Document type helpers for Blattwerk and integrated Kurzentwurf flows."""

from __future__ import annotations

from typing import Mapping

from .blatt_kern_shared import normalize_document_mode

DOCUMENT_TYPE_WORKSHEET = "worksheet"
DOCUMENT_TYPE_PRESENTATION = "presentation"
DOCUMENT_TYPE_KURZENTWURF = "kurzentwurf"

KNOWN_DOCUMENT_TYPES = {
    DOCUMENT_TYPE_WORKSHEET,
    DOCUMENT_TYPE_PRESENTATION,
    DOCUMENT_TYPE_KURZENTWURF,
}

DOCUMENT_TYPE_DETECTION_YAML_KEYS = "yaml_keys"
DOCUMENT_TYPE_DETECTION_HYBRID = "hybrid"
DOCUMENT_TYPE_DETECTION_EXPLICIT_KEY = "document_type_key"

KNOWN_DOCUMENT_TYPE_DETECTION_MODES = {
    DOCUMENT_TYPE_DETECTION_YAML_KEYS,
    DOCUMENT_TYPE_DETECTION_HYBRID,
    DOCUMENT_TYPE_DETECTION_EXPLICIT_KEY,
}

_KURZENTWURF_META_KEYS = ("Stundenthema", "Lerngruppe", "start")
_KURZENTWURF_TITLE = "Neuer Kurzentwurf"


def normalize_document_type(value: object, default: str = DOCUMENT_TYPE_WORKSHEET) -> str:
    candidate = str(value or "").strip().lower()
    if candidate in KNOWN_DOCUMENT_TYPES:
        return candidate
    if candidate == "lesson_plan":
        return DOCUMENT_TYPE_KURZENTWURF
    if candidate == "slide_deck":
        return DOCUMENT_TYPE_PRESENTATION
    if candidate == "arbeitsblatt":
        return DOCUMENT_TYPE_WORKSHEET
    return default


def normalize_document_type_detection_mode(
    value: object,
    default: str = DOCUMENT_TYPE_DETECTION_YAML_KEYS,
) -> str:
    candidate = str(value or "").strip().lower()
    if candidate in KNOWN_DOCUMENT_TYPE_DETECTION_MODES:
        return candidate
    return default


def detect_document_type_from_meta(
    meta: Mapping[str, object] | None,
    *,
    detection_mode: str = DOCUMENT_TYPE_DETECTION_YAML_KEYS,
) -> str:
    metadata = meta if isinstance(meta, Mapping) else {}
    normalized_detection_mode = normalize_document_type_detection_mode(detection_mode)
    explicit_document_type = normalize_document_type(metadata.get("document_type"), default="")
    normalized_mode = normalize_document_mode(metadata.get("mode"), default=DOCUMENT_TYPE_WORKSHEET)

    if normalized_detection_mode in {
        DOCUMENT_TYPE_DETECTION_HYBRID,
        DOCUMENT_TYPE_DETECTION_EXPLICIT_KEY,
    } and explicit_document_type:
        return explicit_document_type

    if normalized_mode == DOCUMENT_TYPE_PRESENTATION:
        return DOCUMENT_TYPE_PRESENTATION

    if normalized_detection_mode == DOCUMENT_TYPE_DETECTION_EXPLICIT_KEY:
        return DOCUMENT_TYPE_WORKSHEET

    if _looks_like_kurzentwurf_meta(metadata):
        return DOCUMENT_TYPE_KURZENTWURF

    return DOCUMENT_TYPE_WORKSHEET


def get_new_document_title(document_type: str, preferences: Mapping[str, object] | None = None) -> str:
    document_type = normalize_document_type(document_type)
    user_preferences = preferences if isinstance(preferences, Mapping) else {}
    title_prefix = str(user_preferences.get("new_doc_title_prefix", "") or "").strip()

    if document_type == DOCUMENT_TYPE_PRESENTATION:
        base_title = "Neue Praesentation"
    elif document_type == DOCUMENT_TYPE_KURZENTWURF:
        base_title = _KURZENTWURF_TITLE
    else:
        base_title = "Neues Arbeitsblatt"

    if title_prefix:
        return f"{title_prefix} {base_title}".strip()
    return base_title


def build_new_document_content(document_type: str, preferences: Mapping[str, object] | None = None) -> str:
    user_preferences = preferences if isinstance(preferences, Mapping) else {}
    normalized_document_type = normalize_document_type(document_type)

    if normalized_document_type == DOCUMENT_TYPE_PRESENTATION:
        return _build_presentation_template(user_preferences)
    if normalized_document_type == DOCUMENT_TYPE_KURZENTWURF:
        return _build_kurzentwurf_template(user_preferences)
    return _build_worksheet_template(user_preferences)


def get_new_document_dialog_defaults(document_type: str) -> tuple[str, str]:
    normalized_document_type = normalize_document_type(document_type)
    if normalized_document_type == DOCUMENT_TYPE_PRESENTATION:
        return ("Neue Praesentation anlegen", "praesentation.md")
    if normalized_document_type == DOCUMENT_TYPE_KURZENTWURF:
        return ("Neuen Kurzentwurf anlegen", "kurzentwurf.md")
    return ("Neues Aufgabenblatt anlegen", "arbeitsblatt.md")


def _looks_like_kurzentwurf_meta(meta: Mapping[str, object]) -> bool:
    return sum(1 for key in _KURZENTWURF_META_KEYS if str(meta.get(key, "") or "").strip()) >= 2


def _build_worksheet_template(preferences: Mapping[str, object]) -> str:
    default_subject = str(preferences.get("default_subject", "") or "").strip() or "Fach eintragen"
    author = str(preferences.get("default_document_author", "") or "").strip()
    school = str(preferences.get("default_school_name", "") or "").strip()
    language_variant = str(preferences.get("language_variant", "") or "").strip()
    date_format = str(preferences.get("date_format", "") or "").strip()
    worksheet_label = str(preferences.get("worksheet_label", "") or "").strip()
    default_grade = str(preferences.get("default_grade_level", "") or "").strip()
    work_emoji_visible = bool(preferences.get("default_work_emoji_visible", True))

    metadata_lines = [
        "---",
        f"document_type: {DOCUMENT_TYPE_WORKSHEET}",
        f"Titel: {get_new_document_title(DOCUMENT_TYPE_WORKSHEET, preferences)}",
        f"Fach: {default_subject}",
        "Thema: Thema eintragen",
    ]
    if author:
        metadata_lines.append(f"Autor: {author}")
    if school:
        metadata_lines.append(f"Schule: {school}")
    if default_grade:
        metadata_lines.append(f"Klassenstufe: {default_grade}")
    if language_variant:
        metadata_lines.append(f"Sprache: {language_variant}")
    if date_format:
        metadata_lines.append(f"Datumsformat: {date_format}")
    if worksheet_label:
        metadata_lines.append(f"LabelAufgaben: {worksheet_label}")
    if not work_emoji_visible:
        metadata_lines.append("mode: test")
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
    default_subject = str(preferences.get("default_subject", "") or "").strip() or "Fach eintragen"
    author = str(preferences.get("default_document_author", "") or "").strip()
    school = str(preferences.get("default_school_name", "") or "").strip()
    default_grade = str(preferences.get("default_grade_level", "") or "").strip()

    metadata_lines = [
        "---",
        f"document_type: {DOCUMENT_TYPE_PRESENTATION}",
        "mode: presentation",
        "presentation_layout: presentation_16_9",
        f"Titel: {get_new_document_title(DOCUMENT_TYPE_PRESENTATION, preferences)}",
        f"Fach: {default_subject}",
        "Thema: Thema eintragen",
    ]
    if author:
        metadata_lines.append(f"Autor: {author}")
    if school:
        metadata_lines.append(f"Schule: {school}")
    if default_grade:
        metadata_lines.append(f"Klassenstufe: {default_grade}")
    metadata_lines.append("---")

    return (
        "\n".join(metadata_lines)
        + "\n\n"
        + "--# Einstieg\n"
        + ":::task title=\"Einstieg\"\n"
        + "Starte hier mit der ersten Folie.\n"
        + ":::\n\n"
        + "-+\n"
        + ":::task title=\"Weiterfuehrung\"\n"
        + "Fuehre hier den naechsten Gedanken aus.\n"
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
        + "S> Aktivierung von Vorwissen und Zieltransparenz.\n"
        + "A>\n"
        + "s< Erste Vermutungen formulieren.\n"
        + "U> Plenum; Tafel\n"
        + "ant< Typische Fehlannahme notieren.\n\n"
        + "---\n"
        + "A>\n"
        + "s< Schwerpunkt der Lernaktivitaet festhalten.\n\n"
        + "#erarbeitung t=20\n"
        + "S> Leitfrage in Teams bearbeiten.\n"
        + "A>\n"
        + "s< Arbeitsphase mit Materialanalyse und Zwischenfeedback.\n"
        + "U> Teamarbeit; Materialset A\n"
    )