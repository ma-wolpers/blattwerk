from app.core.wordsearch_strategy import resolve_wordsearch_generation_strategy


def test_wordsearch_strategy_uses_balanced_defaults_when_missing():
    strategy = resolve_wordsearch_generation_strategy({})

    assert strategy.mode == "balanced"
    assert strategy.max_candidate_sizes == 140
    assert strategy.placement_attempts_per_size == 16
    assert strategy.max_candidates_per_word == 120


def test_wordsearch_strategy_uses_robust_preset():
    strategy = resolve_wordsearch_generation_strategy({"strategy": "robust"})

    assert strategy.mode == "robust"
    assert strategy.max_candidate_sizes == 220
    assert strategy.placement_attempts_per_size == 28


def test_wordsearch_strategy_applies_bounded_overrides():
    strategy = resolve_wordsearch_generation_strategy(
        {
            "strategy": "compact",
            "max_candidate_sizes": "9999",
            "placement_attempts": "0",
            "candidate_limit": "-5",
            "area_density_factor": "3.1",
            "min_grid_edge": "20",
            "longest_word_padding": "-1",
            "sqrt_padding": "120",
        }
    )

    assert strategy.mode == "compact"
    assert strategy.max_candidate_sizes == 600
    assert strategy.placement_attempts_per_size == 1
    assert strategy.max_candidates_per_word == 8
    assert strategy.area_density_factor == 2.5
    assert strategy.min_grid_edge == 12
    assert strategy.longest_word_padding == 0
    assert strategy.sqrt_padding == 40
