"""`:::structogram` als Diagrammblock: bündelt Renderer, Parser und Prüfungen (Modulvertrag)."""

from __future__ import annotations

from .answer_special_struktogramm import estimate_struktogramm_weight as estimate_weight
from .answer_special_struktogramm import render_struktogramm_block as render
from .struktogramm_parse import parse_struktogramm as parse
from .struktogramm_validation import check_structogram as check

__all__ = ["check", "estimate_weight", "parse", "render"]
