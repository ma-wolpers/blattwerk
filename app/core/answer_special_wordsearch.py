"""Wordsearch answer renderer and grid generation helpers."""

from __future__ import annotations

import random
import re
from html import escape

from .answer_special_shared import _as_text_list, _option_is_enabled, _safe_int
from .wordsearch_strategy import resolve_wordsearch_generation_strategy


def _normalize_wordsearch_token(word):
    """Normalisiert Wörter auf ein großgeschriebenes Buchstaben-Token."""
    if word is None:
        return ""

    text = str(word).strip()
    text = text.replace("ß", "ss").replace("ẞ", "SS")
    text = re.sub(r"[^A-Za-zÄÖÜäöü]", "", text)
    return text.upper()


def parse_wordsearch_words(options, content):
    """Sammelt und dedupliziert Wortlisten aus Blockinhalt und Optionen."""
    words = []

    for raw_line in (content or "").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        bullet_match = re.match(r"^[-*+]\s+(.*)$", stripped)
        candidate = bullet_match.group(1).strip() if bullet_match else stripped

        for part in re.split(r"[,;|]", candidate):
            normalized = _normalize_wordsearch_token(part)
            if normalized:
                words.append(normalized)

    option_words = _as_text_list(options.get("words") or options.get("word_list"))
    for part in option_words:
        normalized = _normalize_wordsearch_token(part)
        if normalized:
            words.append(normalized)

    unique_words = []
    seen = set()
    for word in words:
        if word in seen:
            continue
        seen.add(word)
        unique_words.append(word)

    return unique_words


def _parse_min_wordsearch_size(options):
    """Liest Mindestgröße als `(rows, cols)` aus Wordsearch-Optionen."""
    min_rows = max(1, _safe_int(options.get("min_rows") or options.get("rows"), 0))
    min_cols = max(1, _safe_int(options.get("min_cols") or options.get("cols"), 0))

    size_raw = options.get("min_size") or options.get("size") or options.get("min")
    if size_raw:
        text = str(size_raw).strip().lower().replace("×", "x")
        pair_match = re.fullmatch(r"(\d+)\s*x\s*(\d+)", text)
        single_match = re.fullmatch(r"(\d+)", text)

        if pair_match:
            min_rows = max(min_rows, int(pair_match.group(1)))
            min_cols = max(min_cols, int(pair_match.group(2)))
        elif single_match:
            value = int(single_match.group(1))
            min_rows = max(min_rows, value)
            min_cols = max(min_cols, value)

    return max(1, min_rows), max(1, min_cols)


def _wordsearch_candidate_positions(grid, word, directions):
    """Ermittelt alle gültigen Startpositionen für ein Wort im Raster."""
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    candidates = []

    for d_row, d_col in directions:
        for start_row in range(rows):
            for start_col in range(cols):
                end_row = start_row + d_row * (len(word) - 1)
                end_col = start_col + d_col * (len(word) - 1)
                if end_row < 0 or end_row >= rows or end_col < 0 or end_col >= cols:
                    continue

                overlap = 0
                valid = True
                for index, letter in enumerate(word):
                    row = start_row + d_row * index
                    col = start_col + d_col * index
                    cell_value = grid[row][col]
                    if cell_value is None:
                        continue
                    if cell_value != letter:
                        valid = False
                        break
                    overlap += 1

                if not valid:
                    continue

                candidates.append((overlap, start_row, start_col, d_row, d_col))

    return candidates


def _wordsearch_place_word(grid, fill_counts, word, start_row, start_col, d_row, d_col):
    """Platziert ein Wort und liefert die belegten Positionen zurück."""
    positions = []
    for index, letter in enumerate(word):
        row = start_row + d_row * index
        col = start_col + d_col * index
        if grid[row][col] is None:
            grid[row][col] = letter
        fill_counts[row][col] += 1
        positions.append((row, col))
    return positions


def _wordsearch_unplace_word(grid, fill_counts, positions):
    """Entfernt eine vorherige Wortplatzierung aus Raster und Zähler."""
    for row, col in positions:
        fill_counts[row][col] -= 1
        if fill_counts[row][col] <= 0:
            fill_counts[row][col] = 0
            grid[row][col] = None


