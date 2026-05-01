"""Help-card extraction and HTML rendering."""

from __future__ import annotations

from html import escape

from ..styles.blatt_styles import build_stylesheet
from .blatt_kern_shared import (
    HELP_BLOCK_TYPES,
    _new_markdown_converter,
    _help_labels_for_tag,
    _normalize_help_tag,
    _resolve_help_level,
    is_hole_punch_layout_enabled,
    normalize_markdown,
    should_render_block,
)


def collect_help_blocks(blocks, include_solutions=False, document_mode="worksheet"):
    """Extrahiert sichtbare Hilfeblöcke inkl. Metadaten in Dokumentreihenfolge."""

    collected = []
    for block_type, options, content in blocks:
        if block_type not in HELP_BLOCK_TYPES:
            continue
        if not should_render_block(
            block_type,
            options,
            include_solutions,
            document_mode=document_mode,
        ):
            continue

        collected.append(
            {
                "options": dict(options),
                "content": (content or "").strip(),
                "level": _resolve_help_level(options),
            }
        )

    return collected


def _annotate_help_block_labels(help_blocks, help_tag):
    """Assigns deterministic visible labels to help cards based on global/local tags."""

    normalized_help_tag = _normalize_help_tag(help_tag)
    auto_tag_entries = [block for block in help_blocks if not _normalize_help_tag(block["options"].get("tag"))]
    auto_labels = _help_labels_for_tag(len(auto_tag_entries), normalized_help_tag)
    auto_label_index = 0

    annotated_blocks = []
    for block in help_blocks:
        block_options = block["options"]
        local_tag = _normalize_help_tag(block_options.get("tag"))
        if local_tag:
            help_label = local_tag
        else:
            help_label = (
                auto_labels[auto_label_index]
                if auto_label_index < len(auto_labels)
                else None
            )
            auto_label_index += 1

        annotated_block = dict(block)
        annotated_block["label"] = help_label
        annotated_blocks.append(annotated_block)

    return annotated_blocks


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

    help_blocks = collect_help_blocks(
        blocks,
        include_solutions=include_solutions,
        document_mode="worksheet",
    )
    if not help_blocks:
        return ""

    help_blocks = _annotate_help_block_labels(help_blocks, (meta or {}).get("tag"))

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
        label_text = (block.get("label") or "").strip()
        header_title = f"{label_text} - {title_text}" if label_text else title_text
        level_badge = (
            f"<span class='help-card-level'>Stufe {level}</span>"
            if level is not None
            else ""
        )

        cards_html.append(
            f"""
<section class="help-card" data-help-index="{index}">
<header class="help-card-header">
<h2>{escape(header_title)}</h2>
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
