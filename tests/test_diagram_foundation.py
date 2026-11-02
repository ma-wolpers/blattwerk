"""Tests für die Diagramm-Registrierung und die gemeinsamen Textbausteine."""

from __future__ import annotations

import re

from app.core._editable_convert_js import _IMAGE_ONLY_BLOCK_TYPES
from app.core.authoring_guide_prose import PROSE_SECTIONS
from app.core.blatt_validator_constants import BLOCK_ALLOWED_OPTIONS, KNOWN_BLOCK_TYPES
from app.core.block_insert_snippets import BLOCK_INSERT_SNIPPETS
from app.core.diagram_block_catalog import DIAGRAM_BLOCKS, DIAGRAM_HEADER_RE
from app.core.diagram_block_dispatch import estimate_diagram_weight, render_diagram_block
from app.core.diagram_text import iter_source_lines, make_cell, render_cell

EXISTING_CODE_PREFIXES = {"AN", "BL", "CW", "EV", "FM", "IM", "KL", "MA", "MJ", "OP", "PK", "PT", "QR", "SC", "SL"}


def test_every_diagram_block_is_derived_everywhere():
    """Ein Katalogeintrag reicht: Validator, Snippets, PPTX-Liste und Prosa kennen den Block."""
    for spec in DIAGRAM_BLOCKS:
        assert spec.name in KNOWN_BLOCK_TYPES
        assert {"width", "show", "mode", "align"} <= BLOCK_ALLOWED_OPTIONS[spec.name]
        assert BLOCK_INSERT_SNIPPETS[spec.name] == spec.snippet
        assert spec.name in _IMAGE_ONLY_BLOCK_TYPES
        assert f"block:{spec.name}" in PROSE_SECTIONS
        assert DIAGRAM_HEADER_RE.match(f":::{spec.name} width=50%")


def test_diagram_names_are_lowercase_english_and_codes_are_unique():
    """Blocknamen ohne Umlaute; jeder Block hat einen eigenen Leer-Code außerhalb des Bestands."""
    codes = [spec.empty_code for spec in DIAGRAM_BLOCKS]
    assert len(codes) == len(set(codes))
    for spec in DIAGRAM_BLOCKS:
        assert spec.name.isascii() and spec.name.islower()
        assert spec.empty_code[:2] not in EXISTING_CODE_PREFIXES


def test_every_snippet_renders_and_estimates_a_weight():
    """Jedes Einfüge-Snippet ist gültig: Es rendert in beiden Fassungen etwas Sichtbares."""
    for spec in DIAGRAM_BLOCKS:
        content = "\n".join(spec.snippet.replace("\x01", "").splitlines()[1:-1])
        assert render_diagram_block(spec.name, {}, content, include_solutions=False)
        assert render_diagram_block(spec.name, {}, content, include_solutions=True)
        assert estimate_diagram_weight(spec.name, {}, content) > 0


def test_source_lines_keep_numbers_and_read_markers_after_indent():
    """Kommentar- und Leerzeilen zählen nicht, die sichtbare Zeilennummer bleibt."""
    lines = list(iter_source_lines("a\n\n%%Notiz%%\n    % b\n\t§ c\n"))
    assert [(line.number, line.width, line.show, line.text) for line in lines] == [
        (1, 0, "both", "a"),
        (4, 4, "solution", "b"),
        (5, 4, "worksheet", "c"),
    ]


def test_render_cell_hides_gap_in_worksheet_and_marks_it_in_solution():
    """Lücke: im Arbeitsblatt unsichtbar platzhaltend, in der Lösung sichtbar."""
    cell = make_cell("a %{b}")
    worksheet, worksheet_gap = render_cell(cell, include_solutions=False)
    solution, solution_gap = render_cell(cell, include_solutions=True)
    assert worksheet_gap and "diagram-hidden" in worksheet
    assert not solution_gap and "diagram-hidden" not in solution and "b" in solution


