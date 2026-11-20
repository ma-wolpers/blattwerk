"""Sprache eines Dokuments: optionales Frontmatter-Feld `Sprache`, sonst Programm-Standard.

Einzige Stelle, die entscheidet, in welcher Sprache Blattwerk seine *eigenen* Texte
(Kopfzeile, "Aufgabe N", Punkte, Seitenzahlen, Lösungs-Badge …) in ein Dokument
schreibt. Die Texte selbst stehen als Daten in `document_labels_data.LABELS`.

Auflösung (Muster wie `document_font.resolve_document_font_profile`):

* gültiger Dokumentwert (z. B. ``pt-BR``, Groß-/Kleinschreibung egal) -> diese Sprache,
* kein Wert -> `DEFAULT_LANGUAGE` (Deutsch, bisheriges Verhalten),
* unbekannter Wert -> Standard plus Problemtext; der Validator meldet ihn als
  Warnung `FM013`, der Build läuft weiter.

Weitergabe an die Block-Renderer: `render_html` löst die Sprache einmal auf und gibt
sie sichtbar weiter; tief in der Block-Kette kommt sie wie Druckbreite und Cache als
Laufzeitoption `_language` an (`blatt_kern_layout_columns._with_runtime_layout_options`)
und wird mit `language_from_options` gelesen. Fehlt sie dort (z. B. Validator,
Erwartungshorizont), gilt der Standard -- lehrkraftseitige Ausgaben bleiben deutsch.
"""

from __future__ import annotations

from html import escape

from .document_labels_data import DEFAULT_LANGUAGE, LABELS, LANGUAGES, PLURAL_ONE_BELOW

LANGUAGE_KEY = "Sprache"
"""Frontmatter-Schlüssel (deutsch wie `Titel`, `Fach`, `Stufe`)."""

LANGUAGE_OPTION_KEY = "_language"
"""Laufzeitoption, mit der die aufgelöste Sprache die Block-Renderer erreicht."""


def document_language_value(meta) -> str | None:
    """Rohwert von `Sprache` aus dem Frontmatter, getrimmt und klein; ``None`` wenn leer.

    Example:
        >>> document_language_value({"Sprache": " pt-BR "})
        'pt-br'
        >>> document_language_value({}) is None
        True
    """
    raw = (meta or {}).get(LANGUAGE_KEY)
    if raw is None:
        return None
    text = str(raw).strip().lower()
    return text or None


def resolve_document_language(meta) -> tuple[str, str | None]:
    """Liefert ``(sprache, problem)`` für ein Dokument.

    Args:
        meta: Frontmatter-Dict des Dokuments (oder ``None``).

    Returns:
        Den Sprachschlüssel aus `LANGUAGES` und ``None`` oder einen Problemtext für
        einen unbekannten Dokumentwert (dann gilt der Programm-Standard).

    Example:
        >>> resolve_document_language({"Sprache": "pt-BR"})
        ('pt-br', None)
        >>> resolve_document_language({})
        ('de', None)
        >>> resolve_document_language({"Sprache": "klingonisch"})[0]
        'de'
    """
    value = document_language_value(meta)
    if value is None:
        return DEFAULT_LANGUAGE, None
    if value in LANGUAGES:
        return value, None
    problem = (
        f"Unbekannte Sprache `{LANGUAGE_KEY}: {value}`; es gilt der Programm-Standard "
        f"`{DEFAULT_LANGUAGE}`. Erlaubt: {', '.join(LANGUAGES)}."
    )
    return DEFAULT_LANGUAGE, problem


def normalize_language(language) -> str:
    """Bekannter Sprachschlüssel oder der Standard (robust gegen ``None``/Altwerte).

    Example:
        >>> normalize_language("PT-BR"), normalize_language(None), normalize_language("xx")
        ('pt-br', 'de', 'de')
    """
    text = str(language or "").strip().lower()
    return text if text in LANGUAGES else DEFAULT_LANGUAGE


def language_from_options(options) -> str:
    """Sprache aus den Laufzeitoptionen eines Blocks (`_language`), sonst der Standard."""
    return normalize_language((options or {}).get(LANGUAGE_OPTION_KEY))


def html_lang(language) -> str:
    """Wert für ``<html lang>`` (steuert u. a. die Silbentrennung).

    Example:
        >>> html_lang("pt-br")
        'pt-BR'
    """
    return LANGUAGES[normalize_language(language)]["html_lang"]


def format_date(value, language) -> str:
    """Datum im Format der Dokumentsprache (`LANGUAGES[...]["date_format"]`).

    Example:
        >>> from datetime import date
        >>> format_date(date(2026, 9, 25), "de"), format_date(date(2026, 9, 25), "pt-br")
        ('25.09.2026', '25/09/2026')
    """
    return value.strftime(LANGUAGES[normalize_language(language)]["date_format"])


def _template(key: str, language: str, count) -> str:
    """Vorlage für ``key`` in ``language``; Pluraltupel werden über ``count`` aufgelöst.

    Fehlt eine Sprache bei einem Label (vom Guardrail-Test verhindert), fällt die
    Vorlage auf den Standard zurück, statt den Build abzubrechen.
    """
    language = normalize_language(language)
    entry = LABELS[key]
    template = entry.get(language, entry[DEFAULT_LANGUAGE])
    if isinstance(template, tuple):
        one, other = template
        limit = PLURAL_ONE_BELOW.get(language)
        if limit is None or count is None:
            return one
        return one if abs(float(count)) < limit else other
    return template


def label(key: str, language, count=None, **values) -> str:
    """Klartext-Label in der Dokumentsprache, Platzhalter mit ``values`` gefüllt.

    Args:
        key: Schlüssel in `document_labels_data.LABELS` (unbekannt -> ``KeyError``,
            ein Programmierfehler, kein Benutzerfehler).
        language: Sprachschlüssel; unbekannt/``None`` -> Programm-Standard.
        count: Zahl für Pluralvorlagen (``None`` -> erste Form).
        **values: Werte der ``{name}``-Platzhalter (werden nicht escaped).

    Example:
        >>> label("task_numbered", "pt-br", number=3)
        'Questão 3'
        >>> label("points", "pt-br", count=2, points="2"), label("points", "de", points="2")
        ('2 pts', '2 P')
    """
    return _template(key, language, count).format(**values)


def label_html(key: str, language, count=None, **html_values) -> str:
    """Wie `label`, aber für HTML: die Vorlage wird escaped, die Werte sind fertiges HTML.

    So können Platzhalter Markup tragen (z. B. eine leere Ausfülllinie), ohne dass
    der Vorlagentext ungeprüft ins HTML gelangt.

    Example:
        >>> label_html("evaluation_grade", "de", blank="<span></span>")
        'Note: <span></span>'
    """
    return escape(_template(key, language, count)).format(**html_values)
