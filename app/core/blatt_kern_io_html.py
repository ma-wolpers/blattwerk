"""HTML post-processing helpers for image paths and sizing."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote


def absolutize_local_image_sources(html, base_dir):
    """Wandelt relative Bildpfade in absolute `file://`-URIs um."""
    base_dir = Path(base_dir)

    def resolve_src(src):
        source = (src or "").strip()
        if not source:
            return source

        if source.startswith(("http://", "https://", "file://", "data:", "#", "//")):
            return source

        if re.match(r"^[a-zA-Z]+:", source) and not re.match(
            r"^[a-zA-Z]:[\\/]", source
        ):
            return source

        if re.match(r"^[a-zA-Z]:[\\/]", source):
            return Path(source).resolve().as_uri()

        decoded_source = unquote(source)
        return (base_dir / decoded_source).resolve().as_uri()

    pattern = re.compile(
        r'(<img\b[^>]*\bsrc\s*=\s*)(["\'])(.*?)(\2)', flags=re.IGNORECASE
    )

    def repl(match):
        prefix = match.group(1)
        quote = match.group(2)
        src = match.group(3)
        return f"{prefix}{quote}{resolve_src(src)}{quote}"

    return pattern.sub(repl, html)


def apply_image_size_options(html):
    """Übernimmt Bildgrößenoptionen aus dem `title`-Attribut in CSS-Styles.

    Unterstützte Schlüssel im title:
    - `w` / `width`
    - `h` / `height`
    - `maxw` / `max-width`
    """
    img_pattern = re.compile(r"<img\b[^>]*>", flags=re.IGNORECASE)
    title_pattern = re.compile(r"\btitle\s*=\s*([\"'])(.*?)\1", flags=re.IGNORECASE)
    style_pattern = re.compile(r"\bstyle\s*=\s*([\"'])(.*?)\1", flags=re.IGNORECASE)

    def valid_css_size(value):
        return bool(
            re.fullmatch(
                r"(?:\d+(?:\.\d+)?(?:px|%|cm|mm|in|pt|em|rem|vw|vh|vmin|vmax)?|auto)",
                value.strip(),
                flags=re.IGNORECASE,
            )
        )

    def parse_title_options(title_text):
        normalized = title_text.replace(";", " ").replace(",", " ")
        tokens = [token for token in normalized.split() if token.strip()]
        if not tokens:
            return None

        key_map = {
            "w": "width",
            "width": "width",
            "h": "height",
            "height": "height",
            "maxw": "max-width",
            "max-width": "max-width",
        }

        styles = {}
        for token in tokens:
            if "=" not in token:
                return None
            key, value = token.split("=", 1)
            css_key = key_map.get(key.strip().lower())
            if not css_key:
                return None
            css_value = value.strip()
            if not valid_css_size(css_value):
                return None
            styles[css_key] = css_value

        return styles or None

    def apply_to_tag(tag):
        title_match = title_pattern.search(tag)
        if not title_match:
            return tag

        styles = parse_title_options(title_match.group(2))
        if not styles:
            return tag

        existing_style = ""
        style_match = style_pattern.search(tag)
        if style_match:
            existing_style = style_match.group(2).strip()

        style_parts = []
        if existing_style:
            style_parts.append(existing_style.rstrip(";"))
        style_parts.extend(f"{key}:{value}" for key, value in styles.items())
        merged_style = "; ".join(style_parts)

        updated_tag = title_pattern.sub("", tag, count=1)
        if style_match:
            updated_tag = style_pattern.sub(
                f'style="{merged_style}"', updated_tag, count=1
            )
        else:
            updated_tag = updated_tag.replace("<img", f'<img style="{merged_style}"', 1)

        return re.sub(r"\s+>", ">", updated_tag)

    return img_pattern.sub(lambda m: apply_to_tag(m.group(0)), html)