def _assign_wordsearch_directions(words, options, allow_diagonal, rng):
    """Weist Wörtern erlaubte Richtungen anhand der Optionen zu."""
    horizontal_words = {
        _normalize_wordsearch_token(item)
        for item in _as_text_list(options.get("horizontal"))
    }
    vertical_words = {
        _normalize_wordsearch_token(item)
        for item in _as_text_list(options.get("vertical"))
    }

    direction_map = {}
    unspecified = []

    for word in words:
        in_horizontal = word in horizontal_words
        in_vertical = word in vertical_words

        if in_horizontal and in_vertical:
            direction_map[word] = "HV"
        elif in_horizontal:
            direction_map[word] = "H"
        elif in_vertical:
            direction_map[word] = "V"
        else:
            unspecified.append(word)

    target_horizontal = max(1, round(len(words) / 2))
    current_horizontal = sum(
        1 for value in direction_map.values() if value in {"H", "HV"}
    )

    for word in sorted(unspecified, key=len, reverse=True):
        prefer_horizontal = len(word) >= 7
        choose_horizontal = current_horizontal < target_horizontal and (
            prefer_horizontal or rng.random() < 0.55
        )
        direction_map[word] = "H" if choose_horizontal else "V"
        if direction_map[word] == "H":
            current_horizontal += 1

    directions_by_word = {}
    for word in words:
        mode = direction_map.get(word, "H")
        if mode == "HV":
            allowed = [(0, 1), (1, 0)]
        elif mode == "V":
            allowed = [(1, 0)]
        else:
            allowed = [(0, 1)]

        if (
            allow_diagonal
            and word not in horizontal_words
            and word not in vertical_words
        ):
            allowed = list(allowed) + [(1, 1), (1, -1)]

        directions_by_word[word] = allowed

    return directions_by_word


def _wordsearch_dimensions_feasible(rows, cols, words, directions_by_word):
    """Überprüft, ob die Dimensionen für die Wortsuche machbar sind."""
    for word in words:
        allowed = directions_by_word.get(word, [(0, 1)])
        fits = False
        length = len(word)
        for d_row, d_col in allowed:
            if d_row == 0 and d_col == 1 and cols >= length:
                fits = True
            elif d_row == 1 and d_col == 0 and rows >= length:
                fits = True
            elif d_row == 1 and d_col in {1, -1} and rows >= length and cols >= length:
                fits = True
        if not fits:
            return False
    return True


