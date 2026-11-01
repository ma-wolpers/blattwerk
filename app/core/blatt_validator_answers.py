"""Inhaltliche Prüfungen der Übungsblöcke: Passen die Angaben zueinander?

Bisher gingen Widersprüche still durch, weil die Renderer sie fehlertolerant übergehen,
etwa eine Zuordnung auf einen nicht vorhandenen Eintrag. Die Prüfungen lesen die Blöcke
mit denselben Parsern wie die Renderer, damit beide dasselbe sehen.

Zuständig für `mc`, `checkgrid`, `matching`, `cloze`, `ordering`, `wordsearch`. Einstieg ist
`validate_block_contents`, der auch die übrigen Inhaltsprüfungen aufruft.
"""

from __future__ import annotations

import re
from collections import Counter

import yaml

from .answer_matching_parse import parse_matching_sources
from .answer_special_checkgrid import parse_checkgrid_payload
from .answer_special_ordering import parse_ordering_items
from .answer_special_shared import _normalize_keyword, _parse_option_list
from .answer_special_wordsearch import parse_wordsearch_words
from .blatt_kern_answer_choice import _parse_multiple_choice_content
from .blatt_validator_answers_math import check_geometry, check_numberline, check_table
from .blatt_validator_structure import check_document_structure, check_mindmap, check_selfcheck, check_task_title, check_help
from .diagram_validation import DiagnosticCollector

_CHECKBOX_RE = re.compile(r"^\s*[-*+]\s+\[[ xX]?\]\s")
_TF_VALUES = {"1", "true", "yes", "on", "tf", "richtigfalsch", "richtig_false"}
_GAP_RE = re.compile(r"\{\{\s*[^{}]+?\s*\}\}")


def check_mc(collect, options, content) -> None:
    """Prüft Auswahlaufgaben (`AN021`-`AN024`)."""
    if _normalize_keyword(options.get("tf") or options.get("true_false"), default="false") in _TF_VALUES:
        if any(_CHECKBOX_RE.match(line) for line in (content or "").splitlines()):
            collect.add("AN023", "`tf=true` erwartet reine Aussagen, eine pro Zeile. `- [x]` erscheint sonst wörtlich.", severity="error")
        return
    _question, groups = _parse_multiple_choice_content(content)
    for question, choices in groups:
        where = f" bei „{question}“" if question else ""
        if not any(correct for _label, correct in choices) and not options.get("correct"):
            collect.add("AN021", f"Keine Antwort ist als richtig markiert{where}.", anchor=f"AN021:{question}")
        repeated = [label for label, count in Counter(label for label, _correct in choices).items() if count > 1]
        if repeated:
            collect.add("AN022", f"Die Antwort `{repeated[0]}` steht doppelt{where}.", anchor=f"AN022:{question}")
    labels = _parse_option_list(options.get("options")) if options.get("options") else []
    total = sum(len(choices) for _question, choices in groups) or len(labels)
    for value in _parse_option_list(options.get("correct")) if options.get("correct") else []:
        if total and str(value).isdigit() and not 1 <= int(value) <= total:
            collect.add("AN024", f"`correct={value}`, es gibt aber nur {total} Antworten.", severity="error", anchor=f"AN024:{value}")


def check_checkgrid(collect, _options, content) -> None:
    """Prüft Ankreuztabellen: Spalten vorhanden, `correct` zeigt auf eine Spalte (`AN025`, `AN026`)."""
    columns, rows = parse_checkgrid_payload(content)
    if not columns or not rows:
        collect.add("AN026", "Es braucht `columns:` und `rows:` mit mindestens einer Aussage.")
        return
    try:
        raw_rows = (yaml.safe_load(content) or {}).get("rows") or []
    except yaml.YAMLError:
        return
    for entry in raw_rows if isinstance(raw_rows, list) else []:
        value = entry.get("correct", entry.get("richtig")) if isinstance(entry, dict) else None
        if value is None:
            continue
        if not (str(value).isdigit() and 1 <= int(value) <= len(columns)):
            collect.add("AN025", f"`correct: {value}` bei „{entry.get('text')}“, es gibt aber nur {len(columns)} Spalten.", severity="error", anchor=f"AN025:{entry.get('text')}")


