"""Tönung über genau einen Weg: Jede farbige Fläche hängt an `var(--tint)`.

Neue Flächen, die am Schalter „Flächen tönen“ vorbeilaufen, fallen hier auf. Was immer getönt
bleiben soll, steht in der einen `--tint: 1`-Regel in `assets/worksheet.css`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.styles.worksheet_design import COLOR_PROFILE_ORDER, build_design_css

CSS = Path(__file__).resolve().parents[1].joinpath("assets", "worksheet.css").read_text(encoding="utf-8")
NEUTRAL_VALUES = re.compile(
    r"^(none|transparent|white|black|currentColor|#fff|#ffffff|#000|#000000|url\(.*\)|var\(--(diagram-paper|diagram-ink|text-color|field|grid)[^)]*\)|repeating-linear-gradient.*)$",
    re.IGNORECASE,
)
SURFACE_RE = re.compile(r"(background(?:-color)?|fill)\s*:\s*([^;]+);")
TEXT_FILL_SELECTOR = re.compile(r"label|text|arrowhead|grid-point|grid-axis|numberline")
"""SVG-Text und Pfeilspitzen färben Schrift und Linien, keine Flächen."""


def _rules(css: str):
    """`(selektor, deklarationen)` aller Regeln, Kommentare entfernt."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return [(" ".join(m.group(1).split()), m.group(2)) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css)]


def _untied_surfaces(css: str) -> list[str]:
    """Flächen mit Farbe, die nicht über `var(--tint)` laufen."""
    found = []
    for selector, body in _rules(css):
        for prop, value in SURFACE_RE.findall(body):
            value = value.strip()
            if NEUTRAL_VALUES.match(value) or "var(--tint" in value or "fill-opacity: calc" in body and "var(--tint" in body:
                continue
            if prop == "fill" and TEXT_FILL_SELECTOR.search(selector):
                continue
            found.append(f"{selector} {{ {prop}: {value} }}")
    return found


def test_every_surface_in_the_stylesheet_follows_the_tint_switch():
    """Keine farbige Fläche im Stylesheet läuft am Schalter vorbei."""
    assert _untied_surfaces(CSS) == []


@pytest.mark.parametrize("profile", COLOR_PROFILE_ORDER)
def test_every_surface_in_the_profile_css_follows_the_tint_switch(profile):
    """Auch die vom Farbprofil erzeugten Flächen hängen am Schalter."""
    assert _untied_surfaces(build_design_css(profile, tint=True)) == []


def test_untinted_mode_only_sets_the_factor():
    """Der Schalter selbst ist eine einzige Variable."""
    tinted = build_design_css("indigo", tint=True)
    untinted = build_design_css("indigo", tint=False)
    from app.styles.worksheet_design import _UNTINTED_CSS

    assert "--tint: 0" in untinted and "--tint: 0" not in tinted
    assert len(untinted) - len(tinted) == len(_UNTINTED_CSS)
    assert _UNTINTED_CSS.count("{") == 1


def test_table_headers_and_meaningful_marks_always_stay_tinted():
    """Tabellenköpfe, Markierungen mit Bedeutung und der Versatz setzen `--tint: 1`."""
    rule = next(selector for selector, body in _rules(CSS) if "--tint: 1" in body)
    for selector in (
        ".answer-table th",
        ".diagram-table th",
        ".evaluation-table th",
        "mark",
        ".cw-cell-code",
        ".crossword-code-letter",
        ".diagram-keep-tint",
        ".diagram-offset",
        ".diagram-fill",
    ):
        assert selector in rule, selector
