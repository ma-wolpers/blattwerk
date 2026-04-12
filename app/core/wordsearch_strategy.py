"""Wordsearch generation strategy presets and option-based resolution."""

from __future__ import annotations

from dataclasses import dataclass


def _safe_int(value: object, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: object, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class WordsearchGenerationStrategy:
    """Explicit limits for deterministic wordsearch placement search."""

    mode: str
    min_grid_edge: int
    max_candidate_sizes: int
    placement_attempts_per_size: int
    max_candidates_per_word: int
    area_density_factor: float
    longest_word_padding: int
    sqrt_padding: int


_STRATEGY_PRESETS: dict[str, WordsearchGenerationStrategy] = {
    "compact": WordsearchGenerationStrategy(
        mode="compact",
        min_grid_edge=3,
        max_candidate_sizes=90,
        placement_attempts_per_size=10,
        max_candidates_per_word=80,
        area_density_factor=1.15,
        longest_word_padding=8,
        sqrt_padding=10,
    ),
    "balanced": WordsearchGenerationStrategy(
        mode="balanced",
        min_grid_edge=3,
        max_candidate_sizes=140,
        placement_attempts_per_size=16,
        max_candidates_per_word=120,
        area_density_factor=1.25,
        longest_word_padding=10,
        sqrt_padding=12,
    ),
    "robust": WordsearchGenerationStrategy(
        mode="robust",
        min_grid_edge=3,
        max_candidate_sizes=220,
        placement_attempts_per_size=28,
        max_candidates_per_word=180,
        area_density_factor=1.35,
        longest_word_padding=12,
        sqrt_padding=14,
    ),
}


def resolve_wordsearch_generation_strategy(options: dict[str, object]) -> WordsearchGenerationStrategy:
    """Resolve strategy preset and bounded overrides from answer options."""
    mode_raw = str(options.get("strategy") or "balanced").strip().lower()
    base = _STRATEGY_PRESETS.get(mode_raw, _STRATEGY_PRESETS["balanced"])

    min_grid_edge = _clamp(
        _safe_int(options.get("min_grid_edge"), base.min_grid_edge),
        1,
        12,
    )
    max_candidate_sizes = _clamp(
        _safe_int(options.get("max_candidate_sizes"), base.max_candidate_sizes),
        10,
        600,
    )
    placement_attempts_per_size = _clamp(
        _safe_int(options.get("placement_attempts"), base.placement_attempts_per_size),
        1,
        100,
    )
    max_candidates_per_word = _clamp(
        _safe_int(options.get("candidate_limit"), base.max_candidates_per_word),
        8,
        1000,
    )
    area_density_factor = max(
        0.8,
        min(2.5, _safe_float(options.get("area_density_factor"), base.area_density_factor)),
    )
    longest_word_padding = _clamp(
        _safe_int(options.get("longest_word_padding"), base.longest_word_padding),
        0,
        40,
    )
    sqrt_padding = _clamp(
        _safe_int(options.get("sqrt_padding"), base.sqrt_padding),
        0,
        40,
    )

    return WordsearchGenerationStrategy(
        mode=base.mode,
        min_grid_edge=min_grid_edge,
        max_candidate_sizes=max_candidate_sizes,
        placement_attempts_per_size=placement_attempts_per_size,
        max_candidates_per_word=max_candidates_per_word,
        area_density_factor=area_density_factor,
        longest_word_padding=longest_word_padding,
        sqrt_padding=sqrt_padding,
    )
