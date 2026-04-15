from app.core.blatt_kern_layout_render import render_html
from app.core.blatt_kern_task_render import render_block


def test_task_work_hint_is_hidden_in_test_mode():
    options = {"work": "single", "_show_task_label": "1"}

    worksheet_html = render_block(
        "task",
        options,
        "Rechne aus.",
        include_solutions=False,
        document_mode="ws",
    )
    test_html = render_block(
        "task",
        options,
        "Rechne aus.",
        include_solutions=False,
        document_mode="test",
    )

    assert "task-work-hint" in worksheet_html
    assert "task-work-symbol single" in worksheet_html
    assert "task-work-hint" not in test_html
    assert "task-work-symbol single" not in test_html


def test_task_action_symbol_stays_visible_in_test_mode():
    options = {"work": "single", "action": "read", "_show_task_label": "1"}

    html = render_block(
        "task",
        options,
        "Lies den Text.",
        include_solutions=False,
        document_mode="test",
    )

    assert "task-work-symbol action" in html
    assert "task-work-symbol single" not in html


def test_subtask_work_symbol_is_hidden_in_test_mode():
    options = {
        "work": "partner",
        "_parent_work": "single",
        "_subtask_index": "0",
        "_subtask_total": "1",
    }

    worksheet_html = render_block(
        "subtask",
        options,
        "Vergleicht eure Ergebnisse.",
        include_solutions=False,
        document_mode="ws",
    )
    test_html = render_block(
        "subtask",
        options,
        "Vergleicht eure Ergebnisse.",
        include_solutions=False,
        document_mode="test",
    )

    assert "task-work-symbol partner" in worksheet_html
    assert "task-work-symbol partner" not in test_html


def test_render_html_respects_frontmatter_mode_in_both_output_modes():
    meta = {"Titel": "T", "Fach": "M", "Thema": "X", "mode": "test"}
    blocks = [("task", {"work": "single", "action": "read"}, "Lies den Text.")]

    worksheet_html = render_html(meta, blocks, include_solutions=False)
    solution_html = render_html(meta, blocks, include_solutions=True)

    assert "title='Einzelarbeit'" not in worksheet_html
    assert "title='Einzelarbeit'" not in solution_html
    assert "- Einzelarbeit" not in worksheet_html
    assert "- Einzelarbeit" not in solution_html
    assert "title='lesen'" in worksheet_html
    assert "title='lesen'" in solution_html


def test_task_content_supports_marker_visibility_by_output_mode():
    content = "§ Nur Arbeitsblatt\n% Nur Loesung\nIn beiden"
    options = {"work": "single", "_show_task_label": "1"}

    worksheet_html = render_block(
        "task",
        options,
        content,
        include_solutions=False,
        document_mode="ws",
    )
    solution_html = render_block(
        "task",
        options,
        content,
        include_solutions=True,
        document_mode="ws",
    )

    assert "Nur Arbeitsblatt" in worksheet_html
    assert "Nur Loesung" not in worksheet_html
    assert "In beiden" in worksheet_html

    assert "Nur Arbeitsblatt" not in solution_html
    assert "Nur Loesung" in solution_html
    assert "In beiden" in solution_html


def test_subtask_content_supports_marker_visibility_by_output_mode():
    options = {
        "work": "partner",
        "_parent_work": "single",
        "_subtask_index": "0",
        "_subtask_total": "1",
    }
    content = "§ Nur Arbeitsblatt\n% Nur Loesung\nIn beiden"

    worksheet_html = render_block(
        "subtask",
        options,
        content,
        include_solutions=False,
        document_mode="ws",
    )
    solution_html = render_block(
        "subtask",
        options,
        content,
        include_solutions=True,
        document_mode="ws",
    )

    assert "Nur Arbeitsblatt" in worksheet_html
    assert "Nur Loesung" not in worksheet_html
    assert "In beiden" in worksheet_html

    assert "Nur Arbeitsblatt" not in solution_html
    assert "Nur Loesung" in solution_html
    assert "In beiden" in solution_html


def test_render_html_shows_single_help_reference_without_key():
    meta = {"Titel": "T", "Fach": "M", "Thema": "X", "mode": "ws"}
    blocks = [
        ("task", {"work": "single"}, "Bearbeite die Aufgabe."),
        ("help", {"title": "Starthilfe"}, "Denke an die Regel."),
    ]

    worksheet_html = render_html(meta, blocks, include_solutions=False)

    assert "→ Lernhilfe" in worksheet_html


