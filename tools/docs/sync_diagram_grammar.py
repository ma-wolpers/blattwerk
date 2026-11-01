#!/usr/bin/env python3
"""Überträgt die Diagramm-Registrierung in die VS-Code-Grammatik und `extension.ts`.

Die Grammatik ist JSON und kann die Registrierung nicht importieren. Damit es dennoch
nur eine Quelle gibt, schreibt dieses Werkzeug die Blocknamen, Schlüsselwörter und
Optionsnamen aus `diagram_block_catalog.py` und `BLOCK_ALLOWED_OPTIONS` in die drei
Regex-Kataloge. `tools/ci/guardrails_extension_sync.py` prüft das Ergebnis.

Aufruf: `python tools/docs/sync_diagram_grammar.py`
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.core.blatt_validator_constants import BLOCK_ALLOWED_OPTIONS, KNOWN_BLOCK_TYPES  # noqa: E402
from app.core.diagram_block_catalog import DIAGRAM_BLOCKS  # noqa: E402

GRAMMAR = ROOT / "vscode-extension/blattwerk-language/syntaxes/blattwerk-injection.tmLanguage.json"
EXTENSION = ROOT / "vscode-extension/blattwerk-language/src/extension.ts"
DIAGRAM_SCOPE = "meta.block.diagram.blattwerk"
GENERAL_SCOPE = "meta.block.blattwerk"


def diagram_keywords() -> list[str]:
    """Alle Schlüsselwörter der Diagrammblöcke, sortiert und ohne Dubletten."""
    return sorted({word for spec in DIAGRAM_BLOCKS for word in spec.keywords})


def _merged_alternatives(existing: str, required: set[str]) -> str:
    """Ergänzt fehlende Alternativen hinten und entfernt unbekannte Blockdopplungen nicht."""
    present = existing.split("|")
    return "|".join(present + sorted(required - set(present)))


def _diagram_pattern() -> dict:
    """Grammatikmuster aller Diagrammblöcke: Marker nach der Einrückung, Schlüsselwörter."""
    names = "|".join(sorted(spec.name for spec in DIAGRAM_BLOCKS))
    words = "|".join(diagram_keywords())
    keyword_scope = "keyword.other.diagram.blattwerk"
    return {
        "name": DIAGRAM_SCOPE,
        "begin": f"^(\\s*)(:::(?:{names}))(?=\\s|$)",
        "beginCaptures": {"2": {"name": "keyword.control.blattwerk"}},
        "end": "^(\\s*:::)\\s*$",
        "endCaptures": {"1": {"name": "keyword.control.blattwerk"}},
        "patterns": [
            {"match": "\\b([a-z_]+)\\b(?==)", "name": "variable.parameter.blattwerk"},
            {
                "match": f"(?i)^\\s*([§%&])(?:\\s+({words})(?=\\s|$))?",
                "captures": {"1": {"name": "keyword.control.blattwerk"}, "2": {"name": keyword_scope}},
            },
            {"match": f"(?i)^\\s*({words})(?=\\s|$)", "captures": {"1": {"name": keyword_scope}}},
            {"match": '(?<==)("[^"]*"|[^\\s]+)', "name": "string.unquoted.blattwerk"},
        ],
    }


def sync_grammar(grammar: dict) -> dict:
    """Setzt das Diagrammmuster und ergänzt die allgemeinen Block- und Optionskataloge."""
    blocks = {name for name in KNOWN_BLOCK_TYPES if name != "raw"}
    options = {option for values in BLOCK_ALLOWED_OPTIONS.values() for option in values}
    patterns = [p for p in grammar["patterns"] if p.get("name") not in (DIAGRAM_SCOPE, "meta.block.structogram.blattwerk")]
    position = next(i for i, p in enumerate(patterns) if p.get("name") == GENERAL_SCOPE)
    patterns.insert(position, _diagram_pattern())
    for pattern in patterns:
        for key in ("begin", "match"):
            value = pattern.get(key)
            if pattern.get("name") != DIAGRAM_SCOPE and isinstance(value, str) and ":::(?:" in value:
                pattern[key] = re.sub(r"(:::\(\?:)([^)]+)(\))", lambda m: m[1] + _merged_alternatives(m[2], blocks) + m[3], value, count=1)
        if pattern.get("name") == GENERAL_SCOPE:
            for inner in pattern["patterns"]:
                match = inner.get("match")
                if isinstance(match, str) and re.search(r"\\b\(([^)]+)\)\\b\(\?==\)", match):
                    inner["match"] = re.sub(
                        r"(\\b\()([^)]+)(\)\\b\(\?==\))",
                        lambda m: m[1] + _merged_alternatives(m[2], options) + m[3],
                        match,
                        count=1,
                    )
    grammar["patterns"] = patterns
    return grammar


def sync_extension(text: str) -> str:
    """Ergänzt die Blockliste in der `hasDirective`-Regex von `extension.ts`."""
    blocks = {name for name in KNOWN_BLOCK_TYPES if name != "raw"}
    return re.sub(r"(:::\()([^)]+)(\)\\b/m)", lambda m: m[1] + _merged_alternatives(m[2], blocks) + m[3], text, count=1)


def _read(path: Path) -> tuple[str, str]:
    """Liest eine Datei unverändert und merkt sich ihr Zeilenende."""
    raw = path.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in raw else "\n"
    return raw.replace("\r\n", "\n"), newline


def main() -> int:
    """Schreibt Grammatik und `extension.ts`."""
    text, newline = _read(GRAMMAR)
    updated = json.dumps(sync_grammar(json.loads(text)), ensure_ascii=False, indent=2) + "\n"
    GRAMMAR.write_bytes(updated.replace("\n", newline).encode("utf-8"))
    text, newline = _read(EXTENSION)
    EXTENSION.write_bytes(sync_extension(text).replace("\n", newline).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
