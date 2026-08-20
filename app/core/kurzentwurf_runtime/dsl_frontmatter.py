"""Kurzentwurf-DSL: YAML-Frontmatter- und `@key:`-Metazeilen-Parsing.

Zwei syntaktische Varianten teilen sich dieselbe Key-Kanonisierung
(`_canonical_meta_key`): ein YAML-`---`-Frontmatterblock am Dokumentanfang
(`_parse_front_matter`) und einzelne `@title:`/`@start:`-Metazeilen
innerhalb des Dokuments (in `dsl.py` per `_META_RE` erkannt). Beide
akzeptieren dieselben deutschen/englischen Alias-Keys.

`TITLE_KEYS`/`SUBTITLE_KEYS`/`START_KEYS` sind öffentlich benannt (statt
`_TITLE_KEYS` mit Unterstrich-Präfix), damit `app/core/markdown_conventions.py`
(Doku-Collector) sie als normative Quelle für die Kurzentwurf-Identitäts-
Metadaten importieren kann, ohne auf private Namen zuzugreifen.
"""

from __future__ import annotations

import re

from .model import Diagnostic

_META_RE = re.compile(
    r"^@(?P<key>title|subtitle|start|start_time|stundenthema|lerngruppe|startuhrzeit|startzeit)\s*:\s*(?P<value>.+?)\s*$",
    re.IGNORECASE,
)

TITLE_KEYS = {"title", "stundenthema"}
SUBTITLE_KEYS = {"subtitle", "lerngruppe"}
START_KEYS = {"start", "start_time", "startuhrzeit", "startzeit"}


def _canonical_meta_key(raw_key: str) -> str | None:
    normalized = "_".join(str(raw_key or "").strip().lower().replace("-", " ").split())
    if normalized in TITLE_KEYS:
        return "title"
    if normalized in SUBTITLE_KEYS:
        return "subtitle"
    if normalized in START_KEYS:
        return "start"
    return None


def _strip_optional_quotes(text: str) -> str:
    value = str(text or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1].strip()
    return value


def _parse_front_matter(
    lines: list[str],
    diagnostics: list[Diagnostic],
) -> tuple[dict[str, str], int]:
    metadata: dict[str, str] = {}

    if not lines:
        return metadata, 0

    first_non_empty = 0
    while first_non_empty < len(lines) and not lines[first_non_empty].strip():
        first_non_empty += 1

    if first_non_empty >= len(lines) or lines[first_non_empty].strip() != "---":
        return metadata, 0

    line_index = first_non_empty + 1
    while line_index < len(lines):
        stripped = lines[line_index].strip()
        if stripped == "---":
            return metadata, line_index + 1

        if not stripped:
            line_index += 1
            continue

        if ":" not in stripped:
            line_index += 1
            continue

        key, value = stripped.split(":", 1)
        canonical_key = _canonical_meta_key(key)
        if canonical_key is not None:
            metadata[canonical_key] = _strip_optional_quotes(value.strip())
        line_index += 1

    diagnostics.append(
        Diagnostic(
            code="KZF045",
            severity="error",
            message="Front-Matter wurde nicht mit --- geschlossen.",
            line=first_non_empty + 1,
        )
    )
    return metadata, len(lines)
