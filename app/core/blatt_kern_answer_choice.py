"""Multiple-choice and cloze answer rendering helpers."""

from __future__ import annotations

import random
import re
from html import escape

from .answer_line_markers import render_answer_content_html_for_mode
from .blatt_kern_shared import (
    _new_markdown_converter,
    _normalize_keyword,
    _option_is_enabled,
    _safe_int,
    normalize_markdown,
)

def _normalize_choice_values(raw_value):
    """Normalisiert kommaseparierte oder pipe-separierte Antwortlisten."""
    if not raw_value:
        return []

    normalized = str(raw_value).replace("|", ",")
    values = [value.strip() for value in normalized.split(",") if value.strip()]
    return values

def _parse_multiple_choice_content(content):
    """Extrahiert eine oder mehrere Frage+Optionen-Gruppen aus dem Blockinhalt."""
    question_lines = []
    options = []
    groups = []

    for raw_line in (content or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        option_match = re.match(r"^[-*+]\s+(.*)$", line)
        if option_match:
            item = option_match.group(1).strip()
            checked_match = re.match(r"^\[(x|X)\]\s+(.*)$", item)
            unchecked_match = re.match(r"^\[\s*\]\s+(.*)$", item)

            if checked_match:
                options.append((checked_match.group(2).strip(), True))
            elif unchecked_match:
                options.append((unchecked_match.group(1).strip(), False))
            else:
                options.append((item, False))
            continue

        if options:
            groups.append(("\n".join(question_lines).strip(), options))
            question_lines = [line]
            options = []
            continue

        question_lines.append(line)

    trailing_question_text = "\n".join(question_lines).strip()
    if options:
        groups.append((trailing_question_text, options))

    return trailing_question_text, groups

def _parse_mc_inline_weights(options):
    """Parst optionale Inline-Breiten für Frage/Optionen (z. B. `2:3`)."""
    raw = options.get("widths")
    if not raw:
        return None

    normalized = str(raw).replace(":", " ").replace(",", " ")
    parts = [part.strip().lower() for part in normalized.split() if part.strip()]
    if len(parts) < 2:
        return None

    weights = []
    for part in parts[:2]:
        value = part[:-2] if part.endswith("fr") else part
        try:
            number = float(value)
        except ValueError:
            continue

        if number <= 0:
            continue
        weights.append(max(0.2, min(number, 50.0)))

    if len(weights) < 2:
        return None

    return weights[0], weights[1]

def _estimate_mc_inline_weights(question_text, choice_items):
    """Schätzt adaptive Inline-Gewichte für Frage/Optionen anhand des Platzbedarfs."""
    question_length = len((question_text or "").strip())
    options_total_length = sum(len((label or "").strip()) for label, _ in choice_items)
    options_count = len(choice_items)

    question_weight = 0.9 + (question_length / 34.0)
    options_weight = 1.0 + (options_total_length / 30.0) + (options_count * 0.18)

    question_weight = max(0.8, min(question_weight, 3.2))
    options_weight = max(1.0, min(options_weight, 5.2))
    return question_weight, options_weight

def _render_inline_markdown_fragment(text):
    """Rendert kurzen Markdown-Text ohne umschließendes `<p>`-Tag."""
    raw = (text or "").strip()
    if not raw:
        return ""

    md = _new_markdown_converter()
    html = md.convert(normalize_markdown(raw)).strip()

    paragraph_match = re.fullmatch(r"<p>(.*)</p>", html, flags=re.DOTALL)
    if paragraph_match:
        return paragraph_match.group(1).strip()

    return html

def _render_multiple_choice_answer(options, content, include_solutions):
    """Rendert Multiple-Choice mit horizontalen Ankreuzfeldern."""
    trailing_question_text, parsed_groups = _parse_multiple_choice_content(content)

    true_false_mode = _normalize_keyword(options.get("tf") or options.get("true_false"), default="false") in {
        "1",
        "true",
        "yes",
        "on",
        "tf",
        "richtigfalsch",
        "richtig_false",
    }
    inline_mode = _option_is_enabled(options.get("inline"), default=False)
    explicit_inline_weights = _parse_mc_inline_weights(options)

    rendered_groups = []

    if true_false_mode:
        correct_raw = _normalize_keyword(options.get("correct"), default="true")
        is_true_correct = correct_raw not in {"false", "falsch", "0", "no", "off"}
        choice_items = [
            ("richtig", is_true_correct),
            ("falsch", not is_true_correct),
        ]
        tf_questions = [line.strip() for line in (content or "").splitlines() if line.strip()]
        if not tf_questions:
            tf_questions = [""]
        rendered_groups = [(question_text, list(choice_items)) for question_text in tf_questions]
    else:
        if parsed_groups:
            rendered_groups = [(question_text, list(group_choices)) for question_text, group_choices in parsed_groups]
        else:
            configured_options = _normalize_choice_values(options.get("options"))
            choice_items = [(label, False) for label in configured_options]

            if not choice_items:
                choice_items = [("richtig", True), ("falsch", False)]

            rendered_groups = [(trailing_question_text, choice_items)]

        correct_indexes = set()
        for value in _normalize_choice_values(options.get("correct")):
            try:
                correct_indexes.add(max(0, int(value) - 1))
            except ValueError:
                continue

        if correct_indexes and len(rendered_groups) == 1:
            question_text, group_choices = rendered_groups[0]
            updated_items = []
            for idx, (label, _is_correct) in enumerate(group_choices):
                updated_items.append((label, idx in correct_indexes))
            rendered_groups[0] = (question_text, updated_items)

    group_html = []
    for question_text, choice_items in rendered_groups:
        choice_html = []
        for label, is_correct in choice_items:
            checked = include_solutions and is_correct
            option_classes = ["mc-option"]
            if include_solutions and is_correct:
                option_classes.append("is-correct")

            box_symbol = "☑" if checked else "☐"
            label_html = _render_inline_markdown_fragment(label)
            choice_html.append(
                f"<div class='{' '.join(option_classes)}'><span class='mc-box'>{box_symbol}</span><span class='mc-label'>{label_html}</span></div>"
            )

        question_html = ""
        if question_text:
            question_html = f"<div class='mc-question'>{_render_inline_markdown_fragment(question_text)}</div>"

        has_question = bool((question_text or "").strip())
        group_classes = ["mc-group"]
        group_style = ""
        if inline_mode and has_question:
            group_classes.append("mc-inline")
            if explicit_inline_weights is not None:
                question_weight, options_weight = explicit_inline_weights
                group_classes.append("mc-inline-custom")
            else:
                question_weight, options_weight = _estimate_mc_inline_weights(question_text, choice_items)
            group_style = f" style='--mc-question-fr:{question_weight:.2f}; --mc-options-fr:{options_weight:.2f}'"

        group_html.append(
            f"<div class='{' '.join(group_classes)}'{group_style}>{question_html}<div class='mc-options'>{''.join(choice_html)}</div></div>"
        )

    container_classes = ["answer", "multiple-choice"]

    return (
        f"<div class='{' '.join(container_classes)}'>"
        f"{''.join(group_html)}"
        "</div>"
    )

def _normalize_word_position(value):
    """Normalisiert Position der Lösungswörter beim Lückentext."""
    normalized = _normalize_keyword(value, default="none")
    if normalized in {"above", "top", "ueber", "über", "oben"}:
        return "above"
    if normalized in {"below", "bottom", "under", "unter", "unten"}:
        return "below"
    return "none"

def _normalize_gap_mode(value):
    """Normalisiert Lückenlängenmodus auf approx/fixed."""
    normalized = _normalize_keyword(value, default="approx")
    if normalized in {"fixed", "equal", "same", "uniform", "gleich"}:
        return "fixed"
    return "approx"

def _shuffle_word_bank(words):
    """Mischt Lösungswörter und vermeidet die Originalreihenfolge, falls möglich."""
    if len(words) <= 1:
        return list(words)

    original = list(words)
    shuffled = list(words)
    rng = random.SystemRandom()

    for _ in range(8):
        rng.shuffle(shuffled)
        if shuffled != original:
            return shuffled

    return original[1:] + original[:1]

def _render_cloze_answer(md, options, content, include_solutions):
    """Rendert Lückentext mit optionaler Wortbank und Lösungsausgabe."""
    cloze_pattern = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
    matches = list(cloze_pattern.finditer(content or ""))

    if not matches:
        return ""

    gap_mode = _normalize_gap_mode(options.get("gap"))
    word_position = _normalize_word_position(options.get("words"))
    fixed_gap_length = max(4, _safe_int(options.get("gap_length", 10), 10))
    gap_length_multiplier = 2

    templated_content = content
    replacements = []

    for idx, match in enumerate(matches):
        solution_word = match.group(1).strip()
        placeholder = f"@@CLOZE_{idx}@@"
        templated_content = templated_content.replace(match.group(0), placeholder, 1)

        if include_solutions:
            replacement_html = f"<span class='cloze-gap cloze-filled'>{escape(solution_word)}</span>"
        else:
            if gap_mode == "fixed":
                gap_length = fixed_gap_length * gap_length_multiplier
            else:
                gap_length = max(8, min(52, (len(solution_word) + 2) * gap_length_multiplier))
            replacement_html = f"<span class='cloze-gap cloze-empty' style='--gap-ch:{gap_length}'></span>"

        replacements.append((placeholder, solution_word, replacement_html))

    cloze_html = md.convert(normalize_markdown(templated_content))
    for placeholder, _solution_word, replacement_html in replacements:
        cloze_html = cloze_html.replace(placeholder, replacement_html)

    word_bank_html = ""
    if not include_solutions and word_position != "none":
        word_bank_words = [solution_word for _placeholder, solution_word, _ in replacements]
        shuffled_words = _shuffle_word_bank(word_bank_words)
        chips = "".join(
            f"<span class='cloze-word'>{escape(solution_word)}</span>" for solution_word in shuffled_words
        )
        word_bank_html = f"<div class='cloze-wordbank'>{chips}</div>"

    if word_position == "above" and word_bank_html:
        body_html = f"{word_bank_html}{cloze_html}"
    elif word_position == "below" and word_bank_html:
        body_html = f"{cloze_html}{word_bank_html}"
    else:
        body_html = cloze_html

    return f"<div class='answer cloze-answer'>{body_html}</div>"

def _render_answer_solution_text(content, include_solutions=True):
    """Render answer text lines for worksheet or solution mode."""
    rendered_html = render_answer_content_html_for_mode(
        content,
        include_solutions=include_solutions,
        default_show="both",
        highlight_solution_segments=True,
    )
    if not rendered_html:
        return ""
    return f"<div class='answer-solution-text'>{rendered_html}</div>"
