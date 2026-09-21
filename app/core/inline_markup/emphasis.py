"""Der Marker-/Eskalationsparser: `*`/`_`/`==`/`~~`/`~`/`^`/`||`/`!!` auf bereits geschütztem Text.

Läuft auf Text, aus dem `spans.py` bereits Kommentare entfernt und
Mathematik/Code als neutrale Platzhalter ausgelagert hat (Schritte 1-3 der
Auswertungsreihenfolge, siehe `syntax.py`). Dieses Modul kennt keine
HTML-Syntax -- es erzeugt ausschließlich `list[Run]`.

Architektur: eine Folge unabhängiger Durchläufe (`_apply_delimiter_stack`
für `*`/`_`, dann einfache Paar-Matcher für `==`/`~~`/`~`/`^`/`||`), die
jeweils auf den aktuell noch unverarbeiteten (`kind="text"`) Textabschnitten
arbeiten und sie durch neu geflaggte Abschnitte ersetzen. Verschachtelung
über Marker-Familien hinweg (z. B. `**fett _und unterstrichen_**`) entsteht
automatisch, weil jeder Durchlauf erneut in die vom vorherigen Durchlauf
erzeugten `kind="text"`-Abschnitte hineinschaut. Nur `*`/`_` brauchen den
aufwändigeren Delimiter-Stack (gestaffelte Eskalation wie `**so*etwas***`);
alle anderen Marker sind einfache, nicht-eskalierende Paare und werden per
einfachem Escape-bewusstem Regex gematcht.

Escape-Schutz (`escaping.py`) und die abschließende Mathe-/Code-Platzhalter-
Auflösung (`placeholders.py`) sind in eigene Module ausgelagert -- dieses
Modul bleibt auf den eigentlichen Marker-Erkennungsalgorithmus fokussiert.
"""

from __future__ import annotations

import re

from .escaping import protect_escapes
from .placeholders import expand_placeholders
from .runs import Run, style_flags


def _star_flags_for_level(level: int) -> tuple[str, ...]:
    return {1: ("italic",), 2: ("bold",), 3: ("bold", "italic")}[level]


def _underscore_flags_for_level(level: int) -> tuple[str, ...]:
    return {1: ("italic",), 2: ("underline",)}[level]


