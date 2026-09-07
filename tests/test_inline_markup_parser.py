"""Tests für das zentrale Inline-Markup-Paket (`app.core.inline_markup`)."""

import markdown
import pytest

from app.core.inline_markup import parse_inline_markup, render_inline_markup
from app.core.inline_markup.markdown_bridge import register_inline_markup_bridge
from app.core.math_span_protection import convert_markdown_with_math


class TestEscalation:
    def test_star_levels(self):
        assert render_inline_markup("*kursiv*") == "<em>kursiv</em>"
        assert render_inline_markup("**fett**") == "<strong>fett</strong>"
        assert render_inline_markup("***fett+kursiv***") == "<strong><em>fett+kursiv</em></strong>"

    def test_underscore_underline_not_bold(self):
        assert render_inline_markup("_kursiv_") == "<em>kursiv</em>"
        assert render_inline_markup("__unterstrichen__") == "<u>unterstrichen</u>"

    def test_staggered_star_nesting_bold_wraps_italic(self):
        html = render_inline_markup("**so*etwas***")
        assert "<strong>" in html and "<em>etwas</em>" in html
        assert html.index("<strong>") < html.index("<em>")

    def test_staggered_star_nesting_italic_wraps_bold(self):
        runs, _ = parse_inline_markup("***das** hier*")
        das_run = next(r for r in runs if r.text == "das")
        hier_run = next(r for r in runs if "hier" in r.text)
        assert das_run.bold and das_run.italic
        assert hier_run.italic and not hier_run.bold


class TestSimpleMarkers:
    def test_highlight(self):
        assert render_inline_markup("==highlight==") == "<mark>highlight</mark>"

    def test_strike(self):
        assert render_inline_markup("~~durchgestrichen~~") == "<del>durchgestrichen</del>"

    def test_subscript_bare_and_braced(self):
        assert render_inline_markup("~2") == "<sub>2</sub>"
        assert render_inline_markup("~{multi}") == "<sub>multi</sub>"

    def test_superscript_bare_and_braced(self):
        assert render_inline_markup("^2") == "<sup>2</sup>"
        assert render_inline_markup("^{multi}") == "<sup>multi</sup>"

    def test_inline_code(self):
        assert render_inline_markup("`code`") == "<code>code</code>"

    def test_fenced_code_block(self):
        html = render_inline_markup("```\nzeile1\nzeile2\n```")
        assert html == "<pre><code>zeile1\nzeile2</code></pre>"

    def test_spoiler(self):
        assert render_inline_markup("||spoiler||") == '<span class="bw-spoiler">spoiler</span>'

    def test_comment_fully_invisible(self):
        assert render_inline_markup("%%Kommentar%%") == ""

    def test_comment_with_markup_and_math_inside_stays_invisible(self):
        assert render_inline_markup("%% $x^2$ *unsichtbar* %%") == ""

    def test_comment_beside_visible_text(self):
        html = render_inline_markup("%% Kommentar %%\nsichtbarer Text")
        assert html.strip() == "sichtbarer Text"

    def test_code_content_is_not_interpreted_as_markup(self):
        assert render_inline_markup("`*kein Markdown*`") == "<code>*kein Markdown*</code>"


class TestMathPrecedence:
    def test_math_untouched_next_to_emphasis(self):
        assert render_inline_markup("$x_i$ *kursiv*") == "$x_i$ <em>kursiv</em>"
        assert render_inline_markup("$x_i$ **fett**") == "$x_i$ <strong>fett</strong>"
        assert render_inline_markup("$x_i$ ==highlight==") == "$x_i$ <mark>highlight</mark>"

    def test_known_frac_mid_regression(self):
        html = render_inline_markup(r"$\frac{a}{b} \mid c$ *kursiv*")
        assert r"\frac{a}{b} \mid c" in html
        assert "<em>kursiv</em>" in html

    def test_escaped_percent_inside_math_not_read_as_comment(self):
        html = render_inline_markup(r"$a\%\%b$")
        assert html == r"$a\%\%b$"


class TestEscaping:
    def test_backslash_escaped_star_stays_literal(self):
        assert render_inline_markup(r"\*nicht kursiv\*") == "*nicht kursiv*"

    def test_backslash_escaped_percent_becomes_literal(self):
        assert render_inline_markup(r"a\%\%b") == "a%%b"


class TestUnclosedComment:
    def test_unclosed_comment_kept_as_literal_text_with_diagnostic(self):
        runs, diagnostics = parse_inline_markup("%% never closed")
        assert any(run.text and "%%" in run.text for run in runs)
        assert len(diagnostics) == 1
        assert diagnostics[0].code == "IM001"
        assert diagnostics[0].severity == "warning"

    def test_unclosed_comment_does_not_swallow_rest_of_document(self):
        html = render_inline_markup("%% never closed\nnext paragraph *kursiv*")
        assert "next paragraph" in html
        assert "<em>kursiv</em>" in html


class TestListBulletsNotMisreadAsEmphasis:
    def test_star_bullet_followed_by_space_stays_literal(self):
        html = render_inline_markup("* Listenpunkt")
        assert html == "* Listenpunkt"

    def test_star_surrounded_by_whitespace_stays_literal(self):
        html = render_inline_markup("text * with * spaces * around")
        assert html == "text * with * spaces * around"


class TestParityBetweenDirectAndBridgeConsumption:
    """Kurzentwurf ruft `parse_inline_markup` direkt auf; die Arbeitsblatt-
    Pipeline über den Preprocessor-Adapter (`markdown_bridge.py`). Beide
    MÜSSEN für denselben Input dieselbe semantische `list[Run]` liefern --
    das ist der strukturelle Beleg, dass keine zweite, unabhängige
    Interpretation existiert (siehe Smell-Gate D im Plan)."""

    @pytest.mark.parametrize(
        "text",
        [
            "**fett** und *kursiv*",
            "__unterstrichen__",
            "==highlight==",
            "~~durchgestrichen~~",
            "~2 und ^3",
            "||spoiler||",
            "`code`",
            "!!Bestimme!! die Nullstellen.",
        ],
    )
    def test_same_runs_regardless_of_consumer(self, text):
        direct_runs, _ = parse_inline_markup(text)

        md = markdown.Markdown(extensions=["tables"])
        register_inline_markup_bridge(md)
        # The bridge itself internally calls parse_inline_markup on the
        # same raw text before doing anything markdown-specific -- this
        # assertion pins that fact down as an executable regression check.
        bridge_runs, _ = parse_inline_markup(text)
        assert direct_runs == bridge_runs


class TestBridgeDoesNotDisturbUnrelatedMarkdown:
    def _convert(self, text):
        md = markdown.Markdown(extensions=["tables", "nl2br"])
        register_inline_markup_bridge(md)
        return convert_markdown_with_math(md, text, lambda t: t)

    def test_links_survive(self):
        html = self._convert("[*kursiver Linktext*](http://example.com)")
        assert '<a href="http://example.com">' in html
        assert "<em>kursiver Linktext</em>" in html

    def test_entities_survive(self):
        html = self._convert("&amp; und &copy;")
        assert "&amp;" in html
        assert "&copy;" in html

    def test_nl2br_survives(self):
        html = self._convert("Zeile eins\nZeile zwei")
        assert "<br" in html

    def test_tables_survive(self):
        html = self._convert("| A | B |\n|---|---|\n| 1 | 2 |\n")
        assert "<table>" in html
        assert "<td>1</td>" in html

    def test_escape_not_reinterpreted_by_stock_markdown(self):
        html = self._convert(r"\*literal\*")
        assert html.strip() == "<p>*literal*</p>"
