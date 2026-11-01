"""Konsistenzprüfungen aller Blöcke: Widersprüche fallen auf, Sinnvolles bleibt still."""

from __future__ import annotations

import pytest

from app.core.blatt_validator import inspect_markdown_text
from app.core.diagram_block_dispatch import render_diagram_block
from app.core.diagram_term import evaluate
from app.core.diagram_term import parse as parse_term

HEAD = "---\nTitel: T\nFach: Mathematik\nThema: X\nshow_student_header: false\n---\n"
PAIR = 'left:\n  - "a"\n  - "b"\nright:\n  - "c"\n  - "d"\n'


def _codes(body: str) -> list[str]:
    """Validator-Codes eines Dokuments."""
    return [d.code for d in inspect_markdown_text(f"{HEAD}{body}\n", document_type="worksheet").diagnostics]


@pytest.mark.parametrize(
    ("code", "body"),
    [
        ("AN021", ":::mc\n- [ ] a\n- [ ] b\n:::"),
        ("AN022", ":::mc\n- [x] a\n- [ ] a\n:::"),
        ("AN023", ":::mc tf=true\n- [x] a\n:::"),
        ("AN025", ':::checkgrid\ncolumns:\n  - "r"\n  - "f"\nrows:\n  - text: "a"\n    correct: 5\n:::'),
        ("AN026", ':::checkgrid\ncolumns:\n  - "r"\n:::'),
        ("AN027", f':::matching layout=horizontal\n{PAIR}matches:\n  - "1-9"\n  - "2-1"\n:::'),
        ("AN028", f":::matching layout=horizontal\n{PAIR}:::"),
        ("AN029", f':::matching layout=horizontal\n{PAIR}matches:\n  - "1-2"\n:::'),
        ("AN030", f':::matching layout=horizontal\n{PAIR}matches:\n  - "1-1"\n  - "2-2"\n:::'),
        ("AN031", f':::matching layout=horizontal\n{PAIR}matches:\n  - "1-2"\n  - "2-1"\nworksheet_matches:\n  - "1-1"\n:::'),
        ("AN032", ':::table rows=1 cols=2\ncells:\n  - ["a", "b", "c"]\n:::'),
        ("AN032", ':::table rows=1 cols=1\ncells:\n  - ["a"]\n  - ["b"]\n:::'),
        ("AN033", ':::table cols=1\ncells:\n  - ["a"]\n:::'),
        ("AN049", ':::table rows=1 cols=2 column_headers="A|B|C"\ncells:\n  - ["a", "b"]\n:::'),
        ("AN049", ':::table rows=1 cols=1 row_headers="A|B"\ncells:\n  - ["a"]\n:::'),
        ("AN037", ":::numberline min=0 max=10 tick_step=1\nanswers:\n  - {value: 50}\n:::"),
        ("AN038", ":::numberline min=10 max=0\n:::"),
        ("AN039", ":::numberline min=0 max=10 tick_step=0\n:::"),
        ("AN040", ':::geometry scale=0.5cm width=10 height=10 axis=true origin="5,5"\npoints:\n  - {x: 99, y: 0}\n:::'),
        ("AN040", ":::geometry scale=0.5cm width=10 height=10\npoints:\n  - {col: 99, row: 1}\n:::"),
        ("AN041", ':::geometry scale=0.5cm width=10 height=10 axis=true origin="5,5"\nfunctions:\n  - {expr: "2*("}\n:::'),
        ("AN043", ":::wordsearch\n- ROM\n- ROM\n:::"),
        ("AN044", ":::wordsearch horizontal=false vertical=false diagonal=false\n- ROM\n:::"),
        ("AN045", ":::cloze\nNur Text.\n:::"),
        ("AN046", ":::cloze\nText {{ohne Ende\n:::"),
        ("AN047", ":::ordering\n- a\n:::"),
        ("AN048", ":::ordering\n- a\n- a\n:::"),
        ("AN050", ":::selfcheck\n:::"),
        ("AN051", ':::selfcheck label1="x"\n- a\n:::'),
        ("AN052", ":::mindmap\n:::"),
        ("AN053", ":::mindmap branches=99\nThema\n:::"),
        ("AN054", ":::task\nA\n:::\n\n:::help level=0\nx\n:::"),
        ("BL014", ':::columns cols=2 widths="1 2 3" :::\n\n:::nextcol :::\n\n:::endcolumns :::'),
        ("BL015", ":::subtask\nx\n:::"),
        ("BL016", ':::task title="Aufgabe 3"\nA\n:::'),
        ("OP006", ":::graph width=abc\nA - B\n:::"),
        ("OP006", ":::dots height=abc\n:::"),
        ("OP007", ":::lines rows=abc\n:::"),
        ("OP007", ":::lines rows=0\nx\n:::"),
        ("OP008", ":::graph binary=quatsch\nA - B\n:::"),
        ("OP002", ":::graph layout=quatsch\nA - B\n:::"),
        ("OP002", ":::chart type=quatsch\nA: 1\n:::"),
    ],
)
def test_existing_blocks_report_contradictions(code, body):
    """Jeder Widerspruch hat seinen Code."""
    assert code in _codes(body)


