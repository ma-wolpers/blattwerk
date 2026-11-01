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
    DiagramBlockSpec(
        name="flowchart",
        title="Flussdiagramm",
        module="diagram_flow",
        snippet=(
            ":::flowchart\n"
            "wenn x > 0\n"
            "    rückgabe x\n"
            "sonst\n"
            "    % rückgabe 0\x01\n"
            ":::\n"
        ),
        empty_code="FC001",
        keywords=_STRUCTOGRAM_KEYWORDS,
        options=(BlockOptionSpec("signature", "text", None, False, MISSING),),
    ),
    DiagramBlockSpec(
        name="sequencediagram",
        title="Sequenzdiagramm",
        module="diagram_sequence",
        snippet=(
            ":::sequencediagram\n"
            "Client -> Server: anfrage()\n"
            "Server --> Client: %{antwort}\x01\n"
            ":::\n"
        ),
        empty_code="SQ001",
        keywords=("teilnehmer",),
    ),
    DiagramBlockSpec(
        name="syntaxdiagram",
        title="Syntaxdiagramm",
        module="diagram_syntax",
        snippet=(
            ":::syntaxdiagram\n"
            'Zahl = [ "-" ] Ziffer { Ziffer }\x01\n'
            ":::\n"
        ),
        empty_code="SY001",
    ),
    DiagramBlockSpec(
        name="logicgates",
        title="Logikgatter",
        module="diagram_logic",
        snippet=(
            ":::logicgates truthtable=true\n"
            "Q = (A und B) oder nicht C\x01\n"
            ":::\n"
        ),
        empty_code="LG001",
        options=(
            BlockOptionSpec("norm", "enum", frozenset({"iec", "ansi"}), False, "iec"),
            BlockOptionSpec("truthtable", "boolean", None, False, False),
            BlockOptionSpec("gaps", "boolean", None, False, False),
        ),
    ),
    DiagramBlockSpec(
        name="probabilitytree",
        title="Baumdiagramm",
        module="diagram_probability",
        snippet=(
            ":::probabilitytree\n"
            "Rot: 1/3\n"
            "    Rot: 1/4\n"
            "    Blau: 3/4\n"
            "Blau: %{2/3}\x01\n"
            ":::\n"
        ),
        empty_code="PB001",
    ),
    DiagramBlockSpec(
        name="termtree",
        title="Rechenbaum",
        module="diagram_term",
        snippet=":::termtree gaps=results\n(3+4)*2\x01\n:::\n",
        empty_code="TT001",
        options=(BlockOptionSpec("gaps", "enum", frozenset({"none", "results", "leaves", "all"}), False, "none"),),
    ),
    DiagramBlockSpec(
        name="timeline",
        title="Zeitstrahl",
        module="diagram_timeline",
        snippet=":::timeline\n1789: Französische Revolution\n1848: Märzrevolution\x01\n:::\n",
        empty_code="TL001",
        options=(BlockOptionSpec("scale", "enum", frozenset({"even", "proportional"}), False, "even"),),
    ),
    DiagramBlockSpec(
        name="chart",
        title="Statistikdiagramm",
        module="diagram_chart",
        snippet=":::chart type=bar\nÄpfel: 12\nBirnen: 7\n% Kirschen: 3\x01\n:::\n",
        empty_code="CH001",
        options=(
            BlockOptionSpec("type", "enum", frozenset({"bar", "pie", "box", "histogram", "scatter"}), False, "bar"),
            BlockOptionSpec("gaps", "enum", frozenset({"none", "values"}), False, "none"),
        ),
    ),
    DiagramBlockSpec(
        name="venn",
        title="Venn-Diagramm",
        module="diagram_venn",
        snippet=":::venn\nA: 2, 4\nA B: 6\nB: %{3, 9}\x01\n:::\n",
        empty_code="VN001",
        keywords=("rest",),
        options=(BlockOptionSpec("variant", "enum", frozenset({"plain", "compare"}), False, "plain"),),
    ),
    DiagramBlockSpec(
        name="arrowdiagram",
        title="Pfeildiagramm",
        module="diagram_arrow",
        snippet=":::arrowdiagram left=x right=y\n1 -> 2\n2 -> 4\n% 3 -> 6\x01\n:::\n",
        empty_code="AR001",
        options=(
            BlockOptionSpec("left", "text", None, False, MISSING),
            BlockOptionSpec("right", "text", None, False, MISSING),
            BlockOptionSpec("kind", "enum", frozenset({"relation", "function"}), False, "relation"),
        ),
    ),
    DiagramBlockSpec(
        name="fractions",
        title="Bruchdarstellung",
        module="diagram_fractions",
        snippet=":::fractions shape=circle\n3/4\n% 2/3\x01\n:::\n",
        empty_code="FR001",
        options=(
            BlockOptionSpec("shape", "enum", frozenset({"circle", "bar"}), False, "circle"),
            BlockOptionSpec("filled", "boolean", None, False, True),
        ),
    ),
    DiagramBlockSpec(
        name="memorydiagram",
        title="Speicherbild",
        module="diagram_memory",
        snippet=":::memorydiagram\nreihung r: 3, 5, 7\nvariable x: %{5}\nreferenz p -> r\x01\n:::\n",
        empty_code="MM001",
        keywords=("reihung", "variable", "referenz", "stapel", "schlange"),
    ),
)

DIAGRAM_BLOCKS_BY_NAME = {spec.name: spec for spec in DIAGRAM_BLOCKS}
DIAGRAM_BLOCK_NAMES = frozenset(DIAGRAM_BLOCKS_BY_NAME)
DIAGRAM_HEADER_RE = re.compile(r"^\s*:::(?:" + "|".join(sorted(DIAGRAM_BLOCK_NAMES)) + r")(?=\s|$)")
"""Erkennt die Kopfzeile eines Diagrammblocks; dort stehen Zeilenmarker nach der Einrückung."""
