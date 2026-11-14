"""Lösungen pro Block in Präsentationen, typabhängiges `mode`, Verfügbarkeitstabelle.

Nutzerentscheidung 2026-11-10: Eine `.pbw` ist Aufgabenblatt und Lösung
zugleich -- jeder Block erscheint, auch `:::solution`. `mode` wählt nur an
lösungsfähigen Blöcken (Antwort-/Diagrammblöcke), ob ihre Lösungen
eingetragen sind (Standard leer); an anderen Blöcken ist es dort veraltet
(`OP004`). Arbeitsblatt und Klausur behalten die Sichtbarkeit je Fassung.
"""

from pathlib import Path

import pytest

from app.core.blatt_kern_layout_render import render_html
from app.core.blatt_validator import inspect_markdown_text
from app.core.blatt_validator_constants import BLOCK_OPTION_SPECS
from app.core.block_availability import BLOCK_AVAILABILITY
from app.core.block_mode_policy import SOLUTION_VARIANT_BLOCK_TYPES, deprecated_ignored_options
from app.core.completion_catalogs import get_completion_options_for_block
from app.core.document_type_registry import (
    DOCUMENT_TYPE_SPECS,
    SOLUTION_DISPLAY_NONE,
    SOLUTION_DISPLAY_PER_BLOCK,
    SOLUTION_DISPLAY_VERSION,
    solutions_per_block,
    solutions_renderable,
)

META = {"Titel": "T", "Fach": "M", "Thema": "X"}
APP_CORE = Path(__file__).resolve().parents[1] / "app" / "core"


def _head(document_type):
    return f"---\ndocument_type: {document_type}\nTitel: T\nFach: M\nThema: X\n---\n"


def _codes(document_type, body):
    return [d.code for d in inspect_markdown_text(_head(document_type) + body, document_type=document_type).diagnostics]


def _presentation_html(blocks):
    return render_html(META, blocks, include_solutions=False, document_type="presentation")


# -- Registry ---------------------------------------------------------------


def test_registry_solution_display_per_type():
    displays = {spec.id: spec.solution_display for spec in DOCUMENT_TYPE_SPECS}
    assert displays["worksheet"] == displays["exam"] == SOLUTION_DISPLAY_VERSION
    assert displays["presentation"] == SOLUTION_DISPLAY_PER_BLOCK
    assert {displays[t] for t in ("kurzentwurf", "schild", "markdown")} == {SOLUTION_DISPLAY_NONE}
    assert not solutions_renderable("presentation") and solutions_per_block("presentation")
    assert solutions_renderable("worksheet") and not solutions_per_block("worksheet")


# -- Rendern in Präsentationen ------------------------------------------------


def test_presentation_shows_solution_block_in_solution_design():
    html = _presentation_html([("solution", {}, "SolutionText")])
    assert "SolutionText" in html
    assert "class='solution'" in html


def test_presentation_answer_block_is_empty_without_mode_and_filled_with_mode_solution():
    empty = _presentation_html([("cloze", {"gap": "fixed"}, "Text {{AlphaGap}} hier.")])
    filled = _presentation_html([("cloze", {"gap": "fixed", "mode": "solution"}, "Text {{BetaGap}} hier.")])
    explicit_worksheet = _presentation_html([("cloze", {"gap": "fixed", "mode": "worksheet"}, "Text {{GammaGap}} hier.")])
    assert "AlphaGap" not in empty
    assert "BetaGap" in filled
    assert "GammaGap" not in explicit_worksheet


def test_presentation_shows_blocks_whose_mode_has_no_effect():
    html = _presentation_html([("info", {"mode": "solution"}, "InfoSol"), ("material", {"mode": "worksheet"}, "MatWs")])
    assert "InfoSol" in html and "MatWs" in html


def test_presentation_task_never_shows_percent_parts():
    html = _presentation_html([("task", {}, "Aufgabe %{GeheimTeil}")])
    assert "GeheimTeil" not in html