def test_render_html_shows_single_help_reference_with_tag_only():
    meta = {"Titel": "T", "Fach": "M", "Thema": "X", "mode": "ws", "tag": "A"}
    blocks = [
        ("task", {"work": "single"}, "Aufgabe 1"),
        ("help", {"title": "H1"}, "Hinweis 1"),
    ]

    worksheet_html = render_html(meta, blocks, include_solutions=False)

    assert "→ A" in worksheet_html


def test_render_html_shows_multiple_help_labels_for_numeric_tag():
    meta = {"Titel": "T", "Fach": "M", "Thema": "X", "mode": "ws", "tag": "1"}
    blocks = [
        ("task", {"work": "single"}, "Aufgabe 1"),
        ("help", {"title": "H1"}, "Hinweis 1"),
        ("help", {"title": "H2"}, "Hinweis 2"),
    ]

    worksheet_html = render_html(meta, blocks, include_solutions=False)

    assert "→ Lernhilfen 1A, 1B" in worksheet_html


def test_render_html_shows_multiple_help_labels_for_letter_tag():
    meta = {"Titel": "T", "Fach": "M", "Thema": "X", "mode": "ws", "tag": "A"}
    blocks = [
        ("task", {"work": "single"}, "Aufgabe 1"),
        ("help", {"title": "H1"}, "Hinweis 1"),
        ("help", {"title": "H2"}, "Hinweis 2"),
    ]

    worksheet_html = render_html(meta, blocks, include_solutions=False)

    assert "→ Lernhilfen 1A, 2A" in worksheet_html


def test_render_html_shows_multiple_help_labels_for_text_tag_ending_with_letter():
    meta = {"Titel": "T", "Fach": "M", "Thema": "X", "mode": "ws", "tag": "TAG"}
    blocks = [
        ("task", {"work": "single"}, "Aufgabe 1"),
        ("help", {"title": "H1"}, "Hinweis 1"),
        ("help", {"title": "H2"}, "Hinweis 2"),
        ("help", {"title": "H3"}, "Hinweis 3"),
    ]

    worksheet_html = render_html(meta, blocks, include_solutions=False)

    assert "→ Lernhilfen TAG1, TAG2, TAG3" in worksheet_html


def test_render_html_help_local_tag_overrides_global_tag_for_that_help():
    meta = {"Titel": "T", "Fach": "M", "Thema": "X", "mode": "ws", "tag": "1"}
    blocks = [
        ("task", {"work": "single"}, "Aufgabe 1"),
        ("help", {"title": "H1", "tag": "LOKAL"}, "Hinweis 1"),
        ("help", {"title": "H2"}, "Hinweis 2"),
    ]

    worksheet_html = render_html(meta, blocks, include_solutions=False)

    assert "→ Lernhilfen LOKAL, 1" in worksheet_html


def test_render_html_local_help_tags_are_not_counted_for_auto_suffixes():
    meta = {"Titel": "T", "Fach": "M", "Thema": "X", "mode": "ws", "tag": "1"}
    blocks = [
        ("task", {"work": "single"}, "Aufgabe 1"),
        ("help", {"title": "H1", "tag": "X"}, "Hinweis 1"),
        ("help", {"title": "H2"}, "Hinweis 2"),
        ("help", {"title": "H3"}, "Hinweis 3"),
    ]

    worksheet_html = render_html(meta, blocks, include_solutions=False)

    assert "→ Lernhilfen X, 1A, 1B" in worksheet_html


def test_render_html_shows_help_reference_on_subtask():
    meta = {"Titel": "T", "Fach": "M", "Thema": "X", "mode": "ws", "tag": "X"}
    blocks = [
        ("task", {"work": "single"}, "Oberaufgabe"),
        ("subtask", {}, "Teilaufgabe"),
        ("help", {"title": "Hilfe"}, "Zusatz"),
    ]

    worksheet_html = render_html(meta, blocks, include_solutions=False)

    assert "subtask-help-reference" in worksheet_html
    assert "→ X" in worksheet_html


def test_task_title_is_rendered_in_task_label_before_work_mode():
    options = {
        "work": "single",
        "title": "Titel hier",
        "_show_task_label": "1",
        "_auto_number": "1",
    }

    worksheet_html = render_block(
        "task",
        options,
        "Rechne aus.",
        include_solutions=False,
        document_mode="ws",
    )

    assert "Aufgabe 1 - Titel hier" in worksheet_html
    assert worksheet_html.index("Aufgabe 1 - Titel hier") < worksheet_html.index("Einzelarbeit")
