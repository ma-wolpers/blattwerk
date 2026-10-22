"""Tests für Parser und Validator von `:::struktogramm`.

Normative Vorlage sind die vier GO-Beispiele (`struktogramm_go_examples.py`):
sie müssen ohne jede Diagnose durchlaufen. Fehlerfälle prüfen je einen `SG`-Code.
"""

import pytest

from app.core.blatt_validator import inspect_markdown_text
from app.core.struktogramm_parse import Branch, Loop, Statement, Switch, parse_struktogramm
from app.core.struktogramm_validation import ends_with_return, validate_struktogramm_block
from struktogramm_go_examples import GO_EXAMPLE_3, GO_EXAMPLE_4, GO_EXAMPLES


def _codes(content, signature="f(x: Zahl): Zahl"):
    """Diagnosecodes eines Blocks mit gegebener Signatur (`None` = ohne Option)."""
    options = {} if signature is None else {"signature": signature}
    return [d.code for d in validate_struktogramm_block(0, "struktogramm", options, content)]


@pytest.mark.parametrize(("signature", "content"), GO_EXAMPLES)
def test_go_examples_have_no_diagnostics(signature, content):
    """Alle vier GO-Beispiele: keine Struktur-, Signatur-, Rückgabe- oder Parameterdiagnose."""
    assert _codes(content, signature) == []


def test_go_example_3_tree_shape():
    """Bsp. 3: Kopf- und Fußschleife, Auswahl mit leerem `sonst`."""
    elements, issues = parse_struktogramm(GO_EXAMPLE_3[1])
    assert issues == []
    kinds = [type(e).__name__ for e in elements]
    assert kinds == ["Statement", "Loop", "Statement", "Loop", "Statement"]
    foot = elements[3]
    assert foot.kind == "foot" and foot.text.text == "wiederhole bis anzahlRot > 30"
    head = foot.body[0]
    assert isinstance(head, Loop) and head.kind == "head" and head.text.text == "wiederhole 100-mal"
    switch = head.body[1]
    assert isinstance(switch, Switch)
    assert [c.value.text for c in switch.cases] == ["1", "2", "3", "4"]
    assert switch.default == []
    assert elements[0].cell.text.startswith("f ← leere")


def test_go_example_4_nested_branches():
    """Bsp. 4: `wenn` ohne `sonst` und verschachtelte Verzweigung im `sonst`."""
    elements, _ = parse_struktogramm(GO_EXAMPLE_4[1])
    first, _, second = elements
    assert isinstance(first, Branch) and not first.has_else and first.no == []
    assert isinstance(second, Branch) and second.has_else
    assert isinstance(second.no[-1], Branch)


def test_return_and_input_display_texts():
    """`rückgabe X` → „gib X zurück“, `eingabe x` → „lies x ein“."""
    elements, _ = parse_struktogramm("eingabe x\nrückgabe x")
    assert [(e.kind, e.cell.text) for e in elements] == [("input", "lies x ein"), ("return", "gib x zurück")]


def test_backslash_escapes_keyword():
    """`\\wenn …` ist eine Anweisung, keine Verzweigung."""
    elements, issues = parse_struktogramm("\\wenn es regnet, Schirm")
    assert issues == [] and isinstance(elements[0], Statement)
    assert elements[0].cell.text == "wenn es regnet, Schirm"


def test_markers_after_indentation():
    """`%` nach der Einrückung macht den Elementtext zur Lösung; `%{…}` einen Teil."""
    elements, _ = parse_struktogramm("wenn a\n    % rückgabe wahr\nrückgabe %{falsch}")
    hidden = elements[0].yes[0].cell.segments
    assert {s["show"] for s in hidden} == {"solution"}
    partial = elements[1].cell.segments
    assert [s["show"] for s in partial] == ["both", "solution", "both"]


@pytest.mark.parametrize(
    ("content", "code"),
    [
        ("wenn a\n    rückgabe 1\n  rückgabe 2", "SG001"),
        ("rückgabe 1\n    rückgabe 2", "SG002"),
        ("sonst\nrückgabe 1", "SG003"),
        ("wiederhole\n    x <- 1\nrückgabe x", "SG004"),
        ("solange x\nrückgabe x", "SG005"),
        ("auswahl x\nrückgabe x", "SG005"),
        ("wenn\n    rückgabe 1\nrückgabe x", "SG006"),
        ("auswahl x\n    rückgabe 1\nrückgabe x", "SG008"),
    ],
)
def test_structure_errors(content, code):
    """Jeder Strukturfehler liefert seinen Code (als Fehler)."""
    diagnostics = validate_struktogramm_block(0, "struktogramm", {"signature": "f(x: Zahl): Zahl"}, content)
    matching = [d for d in diagnostics if d.code == code]
    assert matching and matching[0].severity == "error"


def test_empty_block_and_missing_signature_warn():
    """Leerer Block (`SG007`) und fehlende Signatur (`SG020`) sind Warnungen."""
    assert _codes("") == ["SG007"]
    assert _codes("rückgabe 1", signature=None) == ["SG020"]


def test_invalid_signature_is_an_error():
    """Eine Signatur außerhalb der GO-Form ist ein Fehler mit ihrem Code."""
    diagnostics = validate_struktogramm_block(0, "struktogramm", {"signature": "f(a, b)"}, "rückgabe a")
    assert [(d.code, d.severity) for d in diagnostics] == [("SG012", "error")]


def test_return_without_return_type_is_an_error():
    """`rückgabe` bei Signatur ohne Rückgabetyp: `SG021`."""
    assert _codes("rückgabe x", signature="sortiere(x: Reihung)") == ["SG021"]


def test_missing_return_on_some_path_warns():
    """Rückgabe nur im wahr-Zweig: `SG022` (Warnung)."""
    assert _codes("wenn x > 0\n    rückgabe x") == ["SG022"]


def test_literal_gib_zurueck_gets_a_hint():
    """Wer `gib … zurück` als Anweisung schreibt, bekommt den Hinweis auf `rückgabe`."""
    diagnostics = validate_struktogramm_block(0, "struktogramm", {"signature": "f(x: Zahl): Zahl"}, "gib x zurück")
    assert "`rückgabe …`" in diagnostics[0].message


def test_unused_parameter_warns():
    """Ein Parameter, der nirgends vorkommt: `SG023`."""
    assert _codes("rückgabe 1", signature="f(x, y: Zahl): Zahl") == ["SG023"]


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("rückgabe 1", True),
        ("wenn a\n    rückgabe 1\nsonst\n    rückgabe 2", True),
        ("wenn a\n    rückgabe 1\nsonst", False),
        ("solange a\n    rückgabe 1", False),
        ("wiederhole\n    rückgabe 1\nbis a", True),
        ("auswahl a\n    fall 1\n        rückgabe 1\n    sonst\n        rückgabe 2", True),
        ("auswahl a\n    fall 1\n        rückgabe 1", False),
    ],
)
def test_ends_with_return_rules(content, expected):
    """Pfadregeln: Verzweigung beide Zweige, Auswahl inkl. `sonst`, Kopfschleife nie, Fußschleife Rumpf."""
    elements, _ = parse_struktogramm(content)
    assert ends_with_return(elements) is expected


def test_validator_hook_runs_for_alias_in_documents():
    """Im Gesamtvalidator greift die Prüfung auch für den Alias `structogram`."""
    text = "---\nTitel: T\nFach: Informatik\nThema: X\n---\n\n:::structogram\nrückgabe 1\n:::\n"
    codes = [d.code for d in inspect_markdown_text(text).diagnostics]
    assert "SG020" in codes and "BL001" not in codes
