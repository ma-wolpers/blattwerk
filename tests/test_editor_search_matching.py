from app.ui.blatt_ui_editor_search import (
    _find_all_matches,
    _resolve_initial_match_index,
    _resolve_next_match_index,
)


# --- _find_all_matches -------------------------------------------------

def test_find_all_matches_empty_query_returns_no_matches():
    assert _find_all_matches("hello world", "", case_sensitive=False) == []


def test_find_all_matches_case_insensitive_by_default():
    assert _find_all_matches("Hello hello HELLO", "hello", case_sensitive=False) == [
        (0, 5),
        (6, 11),
        (12, 17),
    ]


def test_find_all_matches_case_sensitive_only_matches_exact_case():
    assert _find_all_matches("Hello hello HELLO", "hello", case_sensitive=True) == [(6, 11)]


def test_find_all_matches_no_match_returns_empty_list():
    assert _find_all_matches("hello world", "xyz", case_sensitive=False) == []


def test_find_all_matches_is_literal_not_regex():
    # "." und "*" sollen nicht als Regex-Metazeichen interpretiert werden.
    text = "3.14 is not 3x14"
    assert _find_all_matches(text, "3.14", case_sensitive=False) == [(0, 4)]


def test_find_all_matches_overlapping_occurrences_do_not_overlap_in_result():
    # "aaa" mit Suchbegriff "aa" -> nicht ueberlappende Treffer (0,2) und (2,4) wie
    # bei klassischen Editor-Suchfunktionen ueblich (kein Rueckschritt in bereits
    # konsumierten Text).
    assert _find_all_matches("aaaa", "aa", case_sensitive=False) == [(0, 2), (2, 4)]


def test_find_all_matches_finds_match_at_end_of_text():
    assert _find_all_matches("hello world", "world", case_sensitive=False) == [(6, 11)]


# --- _resolve_next_match_index -----------------------------------------

def test_resolve_next_match_index_no_matches_returns_none():
    assert _resolve_next_match_index(0, None, 1) is None
    assert _resolve_next_match_index(0, 0, 1) is None


def test_resolve_next_match_index_forward_without_current_starts_at_first():
    assert _resolve_next_match_index(5, None, 1) == 0


def test_resolve_next_match_index_backward_without_current_starts_at_last():
    assert _resolve_next_match_index(5, None, -1) == 4


def test_resolve_next_match_index_forward_advances_by_one():
    assert _resolve_next_match_index(5, 1, 1) == 2


def test_resolve_next_match_index_backward_steps_back_by_one():
    assert _resolve_next_match_index(5, 1, -1) == 0


def test_resolve_next_match_index_forward_wraps_at_end():
    assert _resolve_next_match_index(3, 2, 1) == 0


def test_resolve_next_match_index_backward_wraps_at_start():
    assert _resolve_next_match_index(3, 0, -1) == 2


def test_resolve_next_match_index_single_match_cycles_to_itself():
    assert _resolve_next_match_index(1, 0, 1) == 0
    assert _resolve_next_match_index(1, 0, -1) == 0


# --- _resolve_initial_match_index --------------------------------------

def test_resolve_initial_match_index_no_matches_returns_none():
    assert _resolve_initial_match_index([], 5) is None


def test_resolve_initial_match_index_picks_first_match_at_or_after_cursor():
    matches = [(0, 3), (10, 13), (20, 23)]
    assert _resolve_initial_match_index(matches, 5) == 1


def test_resolve_initial_match_index_cursor_exactly_on_match_start_picks_it():
    matches = [(0, 3), (10, 13), (20, 23)]
    assert _resolve_initial_match_index(matches, 10) == 1


def test_resolve_initial_match_index_wraps_to_first_when_cursor_past_all_matches():
    matches = [(0, 3), (10, 13)]
    assert _resolve_initial_match_index(matches, 999) == 0


def test_resolve_initial_match_index_cursor_before_all_matches_picks_first():
    matches = [(5, 8), (10, 13)]
    assert _resolve_initial_match_index(matches, 0) == 0
