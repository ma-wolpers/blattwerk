"""Help-card extraction and HTML rendering."""

from __future__ import annotations

from html import escape

from ..styles.blatt_styles import build_stylesheet
from .blatt_kern_shared import (
    HELP_BLOCK_TYPES,
    _new_markdown_converter,
    _resolve_help_level,
    is_hole_punch_layout_enabled,
    normalize_markdown,
    should_render_block,
)


def collect_help_blocks(blocks, include_solutions=False):
    """Extrahiert sichtbare Hilfeblöcke inkl. Metadaten in Dokumentreihenfolge."""

    collected = []
    for block_type, options, content in blocks:
        if block_type not in HELP_BLOCK_TYPES:
            continue
        if not should_render_block(block_type, options, include_solutions):
            continue

        collected.append(
            {
                "options": dict(options),
                "content": (content or "").strip(),
                "level": _resolve_help_level(options),
            }
        )

    return collected


def render_help_cards_html(
    meta,
    blocks,
    include_solutions=False,
    page_format="a4_portrait",
    print_profile="standard",
    color_profile="indigo",
    font_profile="segoe",
    font_size_profile="normal",
):
    """Rendert ausschließlich Hilfeblöcke als kartenseitige HTML-Ausgabe."""

    help_blocks = collect_help_blocks(blocks, include_solutions=include_solutions)
    if not help_blocks:
        return ""

    stylesheet = build_stylesheet(
        page_format,
        print_profile,
        hole_punch_enabled=is_hole_punch_layout_enabled(meta),
        color_profile=color_profile,
        font_profile=font_profile,
        font_size_profile=font_size_profile,
    )

    cards_html = []
    for index, block in enumerate(help_blocks, start=1):
        block_options = block["options"]
        block_content = block["content"]
        level = block["level"]

        markdown_converter = _new_markdown_converter()
        body_html = (
            markdown_converter.convert(normalize_markdown(block_content))
            if block_content
            else ""
        )

        title_text = (block_options.get("title") or "Hilfe").strip() or "Hilfe"
        level_badge = (
            f"<span class='help-card-level'>Stufe {level}</span>"
            if level is not None
            else ""
        )

        cards_html.append(
            f"""
<section class="help-card" data-help-index="{index}">
<header class="help-card-header">
<h2>{escape(title_text)}</h2>
{level_badge}
</header>
<div class="help-card-body">{body_html}</div>
</section>
""".strip()
        )

    title_value = escape((meta or {}).get("Titel", "Hilfekarten"))
    help_cards_css = """
body {
    margin: 0;
}

@page {
    margin: 0;
}

.help-card {
    border: var(--material-border-width) solid var(--material-border-color);
    border-radius: 10px;
    padding: 0.65cm 0.7cm;
    margin: 0 0 0.45cm 0;
    break-inside: avoid;
    page-break-inside: avoid;
}

.help-card:last-child {
    margin-bottom: 0;
}

.help-card-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.6em;
    margin: 0 0 0.4em 0;
}

.help-card-header h2 {
    margin: 0;
    font-size: 1.18em;
}

.help-card-level {
    color: var(--task-hint-color);
    border: 1px solid var(--material-border-color);
    border-radius: 999px;
    padding: 0.04em 0.55em;
    font-size: 0.9em;
    white-space: nowrap;
}

.help-card-body > *:first-child {
    margin-top: 0;
}

.help-card-body > *:last-child {
    margin-bottom: 0;
}
""".strip()

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{title_value} – Hilfekarten</title>
<script>
window.MathJax = {{
    tex: {{
        inlineMath: [['$', '$']],
        displayMath: [['$$', '$$']],
        processEscapes: true,
    }},
    svg: {{
        fontCache: 'none'
    }}
}};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
<style>
{stylesheet}

{help_cards_css}
</style>
</head>
<body>
{"".join(cards_html)}
</body>
</html>
"""
