"""Schlichtes Markdown (`.md`): eine Render-Pipeline für Vorschau und Export.

Semantik (festgelegt im Architektur-Doc, `.md`-Abschnitt):

* **Engine:** python-markdown mit `tables`, `fenced_code`, `sane_lists`.
  Kein `nl2br` (Standard-Zeilenumbruch), kein vollständiges GFM (keine
  Tasklisten, kein `~~`, keine Autolinks), keine Blattwerk-Inline-Marker.
  Raw HTML wird wie in python-markdown üblich durchgereicht.
* **Mathe:** `$…$`/`$$…$$` über `math_span_protection` und MathJax, dieselbe
  Konfiguration wie im Arbeitsblatt.
* **Frontmatter:** wird nach der einen Grenzregel (`frontmatter.py`) erkannt
  und **nicht gerendert**; `Titel` (falls ein String) wird Dokumenttitel.
  Alle anderen Keys -- auch `mode` -- werden ignoriert. Ein kaputtes YAML
  im Frontmatter verhindert das Rendern nicht (der Kopf bleibt trotzdem
  ausgeblendet).
* **Blattwerk-Syntax** (`:::`-Blöcke, `--!` usw.) erscheint als normaler Text.

Preview, HTML-, PDF- und PNG-Export nutzen alle `render_plain_markdown_html`,
damit sie sich nicht fachlich unterscheiden können.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import markdown
import yaml

from .blatt_kern_io_html import absolutize_local_image_sources
from .blatt_kern_io_pdf import write_pdf_from_html
from .export_path_guardrails import validate_export_output_path
from .frontmatter import frontmatter_bounds, load_frontmatter_yaml
from .math_span_protection import convert_markdown_with_math

PLAIN_MARKDOWN_EXTENSIONS = ("tables", "fenced_code", "sane_lists")

_STYLESHEET = """
@page { size: A4 portrait; margin: 2cm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 11pt; line-height: 1.45; color: #111; }
h1, h2, h3 { line-height: 1.2; }
table { border-collapse: collapse; margin: 0.6em 0; }
th, td { border: 1px solid #999; padding: 0.25em 0.5em; vertical-align: top; }
pre { background: #f4f4f4; padding: 0.6em; overflow-x: auto; }
code { font-family: Consolas, "Courier New", monospace; }
img { max-width: 100%; }
"""

_MATHJAX_HEAD = """<script>
window.MathJax = {
    tex: { inlineMath: [['$', '$']], displayMath: [['$$', '$$']], processEscapes: true },
    svg: { fontCache: 'none' }
};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@4/tex-svg.js"></script>"""


def split_plain_markdown(text: str) -> tuple[dict, str]:
    """Trennt Frontmatter (nicht gerendert) und Markdown-Rumpf.

    Returns:
        ``(meta, body)``; ``meta`` ist ``{}`` ohne Frontmatter oder bei
        ungültigem bzw. nicht-mapping YAML.
    """
    source = text or ""
    bounds = frontmatter_bounds(source)
    if bounds is None:
        return {}, source.removeprefix("﻿")
    try:
        meta = load_frontmatter_yaml(bounds.body(source))
    except yaml.YAMLError:
        meta = {}
    return (meta if isinstance(meta, dict) else {}), source[bounds.end :]


def render_plain_markdown_html(text: str) -> str:
    """Rendert schlichtes Markdown zu einem vollständigen HTML-Dokument."""
    meta, body = split_plain_markdown(text)
    title = meta.get("Titel") if isinstance(meta.get("Titel"), str) else ""
    converter = markdown.Markdown(extensions=list(PLAIN_MARKDOWN_EXTENSIONS))
    body_html = convert_markdown_with_math(converter, body, lambda value: value)
    heading = f"<h1>{escape(title)}</h1>\n" if title else ""
    return (
        "<!DOCTYPE html>\n<html lang=\"de\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{escape(title or 'Dokument')}</title>\n{_MATHJAX_HEAD}\n"
        f"<style>{_STYLESHEET}</style>\n</head>\n<body>\n{heading}{body_html}\n</body>\n</html>\n"
    )


def build_plain_markdown(input_path: str | Path, output_path: str | Path) -> Path:
    """Schreibt eine `.md`-Datei als HTML oder PDF (Endung von `output_path`)."""
    source_path = Path(input_path)
    html = render_plain_markdown_html(source_path.read_text(encoding="utf-8"))
    html = absolutize_local_image_sources(html, source_path.parent)
    target = validate_export_output_path(output_path, allowed_suffixes={".pdf", ".html"})
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.suffix.lower() == ".html":
        target.write_text(html, encoding="utf-8")
        return target
    return Path(write_pdf_from_html(html, target))