@pytest.mark.parametrize(
    "body",
    [
        ":::mc\n- [x] a\n- [ ] b\n:::",
        ":::mc tf=true correct=true\nAussage\n:::",
        ':::checkgrid\ncolumns:\n  - "r"\n  - "f"\nrows:\n  - text: "a"\n    correct: 2\n  - text: "ohne Wertung"\n:::',
        f':::matching layout=horizontal\n{PAIR}matches:\n  - "1-2"\n  - "2-1"\nworksheet_matches:\n  - "1-2"\n:::',
        ':::table rows=2 cols=2 column_headers="A|B" row_headers="x|y"\ncells:\n  - ["a", "b"]\n:::',
        ":::numberline min=0 max=10 tick_step=1\nanswers:\n  - {value: 10}\n:::",
        ':::geometry scale=0.5cm width=11 height=11 axis=true origin="5,5"\npoints:\n  - {x: 5, y: -5}\n:::',
        ":::cloze\nEin {{Wort}}.\n:::",
        ":::ordering\n- a\n- b\n:::",
        ":::selfcheck dual=true label1=x\n- a\n:::",
        ":::mindmap branches=12\nThema\n:::",
        ':::task title="Mathe 3"\nA\n:::',
        ":::graph width=70%\nA - B\n:::",
    ],
)
def test_sensible_input_stays_quiet(body):
    """Keine Fehlalarme: Randwerte und bewusst freie Angaben sind in Ordnung."""
    new_codes = {f"AN0{n}" for n in range(21, 55)} | {"BL014", "BL015", "BL016", "OP006", "OP007", "OP008"}
    assert not new_codes & set(_codes(body))


@pytest.mark.parametrize(
    ("code", "content", "block", "options"),
    [
        ("CD011", "klasse A\n    - x: Ganzzahl\n    - x: Ganzzahl", "classdiagram", ""),
        ("CD012", "klasse A\n    c B()", "classdiagram", ""),
        ("CD013", "klasse A\n    - b: B\nklasse B", "classdiagram", ""),
        ("CD014", "klasse A\nobjekt o : A\no -|> A", "classdiagram", ""),
        ("ER008", "entität A\n    __k__", "erdiagram", ""),
        ("ER009", "entität A\n    __k__\n    __k__", "erdiagram", ""),
        ("ST012", "start -> A\nA -> A: a", "statediagram", "kind=dfa output=X"),
        ("ST012", "start -> A\nA -> A: a", "statediagram", "kind=dfa stack=X"),
        ("ST013", "start -> A\nende: A\nA -> A: a / X", "statediagram", "kind=mealy"),
        ("ST014", "start -> A\nA -> A: a", "statediagram", "kind=dfa"),
        ("ST015", "start -> A\nA -> B", "statediagram", "kind=dfa"),
        ("ST015", "start -> A\nA -> A: a\nA -> A: a", "statediagram", ""),
        ("GR007", "A - B\nB - A", "graph", ""),
        ("GR008", "A - B\nB -> C", "graph", ""),
        ("NW004", "A - B\nB - A", "networkdiagram", ""),
        ("NW005", "A - A", "networkdiagram", ""),
        ("NW006", "A - B\nC: router", "networkdiagram", ""),
        ("SQ004", "B --> A: x", "sequencediagram", ""),
        ("SY004", "A = b\nA = c", "syntaxdiagram", ""),
        ("SY005", "A = B\nC = A", "syntaxdiagram", ""),
        ("SY006", 'A = "x"\nB = "y"', "syntaxdiagram", ""),
        ("LG005", "Q = A\nQ = B", "logicgates", ""),
        ("LG006", "Q = Q und A", "logicgates", ""),
        ("LG007", "Q = A", "logicgates", "gaps=true"),
        ("PB006", "A: 1/2\nA: 1/2", "probabilitytree", ""),
        ("TT005", "9^9^9", "termtree", ""),
        ("TT005", "2^0,5", "termtree", ""),
        ("TL004", "32.13.2000: x", "timeline", ""),
        ("CH007", "A: 1\nA: 2", "chart", "type=bar"),
        ("CH008", "A: 1, 2", "chart", "type=box"),
        ("CH009", "A: 50%\nB: 20%", "chart", "type=pie"),
        ("CH010", "0-10: 1\n10-30: 2", "chart", "type=histogram"),
        ("VN002", "rest A: 1\nA: 2\nB: 3", "venn", ""),
        ("FR004", "1000/2", "fractions", ""),
        ("MM006", "reihung r:", "memorydiagram", ""),
        ("MM007", "referenz p -> p", "memorydiagram", ""),
    ],
)
def test_diagram_blocks_report_contradictions(code, content, block, options):
    """Auch die Diagrammblöcke melden fachliche Widersprüche."""
    assert code in _codes(f":::{block} {options}\n{content}\n:::")


def test_snippets_of_all_diagram_blocks_stay_free_of_warnings():
    """Die Einfüge-Vorlagen sind selbst sauber."""
    from app.core.diagram_block_catalog import DIAGRAM_BLOCKS

    for spec in DIAGRAM_BLOCKS:
        codes = _codes(spec.snippet.replace("\x01", ""))
        assert not [code for code in codes if code[:2] in {spec.empty_code[:2]} and code != "SG020"], (spec.name, codes)


def test_huge_powers_do_not_block_rendering():
    """`9^9^9` bleibt ohne Ergebnis, statt das Rendern minutenlang aufzuhalten."""
    terms, _issues = parse_term("9^9^9")
    assert evaluate(terms[0].expression) is None
    assert render_diagram_block("termtree", {}, "9^9^9")
    assert render_diagram_block("fractions", {}, "1000000/2") == ""
