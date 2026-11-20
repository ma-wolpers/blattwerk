"""`Sprache` im Frontmatter: Auflösung, Label-Tabelle (SSOT) und Diagnose `FM013`.

Ohne Feld gilt der Programm-Standard Deutsch; ein gültiger Wert schaltet alle festen
Ausgabetexte um; ein unbekannter Wert ist eine Warnung mit Rückfall auf Deutsch.
"""

from __future__ import annotations

import string

import pytest

from app.core.blatt_validator import has_blocking_diagnostics, inspect_markdown_text
from app.core.document_labels_data import DEFAULT_LANGUAGE, LABELS, LANGUAGES
from app.core.document_language import (
    html_lang,
    label,
    label_html,
    language_from_options,
    resolve_document_language,
)

HEAD = "---\nTitel: T\nFach: M\nThema: X\n{extra}---\n:::task\nA\n:::\n"


@pytest.mark.parametrize(
    ("meta", "expected", "has_problem"),
    [
        ({}, "de", False),
        (None, "de", False),
        ({"Sprache": ""}, "de", False),
        ({"Sprache": "pt-BR"}, "pt-br", False),
        ({"Sprache": " PT-br "}, "pt-br", False),
        ({"Sprache": "de"}, "de", False),
        ({"Sprache": "klingonisch"}, "de", True),
    ],
)
def test_resolution(meta, expected, has_problem):
    """Dokumentwert vor Programm-Standard; unbekannt fällt sichtbar auf Deutsch zurück."""
    language, problem = resolve_document_language(meta)
    assert language == expected
    assert (problem is not None) is has_problem


def _placeholders(template: str) -> set[str]:
    """Namen aller ``{name}``-Platzhalter einer Vorlage."""
    return {name for _text, name, _spec, _conv in string.Formatter().parse(template) if name}


def test_every_label_has_every_language_with_same_placeholders():
    """Guardrail: keine Sprache fehlt, alle Formen nutzen dieselben Platzhalter."""
    for key, entry in LABELS.items():
        assert set(entry) == set(LANGUAGES), key
        reference = _placeholders(entry[DEFAULT_LANGUAGE] if isinstance(entry[DEFAULT_LANGUAGE], str) else entry[DEFAULT_LANGUAGE][0])
        for language, template in entry.items():
            forms = template if isinstance(template, tuple) else (template,)
            assert len(forms) in (1, 2), (key, language)
            for form in forms:
                assert _placeholders(form) == reference, (key, language, form)


def test_german_default_output_is_unchanged():
    """Der Standard reproduziert die bisherigen festen Texte exakt."""
    assert label("task_numbered", None, number=2) == "Aufgabe 2"
    assert label("points", "de", count=1, points="1") == "1 P"
    assert label("bonus_points", "de", count=1, points="1") == "+1 Bonuspunkte"
    assert label("page_of", "de", page=1, pages=2) == "Seite 1 von 2"
    assert html_lang(None) == "de"


@pytest.mark.parametrize(("count", "expected"), [(1, "1 pt"), (1.5, "1,5 pt"), (2, "2 pts"), (None, "2 pt")])
def test_portuguese_plural(count, expected):
    """Portugiesisch: Singular unter 2, sonst Plural; ohne count die erste Form."""
    points = expected.split()[0]
    assert label("points", "pt-br", count=count, points=points) == expected


def test_label_html_escapes_template_not_values():
    """Die Vorlage wird escaped, Platzhalterwerte sind fertiges HTML."""
    assert label_html("evaluation_grade", "pt-br", blank="<span></span>") == "Nota: <span></span>"


def test_language_from_options_defaults():
    """Fehlende oder unbekannte Laufzeitoption -> Programm-Standard."""
    assert language_from_options({}) == "de"
    assert language_from_options({"_language": "pt-br"}) == "pt-br"
    assert language_from_options({"_language": "xx"}) == "de"


def _fm013(text):
    """Bericht und alle FM013-Diagnosen eines Dokuments."""
    report = inspect_markdown_text(text, document_type="worksheet")
    return report, [d for d in report.diagnostics if d.code == "FM013"]


@pytest.mark.parametrize("extra", ["", "Sprache: pt-BR\n", "Sprache: de\n", "Sprache:\n"])
def test_valid_or_missing_language_has_no_warning(extra):
    """Gültige, leere oder fehlende Sprache meldet nichts."""
    _report, hits = _fm013(HEAD.format(extra=extra))
    assert hits == []


def test_unknown_language_warns_but_does_not_block():
    """Unbekannte Sprache: Warnung FM013 mit erlaubten Werten, Build nicht blockiert."""
    report, hits = _fm013(HEAD.format(extra="Sprache: fr\n"))
    assert len(hits) == 1
    assert hits[0].severity == "warning"
    assert "pt-br" in hits[0].message
    assert not has_blocking_diagnostics(report.diagnostics)
