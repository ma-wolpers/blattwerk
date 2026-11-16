"""Emoji-Markierung im fertigen HTML (`emoji_markup.py`) und ihre Darstellung im S/W-Profil.

Jedes Emoji bekommt genau eine Klasse; die einzige CSS-Regel dazu hängt an dieser
Klasse (nicht mehr an `.task-work-symbol`). Dazu kommt die Build-Warnung `SC002`
für die Ampel-Skala im S/W-Profil.
"""

from __future__ import annotations

import re

import pytest

from app.core.blatt_kern_io_build import build_worksheet
from app.core.blatt_kern_layout_render import render_html
from app.core.blatt_kern_shared import parse_blocks
from app.core.emoji_markup import mark_emoji_glyphs
from app.core.selfcheck_bw_warning import append_bw_ampel_warnings
from app.styles.worksheet_design import EMOJI_GLYPH_CLASS, build_design_css

_OPEN = f'<span class="{EMOJI_GLYPH_CLASS}">'


def _marked(emoji: str) -> str:
    return f"{_OPEN}{emoji}</span>"


@pytest.mark.parametrize(
    "html, expected",
    [
        ("<p>Tipp 💡 hier</p>", f"<p>Tipp {_marked('💡')} hier</p>"),
        ("<h2>🚀 Expertenaufgabe</h2>", f"<h2>{_marked('🚀')} Expertenaufgabe</h2>"),
        ("<td>✅</td><td>🔴</td>", f"<td>{_marked('✅')}</td><td>{_marked('🔴')}</td>"),
        ("<p>a ⚖️ b</p>", f"<p>a {_marked('⚖️')} b</p>"),
        ("<p>👨‍👩‍👧!</p>", f"<p>{_marked('👨‍👩‍👧')}!</p>"),
        ("<p>👍🏽</p>", f"<p>{_marked('👍🏽')}</p>"),
        ("<p>🇩🇪</p>", f"<p>{_marked('🇩🇪')}</p>"),
        ("<p>1️⃣</p>", f"<p>{_marked('1️⃣')}</p>"),
    ],
)
def test_emojis_in_text_headings_and_tables_are_marked(html, expected):
    assert mark_emoji_glyphs(html) == expected


@pytest.mark.parametrize("text", ["☐ ☑ ☆", "↔ Pfeil", "⚖︎ Text"])
def test_text_style_symbols_stay_unmarked(text):
    """Textartige Zeichen (mc-Kästchen, Sterne-Skala, VS15) bleiben Text."""
    assert mark_emoji_glyphs(f"<p>{text}</p>") == f"<p>{text}</p>"


def test_head_attributes_svg_comments_and_math_stay_untouched():
    html = (
        "<html><head><title>🍎 Titel</title><style>/* 🍎 */</style></head>"
        "<body><p title='🍎'>x</p><!-- 🍎 --><svg><text>🍎</text></svg>"
        "<p>$\\text{🍎}$ und 🍎</p></body></html>"
    )
    result = mark_emoji_glyphs(html)
    assert result.count(_OPEN) == 1
    assert result.endswith(f"<p>$\\text{{🍎}}$ und {_marked('🍎')}</p></body></html>")


def test_marking_is_idempotent():
    once = mark_emoji_glyphs("<p>💡 und 🧪</p>")
    assert mark_emoji_glyphs(once) == once


def test_symbol_preset_targets_the_emoji_class_not_the_task_symbol():
    css = build_design_css(color_profile="bw")
    rule = re.search(rf"\.{EMOJI_GLYPH_CLASS} \{{(.*?)\}}", css, re.DOTALL)
    assert rule is not None and "grayscale(1)" in rule.group(1)
    assert not re.search(r"\.task-work-symbol \{[^}]*filter", css)


def test_rendered_worksheet_marks_task_symbols_selfcheck_and_heading_emojis():
    source = (
        "## Station 🧪\n\n"
        ":::task hint=tip work=single\nRechne 🍎 aus.\n:::\n\n"
        ":::selfcheck\n- Ich kann das.\n:::\n"
    )
    html = render_html({"Titel": "Test"}, parse_blocks(source), color_profile="bw")
    body = html.split("<body>", 1)[1]
    for emoji in ("🧪", "💡", "👤", "🍎", "\U0001F642"):
        assert _marked(emoji) in body, emoji
    assert re.search(r"<title>[^<]*</title>", html)


def _ampel_blocks():
    return parse_blocks(":::selfcheck scale=ampel\n- Ich kann das.\n:::\n")


@pytest.mark.parametrize("profile, expected", [("bw", 1), ("indigo", 0)])
def test_sc002_warns_only_for_ampel_in_bw(profile, expected):
    diagnostics = []
    append_bw_ampel_warnings(diagnostics_out=diagnostics, blocks=_ampel_blocks(), color_profile=profile)
    assert [d.code for d in diagnostics] == ["SC002"] * expected


def test_sc002_ignores_other_scales():
    diagnostics = []
    blocks = parse_blocks(":::selfcheck scale=smiley\n- Ich kann das.\n:::\n")
    append_bw_ampel_warnings(diagnostics_out=diagnostics, blocks=blocks, color_profile="bw")
    assert diagnostics == []


def test_build_worksheet_reports_sc002(tmp_path):
    source = tmp_path / "blatt.abw"
    source.write_text("---\nTitel: Test\n---\n\n:::selfcheck scale=ampel\n- Ich kann das.\n:::\n", encoding="utf-8")
    diagnostics = []
    build_worksheet(source, tmp_path / "blatt.html", color_profile="bw", diagnostics_out=diagnostics, block_on_critical=False)
    assert "SC002" in {d.code for d in diagnostics}
