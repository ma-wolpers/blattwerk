"""Reine Konstanten/Datentabellen für den Blattwerk-Kernparser.

Enthält ausschließlich Sets/Dicts/Dataclass-Tupel ohne Logik — vom
300-Zeilen-Limit ausgenommen, analog zu `blatt_validator_constants.py`.

`CONTROL_MARKERS` ist die einzige normative Quelle für die
Blattwerk-eigene Kontrollsyntax (`--!`, `-+`, `--hf`, `--# ...`,
`-=<länge>`, `--`): sowohl `blatt_kern_shared_parsing._parse_inline_control_marker`
(Parser) als auch `blatt_validator_patterns.py` (Validator-Diagnostik)
lesen ihre Muster von hier, statt eigene Kopien der Regexe zu pflegen.
`---` (Standard-Markdown-Trennlinie mit CSS-Zusatzabstand) ist bewusst
**kein** Eintrag hier — der Parser erkennt es nicht als eigenes Token,
es bleibt gewöhnliches Markdown plus eine CSS-Regel in
`assets/worksheet.css`.

`JA_NEIN_BOOLEAN_TOKENS` ist das von `_meta_bool_ja_nein`
(`blatt_kern_shared_meta.py`) akzeptierte Boolean-Vokabular, benannt
ausgelagert, damit `app/core/markdown_conventions.py` (Doku-Collector)
und der Validator (`FM006`, siehe `blatt_validator_document.py`)
dieselbe Quelle referenzieren können, statt das Vokabular ein zweites
Mal als Literal zu pflegen. Dieses Vokabular ist **nicht** identisch
mit `TRUTHY_META_BOOLEAN_TOKENS` in `blatt_validator_constants.py`
(dort ohne `j`/`n`, dafür mit `wahr`/`falsch`) — beide Konstanten
spiegeln zwei echte, unterschiedliche Boolean-Parser im Code, keine
künstlich vereinheitlichte Konvention.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MARKDOWN_EXTENSIONS = ["tables", "nl2br"]

WORK_MODE_MAP = {
    "single": ("👤", "Einzelarbeit", "single"),
    "sgl": ("👤", "Einzelarbeit", "single"),
    "ea": ("👤", "Einzelarbeit", "single"),
    "einzel": ("👤", "Einzelarbeit", "single"),
    "partner": ("👥", "Partnerarbeit", "partner"),
    "pa": ("👥", "Partnerarbeit", "partner"),
    "group": ("👪", "Gruppenarbeit", "group"),
    "grp": ("👪", "Gruppenarbeit", "group"),
    "ga": ("👪", "Gruppenarbeit", "group"),
    "gruppe": ("👪", "Gruppenarbeit", "group"),
}
"""`einzelarbeit`/`partnerarbeit`/`gruppenarbeit` sind entfernt (siehe
`KNOWN_WORK_VALUES` in `blatt_validator_constants.py`) -- die Anzeige-Labels
bleiben unverändert lang/freundlich, obwohl die Eingabesyntax kürzer wurde."""

TASK_ACTION_MAP = {
    "exchange": ("💬", "austauschen", "action"),
    "exc": ("💬", "austauschen", "action"),
    "austauschen": ("💬", "austauschen", "action"),
    "aus": ("💬", "austauschen", "action"),
    "decide": ("⚖️", "entscheiden", "action"),
    "dec": ("⚖️", "entscheiden", "action"),
    "entscheiden": ("⚖️", "entscheiden", "action"),
    "ent": ("⚖️", "entscheiden", "action"),
    "experiment": ("🧪", "experimentieren", "action"),
    "experimentieren": ("🧪", "experimentieren", "action"),
    "exp": ("🧪", "experimentieren", "action"),
    "reflect": ("🤔", "reflektieren", "action"),
    "reflektieren": ("🤔", "reflektieren", "action"),
    "ref": ("🤔", "reflektieren", "action"),
    "read": ("📖", "lesen", "action"),
    "rd": ("📖", "lesen", "action"),
    "lesen": ("📖", "lesen", "action"),
    "les": ("📖", "lesen", "action"),
    "calculate": ("🔢", "rechnen", "action"),
    "calc": ("🔢", "rechnen", "action"),
    "rechnen": ("🔢", "rechnen", "action"),
    "rech": ("🔢", "rechnen", "action"),
    "match": ("↔️", "zuordnen", "action"),
    "mat": ("↔️", "zuordnen", "action"),
    "zuordnen": ("↔️", "zuordnen", "action"),
    "zuo": ("↔️", "zuordnen", "action"),
    "write": ("✍️", "schreiben", "action"),
    "wrt": ("✍️", "schreiben", "action"),
    "schreiben": ("✍️", "schreiben", "action"),
    "schr": ("✍️", "schreiben", "action"),
    "draw": ("📐", "zeichnen", "action"),
    "drw": ("📐", "zeichnen", "action"),
    "zeichnen": ("📐", "zeichnen", "action"),
    "zei": ("📐", "zeichnen", "action"),
}

TASK_HINT_MAP = {
    "tip": ("💡", "Tipp", "hint"),
    "hint": ("💡", "Tipp", "hint"),
    "tipp": ("💡", "Tipp", "hint"),
    "tp": ("💡", "Tipp", "hint"),
    "definition": ("📘", "Definition", "hint"),
    "def": ("📘", "Definition", "hint"),
    "remember": ("💭", "Erinnerung", "hint"),
    "rem": ("💭", "Erinnerung", "hint"),
    "reminder": ("💭", "Erinnerung", "hint"),
    "erinnerung": ("💭", "Erinnerung", "hint"),
    "eri": ("💭", "Erinnerung", "hint"),
    "term": ("📖", "Fachwort", "hint"),
    "tm": ("📖", "Fachwort", "hint"),
    "fachwort": ("📖", "Fachwort", "hint"),
    "fw": ("📖", "Fachwort", "hint"),
    "expert": ("🚀", "Expertenaufgabe", "hint"),
    "experte": ("🚀", "Expertenaufgabe", "hint"),
}
"""`expertenaufgabe` ist entfernt (siehe `KNOWN_HINT_VALUES`), ersetzt durch
`experte` -- das Anzeige-Label "Expertenaufgabe" bleibt unverändert."""

HELP_BLOCK_TYPES = {"help", "hilfe"}
DOCUMENT_MODES = {"worksheet", "solution", "presentation", "test"}
DOCUMENT_MODE_ALIASES = {
    "ws": "worksheet",
    "worksheet": "worksheet",
    "solution": "solution",
    "presentation": "presentation",
    "test": "test",
}

PRESENTATION_SECTION_MARK_PATTERN = re.compile(r"^--#\s+(.+)$")
PRESENTATION_SPACER_MARK_PATTERN = re.compile(
    r"^-=\s*(\d+(?:\.\d+)?(?:cm|mm|px|pt|em|rem|vh|vw|%))\s*$",
    flags=re.IGNORECASE,
)

JA_NEIN_TRUE_TOKENS = frozenset({"1", "true", "yes", "on", "ja", "j"})
JA_NEIN_FALSE_TOKENS = frozenset({"0", "false", "no", "off", "nein", "n"})
JA_NEIN_BOOLEAN_TOKENS = JA_NEIN_TRUE_TOKENS | JA_NEIN_FALSE_TOKENS
"""Von `_meta_bool_ja_nein` akzeptiertes Boolean-Vokabular (EN/DE inkl. Einzelbuchstaben).