def check_matching(collect, options, content) -> None:
    """Prüft Zuordnungen auf Widersprüche und Positionslösungen (`AN027`-`AN031`)."""
    first, second, pairs, worksheet_pairs = parse_matching_sources(options, content)
    if not first or not second:
        return
    for left, right in pairs + worksheet_pairs:
        if not (1 <= left <= len(first) and 1 <= right <= len(second)):
            collect.add("AN027", f"Die Verbindung `{left}-{right}` zeigt auf einen Eintrag, den es nicht gibt.", severity="error", anchor=f"AN027:{left}-{right}")
    valid = [pair for pair in pairs if 1 <= pair[0] <= len(first) and 1 <= pair[1] <= len(second)]
    if not valid:
        collect.add("AN028", "Es gibt keine `matches:`, die Lösung bleibt leer.")
        return
    for side, items, index in (("links", first, 0), ("rechts", second, 1)):
        for position, item in enumerate(items, start=1):
            if position not in {pair[index] for pair in valid}:
                collect.add("AN029", f"„{item}“ ({side}) hat keine Verbindung.", anchor=f"AN029:{side}:{position}")
    if len(valid) >= 2 and all(left == right for left, right in valid):
        collect.add("AN030", "Alle Verbindungen laufen gerade (`1-1`, `2-2`, …). Die Aufgabe lässt sich ohne Inhalt nur über die Position lösen.")
    for pair in worksheet_pairs:
        if pair not in valid and 1 <= pair[0] <= len(first) and 1 <= pair[1] <= len(second):
            collect.add("AN031", f"`worksheet_matches` zeigt `{pair[0]}-{pair[1]}`, das steht aber nicht in `matches`.", severity="error", anchor=f"AN031:{pair}")


def check_cloze(collect, _options, content) -> None:
    """Prüft Lückentexte: mindestens eine Lücke, jede Klammer geschlossen (`AN045`, `AN046`)."""
    text = content or ""
    if not text.strip():
        return
    without_gaps = _GAP_RE.sub("", text)
    if "{{" in without_gaps or "}}" in without_gaps:
        collect.add("AN046", "Eine Lücke ist nicht korrekt geschlossen, erwartet wird `{{Wort}}`.", severity="error")
    elif not _GAP_RE.search(text):
        collect.add("AN045", "Der Text enthält keine Lücke (`{{Wort}}`).")


def check_ordering(collect, _options, content) -> None:
    """Prüft Reihenfolgen: Es gibt etwas zu ordnen, und jede Position ist eindeutig (`AN047`, `AN048`)."""
    items = parse_ordering_items(content)
    if not items:
        return
    if len(items) < 2:
        collect.add("AN047", "Mit einem Element gibt es nichts zu ordnen.")
    repeated = [item for item, count in Counter(items).items() if count > 1]
    if repeated:
        collect.add("AN048", f"`{repeated[0]}` steht doppelt, damit ist die richtige Reihenfolge nicht eindeutig.")


def check_wordsearch(collect, options, content) -> None:
    """Prüft Wortsuchen auf doppelte Wörter und abgeschaltete Richtungen (`AN043`, `AN044`)."""
    words = [re.sub(r"^[-*+]\s+", "", line.strip()).strip().upper() for line in (content or "").splitlines() if line.strip()]
    repeated = [word for word, count in Counter(words).items() if count > 1]
    if repeated:
        collect.add("AN043", f"`{repeated[0]}` steht doppelt und wird nur einmal versteckt.")
    if parse_wordsearch_words(options, content) and all(
        str(options.get(key, "true")).strip().lower() in {"0", "false", "no", "off"} for key in ("horizontal", "vertical", "diagonal")
    ):
        collect.add("AN044", "Alle Richtungen sind ausgeschaltet, kein Wort lässt sich verstecken.", severity="error")


_CHECKS = {
    "mc": ("Auswahlaufgabe", check_mc),
    "checkgrid": ("Ankreuztabelle", check_checkgrid),
    "matching": ("Zuordnung", check_matching),
    "cloze": ("Lückentext", check_cloze),
    "ordering": ("Reihenfolge", check_ordering),
    "wordsearch": ("Wortsuche", check_wordsearch),
    "table": ("Tabelle", check_table),
    "numberline": ("Zahlengerade", check_numberline),
    "geometry": ("Koordinatensystem", check_geometry),
    "selfcheck": ("Selbsteinschätzung", check_selfcheck),
    "mindmap": ("Mindmap", check_mindmap),
    "help": ("Lernhilfe", check_help),
    "task": ("Aufgabe", check_task_title),
    "subtask": ("Teilaufgabe", check_task_title),
}
"""Blocktyp auf Anzeigename und Prüfung; neue Inhaltsprüfungen werden hier eingetragen."""


def validate_block_contents(blocks) -> list:
    """Prüft alle Blöcke eines Dokuments inhaltlich und die Blockfolge im Dokument."""
    diagnostics = []
    for index, (block_type, options, content) in enumerate(blocks):
        entry = _CHECKS.get(block_type)
        if entry is None:
            continue
        title, check = entry
        collect = DiagnosticCollector(index, block_type, options, title)
        check(collect, options or {}, content)
        diagnostics.extend(collect.diagnostics)
    diagnostics.extend(check_document_structure(blocks))
    return diagnostics
