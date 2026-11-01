"""Einzige Registrierung der Diagrammblöcke (Name, Optionen, Snippet, Schlüsselwörter).

Ein neuer Diagrammblock ist genau ein Eintrag in `DIAGRAM_BLOCKS` plus sein Modul.
Daraus abgeleitet werden: `KNOWN_BLOCK_TYPES`/`BLOCK_OPTION_SPECS`, die Einfüge-
Snippets und das Menü, die Liste der PPTX-Bildblöcke, Rendering, Layoutschätzung,
Validierung, die Editor-Hervorhebung und über `tools/docs/sync_diagram_grammar.py`
die VS-Code-Grammatik.

Reine Daten ohne Renderer-Importe, damit `blatt_validator_constants` diese Datei
ohne Importzyklus lesen kann. Die Funktionen löst `diagram_block_dispatch` auf.

Vertrag eines Moduls `app.core.<module>`:

* `render(options, content, include_solutions) -> str`: rein und deterministisch,
  wirft nie wegen Nutzereingaben. Erhält den rohen Inhalt.
* `parse(content) -> (modell, issues)`: fehlertolerant; ein leeres Modell ist falsy.
* optional `check(collect, options, modell)`: fachliche Prüfungen.
* optional `estimate_weight(options, content) -> float`, sonst die gemeinsame Schätzung.
"""

# line-limit: data-only
from __future__ import annotations

import re

from .blatt_validator_specs import MISSING, BlockOptionSpec, DiagramBlockSpec


_STRUCTOGRAM_KEYWORDS = ("wenn", "sonst", "auswahl", "fall", "solange", "für", "wiederhole", "bis", "rückgabe", "eingabe")

DIAGRAM_BLOCKS: tuple[DiagramBlockSpec, ...] = (
    DiagramBlockSpec(
        name="structogram",
        title="Struktogramm",
        module="diagram_structogram",
        snippet=(
            ':::structogram signature="istEnthalten(d: dyn. Reihung vom Inhaltstyp Ganzzahl, v: Ganzzahl): Wahrheitswert"\n'
            "für alle x aus d\n"
            "    wenn x = v\n"
            "        rückgabe wahr\n"
            "% rückgabe falsch\x01\n"
            ":::\n"
        ),
        empty_code="SG007",
        keywords=_STRUCTOGRAM_KEYWORDS,
        options=(BlockOptionSpec("signature", "text", None, False, MISSING),),
    ),
    DiagramBlockSpec(
        name="classdiagram",
        title="Klassendiagramm",
        module="diagram_class",
        snippet=(
            ":::classdiagram\n"
            "klasse Person\n"
            "    - name: Zeichenkette\n"
            "    c Person()\n"
            "    + getName(): Zeichenkette\n"
            "klasse Schueler\n"
            "    - jahrgang: Ganzzahl\n"
            "Schueler -|> Person\x01\n"
            ":::\n"
        ),
        empty_code="CD001",
        keywords=("klasse", "objekt"),
    ),
    DiagramBlockSpec(
        name="erdiagram",
        title="ER-Diagramm",
        module="diagram_er",
        snippet=(
            ":::erdiagram\n"
            "entität Klasse\n"
            "    __Bezeichnung__\n"
            "entität Schueler\n"
            "    __Name__\n"
            "Klasse 1 - gehoertZu - n Schueler\x01\n"
            ":::\n"
        ),
        empty_code="ER001",
        keywords=("entität",),
    ),
    DiagramBlockSpec(
        name="statediagram",
        title="Zustandsdiagramm",
        module="diagram_state",
        snippet=(
            ':::statediagram kind=dfa input="a, b"\n'
            "start -> S0\n"
            "ende: S1\n"
            "S0 -> S0: a\n"
            "S0 -> S1: b\n"
            "S1 -> S1: a, b\x01\n"
            ":::\n"
        ),
        empty_code="ST001",
        keywords=("start", "ende"),
        options=(
            BlockOptionSpec("kind", "enum", frozenset({"dfa", "mealy", "pda"}), False, MISSING),
            BlockOptionSpec("input", "text", None, False, MISSING),
            BlockOptionSpec("output", "text", None, False, MISSING),
            BlockOptionSpec("stack", "text", None, False, MISSING),
        ),
    ),
    DiagramBlockSpec(
        name="graph",
        title="Graph/Baum",
        module="diagram_graph",
        snippet=(
            ":::graph\n"
            "A - B: 5\n"
            "B - C: 2\n"
            "A - C: %{7}\x01\n"
            ":::\n"
        ),
        empty_code="GR001",
        options=(
            BlockOptionSpec("layout", "enum", frozenset({"auto", "tree", "circle"}), False, "auto"),
            BlockOptionSpec("binary", "boolean", None, False, False),
        ),
    ),
    DiagramBlockSpec(
        name="networkdiagram",
        title="Netzwerkplan",
        module="diagram_network",
        snippet=(
            ":::networkdiagram\n"
            "PC1 - Switch - Router - Internet\n"
            "PC2 - Switch\x01\n"
            ":::\n"
        ),
        empty_code="NW001",
    ),
)

DIAGRAM_BLOCKS_BY_NAME = {spec.name: spec for spec in DIAGRAM_BLOCKS}
DIAGRAM_BLOCK_NAMES = frozenset(DIAGRAM_BLOCKS_BY_NAME)
DIAGRAM_HEADER_RE = re.compile(r"^\s*:::(?:" + "|".join(sorted(DIAGRAM_BLOCK_NAMES)) + r")(?=\s|$)")
"""Erkennt die Kopfzeile eines Diagrammblocks; dort stehen Zeilenmarker nach der Einrückung."""