def test_render_cell_keeps_list_markers_and_escapes_html():
    """`- id` wird keine Liste, `a<b` kein HTML-Tag."""
    assert "<ul" not in render_cell(make_cell("- id: Ganzzahl"), False)[0]
    assert "a&lt;b" in render_cell(make_cell("a<b"), False)[0]


def test_diagram_colors_come_only_from_the_color_profile():
    """Keine festen Farben im Diagramm-CSS; das Schwarz-Weiß-Profil liefert nur Grau."""
    import re
    from pathlib import Path

    from app.styles.worksheet_design import build_design_css

    css = Path(__file__).resolve().parents[1].joinpath("assets", "worksheet.css").read_text(encoding="utf-8")
    start = css.index("/* Diagrammblöcke")
    section = css[start: css.index("/* Struktogramm (:::structogram)")]
    fallbacks = {"#777", "#999", "#333", "#111"}
    assert set(re.findall(r"#[0-9a-fA-F]{3,6}", section)) <= fallbacks

    bw = build_design_css("bw")
    for name in ("--theme-accent-main", "--theme-accent-secondary", "--theme-accent-strong"):
        value = re.search(rf"{name}: (#[0-9a-fA-F]{{6}})", bw).group(1)
        assert value[1:3] == value[3:5] == value[5:7], (name, value)


def test_text_width_counts_what_a_formula_shows():
    """LaTeX-Befehle zählen nicht mit, sichtbare Zeichen schon."""
    from app.core.diagram_svg import text_width

    assert text_width("$\\frac{1}{2}$") == text_width("12")
    assert text_width("abc") > text_width("a")


def test_text_and_gaps_always_stand_on_a_light_ground():
    """Töne bleiben flach und hell, die Datenfarben sind hell genug für schwarzen Text."""
    import colorsys
    import re
    from pathlib import Path

    from app.styles.diagram_palette import data_palette

    css = Path(__file__).resolve().parents[1].joinpath("assets", "worksheet.css").read_text(encoding="utf-8")
    for number in range(1, 5):
        rule = re.search(rf"\.diagram-tone-{number} \{{\s*fill: color-mix\(in srgb, var\(--diagram-\w+\) (\d+)%", css)
        assert rule and int(rule.group(1)) < 30, number
    for color in data_palette("#2F7FAE", False) + data_palette("#5A5A5A", False) + data_palette("#000000", True):
        channels = [int(color[i: i + 2], 16) / 255 for i in (1, 3, 5)]
        assert colorsys.rgb_to_hls(*channels)[1] >= 0.6, color


def test_diagrams_use_flat_shades_without_gradients_or_blur():
    """Keine Verläufe und keine unscharfen Schatten; der Versatz ist eine flache Form."""
    from pathlib import Path

    html = render_diagram_block("graph", {}, "A - B")
    assert "Gradient" not in html
    css = Path(__file__).resolve().parents[1].joinpath("assets", "worksheet.css").read_text(encoding="utf-8")
    section = css[css.index("/* Diagrammblöcke"): css.index("/* Struktogramm (:::structogram)")]
    assert "gradient" not in section.replace("Verläufen", "") and "drop-shadow" not in section


def test_data_palette_is_colorful_except_in_black_and_white():
    """Mehrere klar verschiedene Farben; im Schwarz-Weiß-Profil nur Grau."""
    from app.styles.diagram_palette import DATA_COLOR_COUNT, data_palette
    from app.styles.worksheet_design import COLOR_PROFILE_ORDER, build_design_css

    colorful = data_palette("#4C5ED9", False)
    assert len(set(colorful)) == DATA_COLOR_COUNT
    assert len(set(data_palette("#5A5A5A", False))) == DATA_COLOR_COUNT
    assert all(c[1:3] == c[3:5] == c[5:7] for c in data_palette("#4C5ED9", True))
    for profile in COLOR_PROFILE_ORDER:
        assert "--diagram-data-8:" in build_design_css(profile)


