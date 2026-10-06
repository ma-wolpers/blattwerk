"""`:::solution mode/show` ist veraltet und wird ignoriert (Phase 8)."""

import pytest

from app.core.blatt_kern_shared_blocks import should_render_block
from app.core.blatt_validator import inspect_markdown_text
from app.core.completion_catalogs import get_completion_options_for_block

HEAD = "---\ndocument_type: worksheet\nTitel: T\nFach: M\nThema: X\n---\n"


@pytest.mark.parametrize("option", ["mode=worksheet", "mode=solution", "show=worksheet", "show=both"])
def test_solution_mode_and_show_warn_op004(option):
    diagnostics = inspect_markdown_text(HEAD + f":::solution {option}\nX\n:::\n").diagnostics
    codes = [d.code for d in diagnostics]
    assert "OP004" in codes and "OP001" not in codes and "OP003" not in codes


@pytest.mark.parametrize("options", [{"mode": "worksheet"}, {"show": "worksheet"}, {"show": "both"}, {}])
def test_solution_is_only_visible_in_solution_version(options):
    assert should_render_block("solution", options, include_solutions=False) is False
    assert should_render_block("solution", options, include_solutions=True) is True
    assert should_render_block("solution", options, include_solutions=True, document_type="presentation") is False


def test_other_blocks_keep_their_block_mode_option():
    assert should_render_block("info", {"mode": "solution"}, include_solutions=False) is False
    assert should_render_block("info", {"mode": "solution"}, include_solutions=True) is True


def test_completion_no_longer_offers_mode_or_show_for_solution():
    names = set(get_completion_options_for_block("solution"))
    assert "mode" not in names and "show" not in names and "target" in names
