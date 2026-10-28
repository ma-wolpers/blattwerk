"""Lernhilfen-Labels: Karten und Aufgabenverweise folgen derselben Regel.

`help_block_labels` ist die eine Label-Regel, `assign_help_blocks` die eine
Zuordnung Lernhilfe -> (Teil-)Aufgabe (`blatt_kern_shared_blocks`).
"""

from __future__ import annotations

from app.core.blatt_kern_help_render import collect_labeled_help_blocks
from app.core.blatt_kern_layout_render import render_html
from app.core.blatt_kern_shared import assign_help_blocks, help_block_labels

META = {"Titel": "T", "Fach": "M", "Thema": "X"}


def test_help_before_first_task_keeps_references_and_cards_in_step():
    """Regression: eine Lernhilfe vor der ersten Aufgabe verschob die Verweis-Buchstaben gegen die Karten."""
    blocks = [
        ("help", {"title": "Vorab"}, "Allgemeiner Tipp."),
        ("task", {"work": "single"}, "Bearbeite die Aufgabe."),
        ("help", {"title": "Zur Aufgabe"}, "Konkreter Tipp."),
    ]

    worksheet_html = render_html(META, blocks, include_solutions=False)
    labels = [card["label"] for card in collect_labeled_help_blocks(META, blocks)]

    assert labels == ["A", "B"]
    assert "→ Lernhilfe B" in worksheet_html
    assert "→ Lernhilfe A" not in worksheet_html


def test_assignment_links_help_to_nearest_preceding_task_or_subtask():
    blocks = [
        ("help", {}, "vorab"),
        ("task", {}, "Aufgabe"),
        ("subtask", {}, "a"),
        ("help", {"tag": "X"}, "zu a"),
        ("help", {}, "auch zu a"),
    ]

    assignments = assign_help_blocks(blocks)

    assert [(a.block_index, a.label, a.target_index) for a in assignments] == [
        (0, "A", None),
        (3, "X", 2),
        (4, "B", 2),
    ]


def test_label_rule_keeps_local_tags_and_numbers_the_rest():
    assert help_block_labels([None, "LOKAL", None], "1") == ["1A", "LOKAL", "1B"]
    assert help_block_labels([None], None) == [None]
