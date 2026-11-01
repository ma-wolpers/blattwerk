"""Tests für `:::classdiagram` (Vorlage: GO Informatik S. 7)."""

from __future__ import annotations

from app.core.blatt_validator import inspect_markdown_text
from app.core.diagram_block_dispatch import render_diagram_block
from app.core.diagram_class import parse
from diagram_go_examples import GO_CLASS_DIAGRAM

HEAD = "---\nTitel: T\nFach: I\nThema: X\n---\n"


def _codes(content: str) -> list[str]:
    """Validator-Codes eines Dokuments mit genau diesem Block."""
    text = f"{HEAD}:::classdiagram\n{content}\n:::\n"
    return [d.code for d in inspect_markdown_text(text, document_type="worksheet").diagnostics]


def test_go_example_parses_without_issues_or_warnings():
    """Das GO-Beispiel ist fehlerfrei: Sichtbarkeit, Konstruktoren und `...` sind gültig."""
    model, issues = parse(GO_CLASS_DIAGRAM)
    assert not issues
    assert list(model.nodes) == ["Person", "Adresse", "Schueler", "Lehrer", "p42", "adr37"]
    assert not [code for code in _codes(GO_CLASS_DIAGRAM) if code.startswith("CD")]


def test_members_are_sorted_into_compartments_and_dots_stay():
    """Attribute vor Operationen; `...` bleibt im Fach, in dem es steht."""
    model, _ = parse(GO_CLASS_DIAGRAM)
    person = model.nodes["Person"]
    assert [cell.text for cell in person.attributes][-1] == "..."
    assert [cell.text for cell in person.operations][0] == "c Person()"
    assert [cell.text for cell in person.operations][-1] == "..."
    assert model.nodes["p42"].is_object
    assert model.nodes["p42"].title.text == "p42 : Person"


def test_relations_distinguish_inheritance_and_association():
    """`-|>` ist Vererbung, `-` Assoziation, auch als Selbstassoziation."""
    model, _ = parse(GO_CLASS_DIAGRAM)
    found = {(r.source, r.target): r.inherits for r in model.relations}
    assert found[("Schueler", "Person")] is True
    assert found[("Person", "Adresse")] is False
    assert found[("Person", "Person")] is False


def test_render_keeps_identifier_underscores_and_member_signs():
    """`a_str` löst kein Kursiv aus, `- id` wird keine Liste, das Dreieck ist hohl."""
    html = render_diagram_block("classdiagram", {}, GO_CLASS_DIAGRAM)
    assert "a_str, a_plz, a_ort" in html
    assert "<ul" not in html and "<em" not in html
    assert "- id: Ganzzahl" in html
    assert "diagram-shape" in html
    assert "<foreignObject" in html


def test_render_is_deterministic_and_empty_block_renders_nothing():
    """Gleiche Eingabe, gleiche Ausgabe; ohne Inhalt kein HTML."""
    assert render_diagram_block("classdiagram", {}, GO_CLASS_DIAGRAM) == render_diagram_block("classdiagram", {}, GO_CLASS_DIAGRAM)
    assert render_diagram_block("classdiagram", {}, " \n") == ""


def test_gaps_hide_member_in_worksheet_and_show_it_in_solution():
    """`%` nach der Einrückung macht ein Mitglied zur Lücke."""
    content = "klasse A\n    % - geheim: Ganzzahl\n    - offen: Ganzzahl"
    worksheet = render_diagram_block("classdiagram", {}, content, include_solutions=False)
    solution = render_diagram_block("classdiagram", {}, content, include_solutions=True)
    assert "diagram-hidden" in worksheet and "diagram-gap" in worksheet
    assert "diagram-hidden" not in solution and "geheim" in solution


def test_validator_reports_structure_errors_and_go_warnings():
    """Struktur als Fehler, GO-Abweichungen als Warnung."""
    assert "CD001" in _codes("")
    assert "CD002" in _codes("A B C")
    assert "CD003" in _codes("    - x: Ganzzahl")
    assert "CD004" in _codes("klasse A\nklasse A")
    assert "CD005" in _codes("klasse A\nA - B")
    assert "CD006" in _codes("klasse A\n    x: Ganzzahl")
    assert "CD007" in _codes("klasse A\nklasse B\nA - B: kennt")


def test_comment_lines_do_not_count_and_html_is_escaped():
    """Kommentare entfallen, `<` in Typen bleibt Text."""
    model, issues = parse("klasse A\n%%Notiz%%\n    - x: Liste<Ganzzahl>")
    assert not issues
    assert len(model.nodes["A"].attributes) == 1
    assert "Liste&lt;Ganzzahl&gt;" in render_diagram_block("classdiagram", {}, "klasse A\n    - x: Liste<Ganzzahl>")
