# line-limit: data-only
"""Feste Ausgabetexte je Dokumentsprache -- die einzige Quelle (SSOT) aller Labels,
die Blattwerk selbst in Schüler-Dokumente schreibt.

Gewählt wird die Sprache über das optionale Frontmatter-Feld `Sprache`
(`document_language.resolve_document_language`); ohne Feld gilt `DEFAULT_LANGUAGE`.
Alle Zugriffe laufen über `document_language.label`/`label_html` -- kein Renderer
schreibt einen dieser Texte selbst.

Format der Einträge:

* Schlüssel = stabiler, sprachneutraler Name; Wert = ``{sprache: vorlage}``.
* Platzhalter in ``{name}``-Schreibweise (``str.format``); alle Sprachen einer
  Vorlage nutzen dieselben Platzhalter (Guardrail-Test).
* Ein Tupel ``(eins, mehrere)`` statt eines Strings ist eine Pluralvorlage; die
  Auswahl trifft `PLURAL_ONE_BELOW` über den ``count`` des Aufrufers. Deutsch
  braucht keine Pluralformen (``P``, ``Bonuspunkte`` sind schon bisher invariant).

Bewusst **nicht** hier: lehrkraftseitige Texte (Erwartungshorizont, Diagnosen,
Editor-Oberfläche) und die Operatorentabelle -- deren Definitionen stammen aus
deutschen Fachdaten (`data/operatoren/`).

Neue Sprache: Eintrag in `LANGUAGES` und je Label eine Vorlage ergänzen; der
Guardrail-Test `tests/test_document_language.py` meldet fehlende Einträge.
"""

DEFAULT_LANGUAGE = "de"
"""Programm-Standard, solange ein Dokument keine `Sprache` angibt."""

LANGUAGES = {
    "de": {"name": "Deutsch", "html_lang": "de", "date_format": "%d.%m.%Y"},
    "pt-br": {"name": "Português (Brasil)", "html_lang": "pt-BR", "date_format": "%d/%m/%Y"},
}
"""Erlaubte Werte für `Sprache` (klein geschrieben; Eingabe ist unabhängig von
Groß-/Kleinschreibung). `html_lang` landet im `<html lang>`-Attribut und steuert
damit die automatische Silbentrennung des Browsers; `date_format` (``strftime``)
formatiert ein als YAML-Datum vorbefülltes `Datum` der Schülerkopfzeile."""

PLURAL_ONE_BELOW = {"pt-br": 2}
"""Pluralregel je Sprache: Singularform, solange ``abs(count)`` kleiner als dieser
Wert ist (Portugiesisch: ``1,5 ponto``, aber ``2 pontos``). Sprachen ohne Eintrag
nutzen immer die erste bzw. einzige Vorlage."""

LABELS = {
    # -- Schülerkopfzeile ----------------------------------------------------
    "student_name": {"de": "Name", "pt-br": "Nome"},
    "student_group": {"de": "Lerngruppe", "pt-br": "Turma"},
    "student_date": {"de": "Datum", "pt-br": "Data"},
    # -- Aufgabenkopf und Punkte ---------------------------------------------
    "task": {"de": "Aufgabe", "pt-br": "Questão"},
    "task_numbered": {"de": "Aufgabe {number}", "pt-br": "Questão {number}"},
    "points": {"de": "{points} P", "pt-br": ("{points} pt", "{points} pts")},
    "bonus_points": {
        "de": "+{points} Bonuspunkte",
        "pt-br": ("+{points} pt extra", "+{points} pts extras"),
    },
    # -- Lösungen --------------------------------------------------------------
    "solution": {"de": "Lösung", "pt-br": "Solução"},
    "solution_version": {"de": "Lösungsversion", "pt-br": "Gabarito"},
    # -- Kopf- und Fußzeilen ---------------------------------------------------
    "school_year": {"de": "Schuljahr {start}/{end}", "pt-br": "Ano letivo {start}/{end}"},
    "page_of": {"de": "Seite {page} von {pages}", "pt-br": "Página {page} de {pages}"},
    # -- Lernhilfen ------------------------------------------------------------
    "help_title": {"de": "Hilfe", "pt-br": "Ajuda"},
    "help_cards_title": {"de": "Hilfekarten", "pt-br": "Cartões de ajuda"},
    "help_level": {"de": "Stufe {level}", "pt-br": "Nível {level}"},
    "help_reference": {"de": "→ Lernhilfe", "pt-br": "→ Ajuda"},
    "help_references": {"de": "→ Lernhilfen", "pt-br": "→ Ajudas"},
    # -- Klausurteile ----------------------------------------------------------
    "part_a_short": {"de": "Teil A", "pt-br": "Parte A"},
    "part_b_short": {"de": "Teil B", "pt-br": "Parte B"},
    "part_a_heading": {"de": "Teil A – hilfsmittelfrei", "pt-br": "Parte A – sem material de apoio"},
    "part_b_heading": {"de": "Teil B – mit Hilfsmitteln", "pt-br": "Parte B – com material de apoio"},
    "required_part": {"de": "Pflichtteil", "pt-br": "Parte obrigatória"},
    "choice_part": {"de": "Wahlteil {position}", "pt-br": "Parte opcional {position}"},
    "choice_part_note": {
        "de": "Wähle {k} der {n} Wahlteile; gewertet werden die angekreuzten.",
        "pt-br": "Escolha {k} das {n} partes opcionais; serão corrigidas as assinaladas.",
    },
    "choice_part_check": {"de": "Diesen Wahlteil wähle ich.", "pt-br": "Escolho esta parte opcional."},
    # -- Bewertungstabelle -----------------------------------------------------
    "evaluation_task": {"de": "Aufgabe", "pt-br": "Questão"},
    "evaluation_max_points": {"de": "max. Punkte", "pt-br": "pontuação máx."},
    "evaluation_reached": {"de": "erreicht", "pt-br": "obtida"},
    "evaluation_total": {"de": "Gesamt: {points} P", "pt-br": "Total: {points} pts"},
    "evaluation_choice_note": {"de": "Wahlteile: {k} aus {n}", "pt-br": "Partes opcionais: {k} de {n}"},
    "evaluation_percent": {"de": "Dies sind {blank} %", "pt-br": "Isso corresponde a {blank} %"},
    "evaluation_grade": {"de": "Note: {blank}", "pt-br": "Nota: {blank}"},
    "evaluation_footnote": {
        "de": "* Summe nicht ausgewiesen, weil nicht alle Punktzahlen bekannt sind.",
        "pt-br": "* Soma não indicada porque nem todas as pontuações são conhecidas.",
    },
    # -- Antwortblöcke ---------------------------------------------------------
    "choice_true": {"de": "richtig", "pt-br": "verdadeiro"},
    "choice_false": {"de": "falsch", "pt-br": "falso"},
    "crossword_code": {"de": "Lösungscode:", "pt-br": "Palavra-chave:"},
    "crossword_across": {"de": "Waagerecht", "pt-br": "Horizontais"},
    "crossword_down": {"de": "Senkrecht", "pt-br": "Verticais"},
}
"""Alle festen Ausgabetexte; Zugriff ausschließlich über `document_language`."""