def test_offset_repeats_the_shape_with_the_same_measures():
    """Der Versatz ist dieselbe Form, nur verschoben, also auch mit denselben Ecken."""
    html = render_diagram_block("timeline", {}, "1789: a")
    shape = re.search(r"<rect class='diagram-data-1' ([^>]*?) />", html).group(1)
    assert f"<rect class='diagram-offset diagram-offset-data-1' {shape} transform='translate(3 3)' />" in html


def test_parts_inside_a_shape_have_no_own_offset():
    """Kopf einer Klasse und innerer Kreis eines Endzustands werfen keinen eigenen Versatz."""
    classes = render_diagram_block("classdiagram", {}, "klasse A\n    - x: Ganzzahl")
    assert classes.count("diagram-offset ") == 1
    assert classes.count("diagram-flat") == 1
    state = render_diagram_block("statediagram", {}, "start -> A\nende: A\nA -> A: x")
    assert state.count("<ellipse class='diagram-offset ") == 1


def test_bar_offset_stops_at_the_axis():
    """Balken und Histogramm ragen nicht unter die x-Achse."""
    for options, content in (({"type": "bar"}, "A: 4\nB: 2"), ({"type": "histogram"}, "0-10: 4\n10-20: 2")):
        html = render_diagram_block("chart", options, content)
        axis = max(float(y) for y in re.findall(r"<line class='diagram-line' x1='[\d.]+' y1='([\d.]+)' x2='[\d.]+' y2='\1'", html))
        offsets = re.findall(r"<rect class='diagram-offset [^']*' x='[\d.]+' y='([\d.]+)' width='[\d.]+' height='([\d.]+)'", html)
        assert len(offsets) == 2
        for top, height in offsets:
            assert float(top) + float(height) <= axis + 0.1


def test_pie_has_one_offset_for_the_whole_circle():
    """Der Kreis bekommt einen Versatz, die Sektoren keinen eigenen."""
    html = render_diagram_block("chart", {"type": "pie"}, "A: 1\nB: 2\nC: 3")
    assert html.count("diagram-offset ") == 1


def test_untinted_mode_whitens_surfaces_but_keeps_class_headers_and_offsets():
    """Ohne Tönung sind Flächen weiß; Klassenköpfe, Bruchteile und der Versatz bleiben farbig."""
    from app.styles.worksheet_design import build_design_css

    tinted = build_design_css("indigo", tint=True)
    untinted = build_design_css("indigo", tint=False)
    assert "diagram-keep-tint" not in tinted
    assert ':not(.diagram-keep-tint)' in untinted and ".material" in untinted
    assert "diagram-offset" not in untinted and "diagram-fill" not in untinted
    header = render_diagram_block("classdiagram", {}, "klasse A\n    - x: Ganzzahl")
    assert "diagram-keep-tint" in header


def test_gray_profile_is_black_and_white_with_tint():
    """Das frühere Profil „Grau“ wird zu S/W; S/W mit Tönung hat seine hellen Grautöne."""
    import re

    from app.styles.worksheet_design import COLOR_PROFILE_ORDER, build_design_css, normalize_color_profile

    assert "default" not in COLOR_PROFILE_ORDER
    for old in ("default", "standard", "grau", "Grau"):
        assert normalize_color_profile(old) == "bw"
    tinted = build_design_css("bw", tint=True)
    background = re.search(r"--info-bg-color: (#[0-9A-Fa-f]{6})", tinted).group(1)
    assert background.upper() == "#F4F4F4"


def test_every_attribute_oval_has_an_offset():
    """Regression: das ER-Attribut ohne Schlüssel hatte keinen Versatz."""
    html = render_diagram_block("erdiagram", {}, "entität A\n    __k__\n    Name\nentität B\n    __j__\nA 1 - r - n B")
    shapes = re.findall(r"<ellipse class='([^']*)'", html)
    assert len([css for css in shapes if "diagram-offset" in css]) == len([css for css in shapes if "diagram-offset" not in css])
