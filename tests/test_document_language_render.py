"""`Sprache` wirkt auf alle festen Ausgabetexte im HTML -- und ohne Feld bleibt alles deutsch.

Prüft je Renderpfad (Arbeitsblatt/Klausur, Lösungsfassung, Bewertungstabelle,
Wahlteile, Antwortblöcke, Lernhilfen, Präsentation) die portugiesischen Labels und
dass der Programm-Standard die bisherigen deutschen Texte erzeugt.
"""

from __future__ import annotations

from datetime import date

from app.core.blatt_kern_help_render import render_help_cards_html
from app.core.blatt_kern_layout_render import render_html
from app.core.blatt_kern_shared import parse_blocks

META = {"Titel": "T", "Fach": "M", "Thema": "X", "show_student_header": "ja", "Datum": date(2026, 9, 25)}
PT = {**META, "Sprache": "pt-BR"}

EXAM = """:::task points=2 title="Brüche"
Rechne.
:::
:::subtask points=2
a
:::
:::subtask points=1 bonus=true
Extra
:::
:::solution
1/2
:::
:::task points=1
B
:::
:::evaluation grade=true
:::
"""

CHOICE_EXAM = """:::task points=2
A
:::
--w[1] Erster
:::task points=2
B
:::
--w Zweiter
:::task points=2
C
:::
:::evaluation
:::
"""

HM_EXAM = """:::task points=2
A
:::
--hm
:::task points=2
B
:::
"""


def _html(meta, body, document_type="exam", include_solutions=False):
    """Rendert ``body`` mit ``meta``: ``<html lang>``-Zeile plus sichtbarer Body.

    Der ``<head>`` (Stylesheet-Kommentare nennen z. B. „Lerngruppe/Datum“) bleibt
    außen vor, damit die Negativprüfungen nur sichtbaren Text treffen.
    """
    html = render_html(dict(meta), parse_blocks(body), document_type=document_type, include_solutions=include_solutions)
    lang_line = html.splitlines()[1]
    return lang_line + html[html.index("</head>"):]


def test_portuguese_exam_labels():
    """Kopfzeile, Aufgabenlabel, Punkte, Bonus, Bewertungstabelle, Datum, lang-Attribut."""
    html = _html(PT, EXAM)
    for text in ("Questão 1", "2 pts", "+1 pt extra", "Nome", "Turma", "Data", "25/09/2026",
                 "Ano letivo", "pontuação máx.", "obtida", "Nota:", '<html lang="pt-BR">'):
        assert text in html, text
    for german in ("Aufgabe 1", "Lerngruppe", "Schuljahr", "max. Punkte", "Note:"):
        assert german not in html, german


def test_german_default_is_unchanged():
    """Ohne `Sprache` bleiben alle bisherigen deutschen Texte erhalten."""
    html = _html(META, EXAM)
    for text in ("Aufgabe 1", "2 P", "+1 Bonuspunkt<", "Lerngruppe", "Datum", "25.09.2026",
                 "Schuljahr", "max. Punkte", "erreicht", "Note:", '<html lang="de">'):
        assert text in html, text


def test_portuguese_solution_version():
    """Lösungsfassung: Badge im Dokumentkopf und Label der Musterlösung."""
    html = _html(PT, EXAM, include_solutions=True)
    assert "Gabarito" in html and "Solução" in html
    assert "Lösungsversion" not in html and ">Lösung<" not in html


def test_unknown_language_falls_back_to_german():
    """Unbekannter Wert: deutsch rendern (Warnung kommt vom Validator)."""
    html = _html({**META, "Sprache": "fr"}, EXAM)
    assert "Aufgabe 1" in html and '<html lang="de">' in html


def test_portuguese_choice_parts_and_evaluation():
    """Wahlteil-Überschriften, Wahlhinweis, Ankreuzfeld und Tabellenhinweis."""
    html = _html(PT, CHOICE_EXAM)
    for text in ("Parte opcional 1 – Erster", "Escolha 1 das 2 partes opcionais",
                 "Escolho esta parte opcional.", "Partes opcionais: 1 de 2", "Total:"):
        assert text in html, text
    assert "Wahlteil" not in html


def test_portuguese_aid_parts():
    """Teil A/B-Überschriften der Hilfsmittelteile."""
    html = _html(PT, HM_EXAM)
    assert "Parte A – sem material de apoio" in html and "Parte B – com material de apoio" in html


def test_portuguese_true_false_and_crossword():
    """Antwortblöcke: richtig/falsch und Kreuzworträtsel-Überschriften."""
    body = ":::mc tf=true\nAussage\n:::\n:::crossword\nentries:\n  - {word: HAUS, clue: Gebäude}\n  - {word: AST, clue: Zweig}\n:::\n"
    html = _html(PT, body, document_type="worksheet")
    assert "verdadeiro" in html and "falso" in html
    assert "richtig" not in html


def test_portuguese_help_reference_and_cards():
    """Verweis an der Aufgabe und Lernhilfenkarte (Standardtitel, Stufe)."""
    body = ":::task\nA\n:::\n:::help level=2\nTipp\n:::\n"
    worksheet = _html(PT, body, document_type="worksheet")
    assert "→ Ajuda" in worksheet and "Lernhilfe" not in worksheet
    cards = render_help_cards_html(dict(PT), parse_blocks(body))
    assert "Ajuda" in cards and "Nível 2" in cards and '<html lang="pt-BR">' in cards


def test_portuguese_presentation():
    """Präsentationspfad: Aufgabenlabel und lang-Attribut."""
    html = _html(PT, ":::task\nA\n:::\n", document_type="presentation")
    assert '<html lang="pt-BR">' in html