`JA_NEIN_BOOLEAN_TOKENS` (die Vereinigung) ist die Konstante, gegen die
Validator (`FM006`) und Doku-Collector auf reine Mitgliedschaft prüfen;
`JA_NEIN_TRUE_TOKENS`/`JA_NEIN_FALSE_TOKENS` sind nur für
`_meta_bool_ja_nein` selbst relevant (welcher Wert wird zu `True`/
`False`).
"""


@dataclass(frozen=True)
class ControlMarkerSpec:
    """Ein einzelner Blattwerk-Kontrollsyntax-Marker: wie er erkannt wird und was er erzeugt.

    `block_type` muss, wenn gesetzt, in `KNOWN_BLOCK_TYPES`
    (`blatt_validator_constants.py`) existieren — die pseudo-Blocktypen
    `pagebreak`/`framebreak`/`slidechromeoff`/`sectionmark`/`vspacer`
    sind dort bereits gelistet, dieser Katalog liefert nur zusätzlich
    die konkrete Syntax dazu. `block_type=None` markiert Marker ohne
    eigenen pseudo-Blocktyp (aktuell nur `--`, siehe unten) — für diese
    Einträge entfällt die Cross-Konsistenzprüfung gegen
    `KNOWN_BLOCK_TYPES`. `option_capture` benennt, in welche
    Blockoption(en) eine ggf. vorhandene Regex-Gruppe (in Reihenfolge)
    einfließt; bei literalen Markern ohne Gruppen ist das Tupel leer.
    """

    name: str
    block_type: str | None
    kind: str  # "literal" | "pattern"
    literal_or_regex: str | re.Pattern
    option_capture: tuple[str, ...] = ()


CONTROL_MARKERS: tuple[ControlMarkerSpec, ...] = (
    ControlMarkerSpec(
        name="pagebreak",
        block_type="pagebreak",
        kind="literal",
        literal_or_regex="--!",
    ),
    ControlMarkerSpec(
        name="framebreak",
        block_type="framebreak",
        kind="literal",
        literal_or_regex="-+",
    ),
    ControlMarkerSpec(
        name="slidechromeoff",
        block_type="slidechromeoff",
        kind="literal",
        literal_or_regex="--hf",
    ),
    ControlMarkerSpec(
        name="sectionmark",
        block_type="sectionmark",
        kind="pattern",
        literal_or_regex=PRESENTATION_SECTION_MARK_PATTERN,
        option_capture=("title",),
    ),
    ControlMarkerSpec(
        name="vspacer",
        block_type="vspacer",
        kind="pattern",
        literal_or_regex=PRESENTATION_SPACER_MARK_PATTERN,
        option_capture=("height",),
    ),
    ControlMarkerSpec(
        name="soft_section_break",
        block_type=None,
        kind="literal",
        literal_or_regex="--",
    ),
)
"""Syntaktische Tokens, die der Blattwerk-Parser als eigene Kontrollsyntax
interpretiert. `soft_section_break` (`--`) erzeugt keinen pseudo-Block
wie die anderen Einträge, sondern eine `<!--BLATTWERK_SECTION_BREAK-->`-
Markierung im Rohtext (siehe `blatt_kern_shared_parsing.parse_blocks`);
deshalb `block_type=None` statt eines erfundenen Blocktyps. `---`
(gewöhnliche Markdown-Trennlinie mit CSS-Zusatzabstand) ist bewusst
**kein** Eintrag hier — der Parser erkennt sie gar nicht als eigenes
Token.
"""