def _build_wordsearch_grid(words, options):
    """Baut das Raster für die Wortsuche auf."""
    if not words:
        return None

    seed_value = "|".join(
        [
            ",".join(words),
            str(
                options.get("min_size")
                or options.get("size")
                or options.get("min")
                or ""
            ),
            str(options.get("min_rows") or options.get("rows") or ""),
            str(options.get("min_cols") or options.get("cols") or ""),
            str(options.get("diagonal") or ""),
            str(options.get("horizontal") or ""),
            str(options.get("vertical") or ""),
        ]
    )
    rng = random.Random(seed_value)
    allow_diagonal = _option_is_enabled(options.get("diagonal"), default=False)
    min_rows, min_cols = _parse_min_wordsearch_size(options)
    strategy = resolve_wordsearch_generation_strategy(options)
    directions_by_word = _assign_wordsearch_directions(
        words, options, allow_diagonal, rng
    )
    sorted_words = sorted(words, key=len, reverse=True)
    total_letters = sum(len(word) for word in sorted_words)
    longest_word = max(len(word) for word in sorted_words)

    lower_rows = max(min_rows, strategy.min_grid_edge)
    lower_cols = max(min_cols, strategy.min_grid_edge)
    upper_bound = max(
        longest_word + strategy.longest_word_padding,
        int((total_letters * strategy.area_density_factor) ** 0.5) + strategy.sqrt_padding,
        min_rows,
        min_cols,
    )

    candidate_sizes = []
    for rows in range(lower_rows, upper_bound + 1):
        for cols in range(lower_cols, upper_bound + 1):
            area = rows * cols
            if area < total_letters:
                continue
            if not _wordsearch_dimensions_feasible(
                rows, cols, sorted_words, directions_by_word
            ):
                continue
            candidate_sizes.append((area, abs(rows - cols), rows, cols))

    candidate_sizes.sort(key=lambda item: (item[0], item[1], item[2]))

    for _area, _shape_bias, rows, cols in candidate_sizes[: strategy.max_candidate_sizes]:
        for _attempt in range(strategy.placement_attempts_per_size):
            grid = [[None for _ in range(cols)] for _ in range(rows)]
            fill_counts = [[0 for _ in range(cols)] for _ in range(rows)]
            placements = {}

            def place_word_recursive(word_index):
                if word_index >= len(sorted_words):
                    return True

                word = sorted_words[word_index]
                directions = directions_by_word.get(word, [(0, 1)])
                candidates = _wordsearch_candidate_positions(grid, word, directions)
                if not candidates:
                    return False

                rng.shuffle(candidates)
                candidates.sort(key=lambda item: item[0], reverse=True)
                limit = min(len(candidates), strategy.max_candidates_per_word)

                for overlap, start_row, start_col, d_row, d_col in candidates[:limit]:
                    _ = overlap
                    positions = _wordsearch_place_word(
                        grid, fill_counts, word, start_row, start_col, d_row, d_col
                    )
                    placements[word] = (start_row, start_col, d_row, d_col)

                    if place_word_recursive(word_index + 1):
                        return True

                    _wordsearch_unplace_word(grid, fill_counts, positions)
                    placements.pop(word, None)

                return False

            if not place_word_recursive(0):
                continue

            alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            for row in range(rows):
                for col in range(cols):
                    if grid[row][col] is None:
                        grid[row][col] = rng.choice(alphabet)

            return {
                "rows": rows,
                "cols": cols,
                "grid": grid,
                "placements": placements,
                "words": sorted_words,
            }

    return None


def render_wordsearch_answer(options, content, include_solutions):
    """Generiert die HTML-Darstellung der Wortsuche mit Lösungen."""
    words = parse_wordsearch_words(options, content)
    if not words:
        return ""

    generated = _build_wordsearch_grid(words, options)
    if not generated:
        return ""

    rows = generated["rows"]
    cols = generated["cols"]
    grid = generated["grid"]
    placements = generated["placements"]
    ordered_words = generated["words"]

    solution_map = {}
    if include_solutions:
        for word_index, word in enumerate(ordered_words):
            placement = placements.get(word)
            if placement is None:
                continue
            start_row, start_col, d_row, d_col = placement
            for letter_index in range(len(word)):
                row = start_row + d_row * letter_index
                col = start_col + d_col * letter_index
                solution_map.setdefault((row, col), []).append(word_index)

    cells_html = []
    for row in range(rows):
        for col in range(cols):
            css_classes = ["ws-cell"]
            if include_solutions and (row, col) in solution_map:
                color_index = solution_map[(row, col)][0] % 8
                css_classes.append("ws-solved")
                css_classes.append(f"ws-hit-{color_index}")
            cells_html.append(
                f"<span class='{' '.join(css_classes)}'>{escape(grid[row][col])}</span>"
            )

    word_items = []
    for word_index, word in enumerate(ordered_words):
        css_classes = ["ws-word"]
        if include_solutions:
            css_classes.append(f"ws-hit-{word_index % 8}")
        word_items.append(f"<li class='{' '.join(css_classes)}'>{escape(word)}</li>")

    return (
        f"<div class='answer wordsearch-answer' style='--ws-cols:{cols}'>"
        f"<div class='wordsearch-grid'>{''.join(cells_html)}</div>"
        f"<ul class='wordsearch-words'>{''.join(word_items)}</ul>"
        "</div>"
    )


def estimate_wordsearch_weight(options, content):
    """Schätzt das Gewicht der Wortsuche basierend auf den Wörtern."""
    words = parse_wordsearch_words(options, content)
    if not words:
        return 0.0
    area_estimate = max(36, sum(len(word) for word in words) * 1.4)
    return max(2.0, min(7.8, area_estimate / 18.0))