def _apply_delimiter_stack(text: str, char: str, max_level: int, flags_for_level) -> list[Run]:
    """Parst `char`-Eskalation (z. B. `*`/`**`/`***`) mit gestaffelter Teil-Schließung.

    CommonMark-lite: ein Trennzeichenlauf "kann öffnen" (nicht von
    Leerraum gefolgt) und/oder "kann schließen" (nicht von Leerraum
    vorangegangen). Ist beides zugleich möglich, wird IMMER geöffnet
    (neuer Stack-Frame) -- das ist die Regel, die `**so*etwas***` korrekt
    als `<strong>so<em>etwas</em></strong>` auflöst: der mittlere
    Einzelstern kann sowohl öffnen als auch schließen, wird hier aber als
    neue verschachtelte Öffnung behandelt, sodass der abschließende
    Dreifachstern zuerst die innere (Kursiv-)Ebene und danach die äußere
    (Fett-)Ebene schließt.

    Ein Lauf, der nur schließen kann, schließt gegen den Stack so viel wie
    möglich (`min(Lauflänge, verbleibendes Öffnungsbudget)`). Bei einer nur
    TEILWEISEN Schließung bleibt der Frame auf dem Stack offen (nicht
    gepoppt) -- sein bisheriger Inhalt wird mit der gerade erreichten Stufe
    geflaggt und BLEIBT im selben Frame (nicht in einen äußeren Bucket
    verschoben), damit ein späterer vollständiger Schluss diesen bereits
    geflaggten Inhalt zusätzlich mit der äußeren Stufe versieht. Das löst
    `***das** hier*` korrekt zu `<em><strong>das</strong> hier</em>` auf:
    der mittlere Doppelstern verbraucht 2 der 3 Sterne des öffnenden Laufs
    und flaggt "das" bereits als fett, `hier` kommt danach noch unformatiert
    in denselben (weiterhin offenen) Frame, der abschließende Einzelstern
    schließt die verbleibende eine Stufe (kursiv) über beides hinweg.

    Ein Lauf, der weder öffnen noch schließen kann (Leerraum auf beiden
    Seiten), sowie jeder am Textende nie geschlossene Öffnungs-Frame,
    werden als literaler Text belassen -- kein stilles Verschlucken von
    Text bei fehlerhaft ausbalancierter Syntax.
    """
    if not text or char not in text:
        return [Run(kind="text", text=text)] if text else []

    delimiter_pattern = re.compile(re.escape(char) + "+")
    tokens = delimiter_pattern.split(text)
    runs_between = delimiter_pattern.findall(text)

    output: list[Run] = []
    stack: list[dict] = []  # each: {"remaining": int, "content": list[Run]}

    def bucket() -> list[Run]:
        return stack[-1]["content"] if stack else output

    def push_text(value: str) -> None:
        if value:
            bucket().append(Run(kind="text", text=value))

    def flag_all(items: list[Run], level: int) -> list[Run]:
        flags = flags_for_level(level)
        return [item.with_flags(**{flag: True for flag in flags}) for item in items]

    for index, plain in enumerate(tokens):
        push_text(plain)
        if index >= len(runs_between):
            continue

        run_text = runs_between[index]
        run_len = len(run_text)
        prev_char = plain[-1] if plain else None
        next_plain = tokens[index + 1] if index + 1 < len(tokens) else ""
        next_char = next_plain[0] if next_plain else None
        can_open = next_char is not None and not next_char.isspace()
        can_close = prev_char is not None and not prev_char.isspace()

        effective_len = min(run_len, max_level)
        leftover_literal = char * (run_len - effective_len)

        if can_open and can_close:
            push_text(leftover_literal)
            stack.append({"remaining": effective_len, "content": []})
            continue

        if can_close and stack:
            push_text(leftover_literal)
            remaining_to_consume = effective_len
            while remaining_to_consume > 0 and stack:
                top = stack[-1]
                use = min(remaining_to_consume, top["remaining"])
                remaining_to_consume -= use
                top["remaining"] -= use
                if top["remaining"] == 0:
                    finished = stack.pop()
                    flagged = flag_all(finished["content"], use)
                    bucket().extend(flagged)
                else:
                    top["content"] = flag_all(top["content"], use)
            if remaining_to_consume > 0:
                push_text(char * remaining_to_consume)
            continue

        if can_open:
            push_text(leftover_literal)
            stack.append({"remaining": effective_len, "content": []})
            continue

        push_text(run_text)

    while stack:
        frame = stack.pop()
        opening_literal = char * frame["remaining"]
        target = stack[-1]["content"] if stack else output
        target.append(Run(kind="text", text=opening_literal))
        target.extend(frame["content"])

    return output


def _expand_runs(runs: list[Run], matcher) -> list[Run]:
    """Wendet `matcher(text) -> list[Run]` auf jeden `kind="text"`-Run an, andere Runs bleiben unverändert.

    Ergebnis-Runs erben die bereits gesetzten Stil-Flags des Original-Runs
    (ODER-verknüpft) -- so bleibt eine bereits von einem vorherigen
    Durchlauf gesetzte Flagge (z. B. `bold`) erhalten, während dieser
    Durchlauf weitere Flaggen (z. B. `underline`) hinzufügt.
    """
    expanded: list[Run] = []
    for run in runs:
        if run.kind != "text" or not run.text:
            expanded.append(run)
            continue

        base_flags = style_flags(run)
        for sub_run in matcher(run.text):
            if sub_run.kind != "text":
                expanded.append(sub_run)
                continue
            merged = {key: (value or getattr(sub_run, key)) for key, value in base_flags.items()}
            expanded.append(Run(kind="text", text=sub_run.text, **merged))
    return expanded


def _simple_pair_matcher(delimiter: str, **flags: bool):
    """Baut einen Matcher für einfache, nicht-eskalierende Paar-Marker (`==`, `~~`, `||`, `@@`).

    Nimmt beliebig viele Flags entgegen (statt nur eines) -- `!!...!!`
    braucht sowohl `bold=True` (sichtbar identisch zu `**fett**`) als auch
    `operator=True` (semantische Markierung für `operator_legend.py`), im
    Gegensatz zu `==`/`~~`/`||`, die je nur ein Flag setzen.
    """
    pattern = re.compile(r"(?<!\\)" + re.escape(delimiter) + r"(.+?)(?<!\\)" + re.escape(delimiter))

    def matcher(text: str) -> list[Run]:
        result: list[Run] = []
        last_end = 0
        for match in pattern.finditer(text):
            if match.start() < last_end:
                continue
            if match.start() > last_end:
                result.append(Run(kind="text", text=text[last_end : match.start()]))
            result.append(Run(kind="text", text=match.group(1), **flags))
            last_end = match.end()
        if last_end < len(text):
            result.append(Run(kind="text", text=text[last_end:]))
        return result

    return matcher


