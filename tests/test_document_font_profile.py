"""`font_profile` im Frontmatter (Wunschliste Schritt 5a).

Gueltiger Dokumentwert -> steuert Vorschau und Export; fehlend -> App-Standard;
ungueltig -> Warnung FM012 mit gueltigen Namen und App-Standard, Build laeuft weiter.
"""

from __future__ import annotations

import pytest

from app.core.blatt_kern_layout_render import render_html
from app.core.blatt_validator import has_blocking_diagnostics, inspect_markdown_text
from app.core.document_font import resolve_document_font_profile

HEAD = "---\nTitel: T\nFach: M\nThema: X\n{extra}---\n:::task\nA\n:::\n"


@pytest.mark.parametrize(
    ("meta", "app_default", "expected", "has_problem"),
    [
        ({"font_profile": "comic_neue"}, "segoe", "comic_neue", False),
        ({"font_profile": " Arial "}, "segoe", "arial", False),
        ({}, "calibri", "calibri", False),
        ({"font_profile": ""}, "calibri", "calibri", False),
        ({"font_profile": "papyrus"}, "calibri", "calibri", True),
        ({}, "unbekannt", "segoe", False),
    ],
)
def test_resolution_order(meta, app_default, expected, has_problem):
    """Dokumentwert vor App-Standard; ungueltig faellt sichtbar zurueck."""
    profile, problem = resolve_document_font_profile(meta, app_default)
    assert profile == expected
    assert (problem is not None) is has_problem


def _codes(text):
    report = inspect_markdown_text(text, document_type="worksheet")
    return report, [d for d in report.diagnostics if d.code == "FM012"]


def test_invalid_value_is_a_non_blocking_warning_listing_valid_names():
    """FM012 ist eine Warnung mit den gueltigen Namen und blockiert den Build nicht."""
    report, fm012 = _codes(HEAD.format(extra="font_profile: papyrus\n"))
    assert len(fm012) == 1
    assert fm012[0].severity == "warning"
    assert "comic_neue" in fm012[0].message
    assert not has_blocking_diagnostics([d for d in report.diagnostics if d.code == "FM012"])


@pytest.mark.parametrize("value", ["comic_neue", "segoe", "Andika"])
def test_valid_values_produce_no_warning(value):
    """Gueltige Profile (auch mitgelieferte, gross geschrieben) erzeugen keine Diagnose."""
    _, fm012 = _codes(HEAD.format(extra=f"font_profile: {value}\n"))
    assert fm012 == []


def _base_font(html):
    return html.split("--font-family-base:", 1)[1].split(";", 1)[0].strip()


def test_render_uses_document_value_over_app_choice():
    """Das Dokument-Profil schlaegt die uebergebene App-Auswahl."""
    html = render_html({"Titel": "T", "font_profile": "comic_neue"}, [("task", {}, "A")], font_profile="segoe")
    assert _base_font(html).startswith("'Comic Neue'")
    assert "@font-face" in html


def test_render_without_document_value_uses_app_choice():
    """Ohne Dokumentwert gilt die App-Auswahl, und es wird keine Schriftdatei eingebettet."""
    html = render_html({"Titel": "T"}, [("task", {}, "A")], font_profile="calibri")
    assert _base_font(html).startswith("Calibri")
    assert "@font-face" not in html


def test_render_with_invalid_document_value_falls_back_to_app_choice():
    """Ein ungueltiger Dokumentwert faellt auf die App-Auswahl zurueck (Warnung kommt vom Validator)."""
    html = render_html({"Titel": "T", "font_profile": "papyrus"}, [("task", {}, "A")], font_profile="calibri")
    assert _base_font(html).startswith("Calibri")