# -- Arbeitsblatt bleibt unverändert -----------------------------------------


@pytest.mark.parametrize("include_solutions", [False, True])
def test_worksheet_keeps_visibility_per_version(include_solutions):
    blocks = [
        ("material", {"mode": "solution"}, "NurLoesung"),
        ("task", {}, "Aufgabe"),
        ("subtask", {"mode": "worksheet"}, "NurBlatt"),
        ("cloze", {"gap": "fixed"}, "Text {{DeltaGap}} hier."),
        ("solution", {}, "LoesungsText"),
    ]
    html = render_html(META, blocks, include_solutions=include_solutions, document_type="worksheet")
    assert ("NurLoesung" in html) is include_solutions
    assert ("NurBlatt" in html) is not include_solutions
    assert ("DeltaGap" in html) is include_solutions
    assert ("LoesungsText" in html) is include_solutions


# -- Validator ------------------------------------------------------------------


def test_op004_for_mode_on_non_variant_blocks_only_in_presentations():
    body = ":::info mode=solution\nX\n:::\n\n:::task mode=worksheet\nY\n:::\n"
    assert _codes("presentation", body).count("OP004") == 2
    assert "OP004" not in _codes("worksheet", body)


def test_no_op004_for_mode_on_answer_and_diagram_blocks_in_presentations():
    body = ":::cloze gap=fixed mode=solution\nText {{a}}.\n:::\n"
    assert "OP004" not in _codes("presentation", body)


def test_an055_for_percent_parts_in_presentation_tasks():
    body = ":::task\nRechne %{42}\n:::\n"
    assert "AN055" in _codes("presentation", body)
    assert "AN055" not in _codes("worksheet", body)
    assert "AN055" not in _codes("presentation", ":::task\nRechne\n:::\n")


def test_availability_codes_from_one_table():
    body = ":::help\nTipp\n:::\n\n:::expectation\nAnsatz (1P)\n:::\n\n:::evaluation:::\n"
    codes = _codes("presentation", body)
    assert {"BL012", "BL018", "EV002"} <= set(codes)
    worksheet_codes = _codes("worksheet", body)
    assert not {"BL012", "BL018", "EV002"} & set(worksheet_codes)
    assert {entry.block_type for entry in BLOCK_AVAILABILITY} == {"help", "evaluation", "operators", "expectation"}


# -- Editor-Vorschläge ----------------------------------------------------------


def test_completion_hides_mode_where_it_is_deprecated():
    assert "mode" not in get_completion_options_for_block("task", "presentation")
    assert "show" not in get_completion_options_for_block("info", "presentation")
    assert "mode" in get_completion_options_for_block("task", "worksheet")
    assert "mode" in get_completion_options_for_block("cloze", "presentation")
    assert "mode" in get_completion_options_for_block("task")


# -- Guardrails -------------------------------------------------------------------


def test_every_solution_variant_block_has_mode_in_spec():
    """Jeder lösungsfähige Block muss `mode` anbieten, sonst ist er in Präsentationen nie lösbar."""
    missing = [name for name in SOLUTION_VARIANT_BLOCK_TYPES if "mode" not in {o.name for o in BLOCK_OPTION_SPECS[name]}]
    assert missing == []


def test_deprecation_never_hides_mode_on_solution_variant_blocks():
    for name in SOLUTION_VARIANT_BLOCK_TYPES:
        assert "mode" not in deprecated_ignored_options(name, "presentation")


@pytest.mark.parametrize(
    "module",
    ["blatt_kern_shared_blocks.py", "blatt_validator_help.py", "help_cards_appendix.py", "blatt_validator_points.py"],
)
def test_solution_help_points_rules_use_registry_capabilities(module):
    """Keine Folien-Ersatzabfrage und keine eigene Typliste für Lösungen, Lernhilfen und Punkte."""
    source = (APP_CORE / module).read_text(encoding="utf-8")
    assert "has_slide_layout" not in source
    assert "POINTS_DOCUMENT_TYPES" not in source
