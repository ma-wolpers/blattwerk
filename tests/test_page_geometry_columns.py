"""Tests für die Randspalten-Geometrie bei Aufgaben innerhalb von `:::columns` (`page_geometry.py`).

Nur die ERSTE (linke) Spalte grenzt direkt an die linke `body`-Gutter und
kann ihr Aufgabensymbol deshalb in den echten Seitenrand floaten (wie eine
Aufgabe außerhalb von Spalten). Alle weiteren Spalten können das nicht (ein
Float würde in eine Nachbarspalte ragen) und behalten die Icons inline über
dem Label. Da CSS-Selektoren in diesen Tests nicht von einem echten Browser
ausgewertet werden, prüft dieses Modul zwei Dinge getrennt, die zusammen die
Wirkung ergeben: (1) die DOM-Struktur stellt sicher, dass `:first-child`
tatsächlich die linke Spalte trifft, (2) der generierte CSS-Text enthält
exakt den erwarteten, eingeschränkten Selektor -- nicht mehr den alten,
ausnahmslosen `.column .task-margin-icons`.
"""

import re

from app.core.blatt_kern_layout_render import render_columns_container
from app.styles.page_geometry import build_gutter_css

_TASK_OPTIONS = {"work": "partner", "action": "read", "hint": "tip", "_show_task_label": "1"}


def _columns_with_two_tasks():
    columns_blocks = [
        [("task", dict(_TASK_OPTIONS), "Aufgabe links.")],
        [("task", dict(_TASK_OPTIONS), "Aufgabe rechts.")],
    ]
    return render_columns_container(columns_blocks, {"cols": "2"}, include_solutions=False)


def test_task_margin_icons_is_direct_descendant_of_each_column():
    html = _columns_with_two_tasks()

    columns = re.findall(r"<div class='column'>(.*?)</div></div>", html)
    assert len(columns) == 2, html
    for column_content in columns:
        assert column_content.startswith(
            "<div data-block-type=\"task\" class='task'><div class='task-margin-icons'>"
        ), column_content


def test_first_column_task_margin_icons_precedes_second_column():
    html = _columns_with_two_tasks()

    first_column_start = html.index("<div class='column'>")
    second_column_start = html.index("<div class='column'>", first_column_start + 1)
    assert first_column_start < second_column_start


def test_gutter_css_restricts_inline_fallback_to_non_first_columns():
    css = build_gutter_css(reserve_gutters=True)

    assert ".column:not(:first-child) .task-margin-icons {" in css
    # Regression: die alte, ausnahmslose Fassung darf nicht wiederkehren --
    # sie würde auch die erste Spalte auf "float: none" zurücksetzen und
    # damit die echte Randspalte für dortige Aufgabensymbole blockieren.
    assert not re.search(r"(?<!:not\(:first-child\)\s)\.column \.task-margin-icons \{", css)


def test_general_task_margin_icons_rule_still_floats_left():
    """Die erste Spalte bekommt kein eigenes Override -- sie erbt diese allgemeine Regel."""
    css = build_gutter_css(reserve_gutters=True)

    general_rule = re.search(r"(?<!:not\(:first-child\)\s)\.task-margin-icons \{([^}]*)\}", css)
    assert general_rule is not None, css
    assert "float: left" in general_rule.group(1)