def _prefix_matcher(marker_char: str, flag_name: str):
    """Baut einen Matcher für die Präfix-Mechanik von `~`/`^`: `x^y` oder `x^{yz}` -- kein schließendes Zeichen bei Einzelzeichen."""
    escaped = re.escape(marker_char)
    brace_pattern = re.compile(r"(?<!\\)" + escaped + r"\{([^{}]+?)\}")
    bare_pattern = re.compile(r"(?<!\\)" + escaped + r"(?!" + escaped + r")([^\s" + escaped + r"{}])")

    def matcher(text: str) -> list[Run]:
        result: list[Run] = []
        pos = 0
        while pos < len(text):
            brace_match = brace_pattern.match(text, pos)
            if brace_match:
                result.append(Run(kind="text", text=brace_match.group(1), **{flag_name: True}))
                pos = brace_match.end()
                continue
            bare_match = bare_pattern.match(text, pos)
            if bare_match:
                result.append(Run(kind="text", text=bare_match.group(1), **{flag_name: True}))
                pos = bare_match.end()
                continue
            if result and result[-1].kind == "text" and not getattr(result[-1], flag_name):
                result[-1] = Run(kind="text", text=result[-1].text + text[pos], **style_flags(result[-1]))
            else:
                result.append(Run(kind="text", text=text[pos]))
            pos += 1
        return result

    return matcher


_HIGHLIGHT_MATCHER = _simple_pair_matcher("==", highlight=True)
_STRIKE_MATCHER = _simple_pair_matcher("~~", strike=True)
_SPOILER_MATCHER = _simple_pair_matcher("||", spoiler=True)
_OPERATOR_MATCHER = _simple_pair_matcher("!!", bold=True, operator=True)
_SUBSCRIPT_MATCHER = _prefix_matcher("~", "subscript")
_SUPERSCRIPT_MATCHER = _prefix_matcher("^", "superscript")


def parse_emphasis(
    protected_text: str, math_spans: list[str], code_spans: list, word_note_spans: list | None = None
) -> list[Run]:
    """Parst */_/==/~~/~/^/|| auf bereits (Kommentar/Mathe/Code-)geschütztem Text.

    Reihenfolge der Durchläufe: Backslash-Escapes schützen (`escaping.py`)
    -> `*` (Delimiter-Stack) -> `_` (Delimiter-Stack) -> `==` -> `~~` (VOR
    `~`, damit `~~x~~` nicht zuerst als zwei `~`-Präfixe fehlinterpretiert
    wird) -> `~` (Präfix) -> `^` (Präfix) -> `||` -> `!!` -> Platzhalter-
    Expansion (`placeholders.py`).

    WICHTIG: Escape-Platzhalter werden hier bewusst NICHT aufgelöst -- die
    zurückgegebenen `Run.text`-Werte können noch Platzhalter-Zeichen
    enthalten. Auflösung ist konsumentenabhängig (siehe `escaping.py`), da
    `markdown_bridge.py`s "plain" Runs anders behandelt werden müssen als
    direkt gerenderte.
    """
    escaped_text = protect_escapes(protected_text)

    runs: list[Run] = _apply_delimiter_stack(escaped_text, "*", 3, _star_flags_for_level)
    runs = _expand_runs(runs, lambda t: _apply_delimiter_stack(t, "_", 2, _underscore_flags_for_level))
    runs = _expand_runs(runs, _HIGHLIGHT_MATCHER)
    runs = _expand_runs(runs, _STRIKE_MATCHER)
    runs = _expand_runs(runs, _SUBSCRIPT_MATCHER)
    runs = _expand_runs(runs, _SUPERSCRIPT_MATCHER)
    runs = _expand_runs(runs, _SPOILER_MATCHER)
    runs = _expand_runs(runs, _OPERATOR_MATCHER)
    runs = expand_placeholders(runs, math_spans, code_spans, word_note_spans or [])
    return [run for run in runs if run.text]
