"""Synchronitaets-Guardrails zwischen Core-Katalogen und VSCode-Extension: Marker-Token,
Blocktypen und Optionsschluessel (TextMate-Grammatik und ``extension.ts``).
"""

from __future__ import annotations

import json
import re

from guardrails_common import (
    _read,
)


def _check_marker_token_consistency(errors: list[str]) -> None:
    """Ensure marker docs/highlighting stay aligned with core §/%/& token set."""
    target_files = (
        "app/ui/blatt_ui_editor.py",
        "vscode-extension/blattwerk-language/syntaxes/blattwerk-injection.tmLanguage.json",
        "docs/nutzer/NUTZERHANDBUCH.md",
    )

    outdated_patterns = ("[§$&]", "§/$/&")
    for rel_path in target_files:
        text = _read(rel_path)
        for pattern in outdated_patterns:
            if pattern in text:
                errors.append(
                    f"{rel_path}: outdated marker token notation detected ({pattern}); expected §/%/&"
                )


def _load_core_block_and_option_catalogs(errors: list[str]) -> tuple[set[str], set[str]]:
    """Read canonical block/option catalogs from validator constants."""
    try:
        from app.core import blatt_validator as validator
    except Exception as exc:  # pragma: no cover - defensive guardrail fallback
        errors.append(f"app/core/blatt_validator.py: import failed for guardrail sync check ({exc})")
        return set(), set()

    core_block_types = {
        str(value).strip()
        for value in getattr(validator, "KNOWN_BLOCK_TYPES", set())
        if isinstance(value, str) and value.strip() and value.strip() != "raw"
    }

    core_option_keys: set[str] = set()
    option_map = getattr(validator, "BLOCK_ALLOWED_OPTIONS", {})
    if isinstance(option_map, dict):
        for values in option_map.values():
            if isinstance(values, (set, frozenset, tuple, list)):
                core_option_keys.update(
                    str(value).strip()
                    for value in values
                    if isinstance(value, str) and value.strip()
                )

    return core_block_types, core_option_keys


def _extract_alternatives(regex_text: str, marker: str) -> set[str]:
    """Extract alternatives from a regex fragment like :::(?:a|b|c) or :::(a|b|c)."""
    if not regex_text or marker not in regex_text:
        return set()

    if marker.endswith("(?:"):
        close_token = ")"
    else:
        close_token = ")"

    start = regex_text.find(marker)
    if start < 0:
        return set()
    start += len(marker)
    end = regex_text.find(close_token, start)
    if end < 0:
        return set()

    return {
        token.strip()
        for token in regex_text[start:end].split("|")
        if token.strip()
    }


def _extract_block_types_from_tm_language(rel_path: str, errors: list[str]) -> tuple[set[str], set[str]]:
    """Extract block type alternatives from begin and self-closing grammar regexes."""
    try:
        payload = json.loads(_read(rel_path))
    except Exception as exc:
        errors.append(f"{rel_path}: invalid JSON ({exc})")
        return set(), set()

    begin_set: set[str] = set()
    self_closing_set: set[str] = set()

    for pattern in payload.get("patterns", []):
        if not isinstance(pattern, dict):
            continue
        begin_regex = pattern.get("begin")
        if isinstance(begin_regex, str) and ":::(?:" in begin_regex:
            begin_set = _extract_alternatives(begin_regex, ":::(?:")

        match_regex = pattern.get("match")
        if isinstance(match_regex, str) and ":::(?:" in match_regex:
            self_closing_set = _extract_alternatives(match_regex, ":::(?:")

    if not begin_set:
        errors.append(f"{rel_path}: could not extract block types from begin regex")
    if not self_closing_set:
        errors.append(f"{rel_path}: could not extract block types from self-closing regex")

    return begin_set, self_closing_set


def _extract_option_keys_from_tm_language(rel_path: str, errors: list[str]) -> set[str]:
    """Extract option-key highlighting catalog from the general block pattern (`meta.block.blattwerk`).

    Nur dieses Muster gilt fuer alle Blocktypen; spezielle Blockmuster (z. B.
    `meta.block.struktogramm.blattwerk`) haben eigene, kleinere Optionslisten
    und duerfen nicht als Katalog gelesen werden.
    """
    try:
        payload = json.loads(_read(rel_path))
    except Exception:
        return set()

    for pattern in payload.get("patterns", []):
        if not isinstance(pattern, dict) or pattern.get("name") != "meta.block.blattwerk":
            continue
        inner_patterns = pattern.get("patterns")
        if not isinstance(inner_patterns, list):
            continue
        for inner in inner_patterns:
            if not isinstance(inner, dict):
                continue
            match_regex = inner.get("match")
            if not isinstance(match_regex, str):
                continue

            capture = re.search(r"\\b\(([^)]+)\)\\b\(\?==\)", match_regex)
            if capture:
                return {
                    token.strip()
                    for token in capture.group(1).split("|")
                    if token.strip()
                }

    errors.append(f"{rel_path}: could not extract option-key regex alternatives")
    return set()


def _extract_block_types_from_extension_ts(rel_path: str, errors: list[str]) -> set[str]:
    """Extract block type alternatives from diagnostics hasDirective regex."""
    text = _read(rel_path)
    capture = re.search(r":::\(([^)]+)\)\\b/m", text)
    if not capture:
        errors.append(f"{rel_path}: could not extract hasDirective block type regex")
        return set()

    return {
        token.strip()
        for token in capture.group(1).split("|")
        if token.strip()
    }


def _check_extension_validator_sync(errors: list[str]) -> None:
    """Ensure validator block/option catalogs stay in sync with extension regex catalogs."""
    core_block_types, core_option_keys = _load_core_block_and_option_catalogs(errors)
    if not core_block_types:
        return

    tm_path = "vscode-extension/blattwerk-language/syntaxes/blattwerk-injection.tmLanguage.json"
    ts_path = "vscode-extension/blattwerk-language/src/extension.ts"

    begin_blocks, self_closing_blocks = _extract_block_types_from_tm_language(tm_path, errors)
    ts_blocks = _extract_block_types_from_extension_ts(ts_path, errors)
    tm_option_keys = _extract_option_keys_from_tm_language(tm_path, errors)

    if begin_blocks and self_closing_blocks and begin_blocks != self_closing_blocks:
        errors.append(
            f"{tm_path}: begin/self-closing block catalogs differ -> "
            f"begin-only={sorted(begin_blocks - self_closing_blocks)}, "
            f"self-closing-only={sorted(self_closing_blocks - begin_blocks)}"
        )

    if begin_blocks:
        missing_in_tm = sorted(core_block_types - begin_blocks)
        if missing_in_tm:
            errors.append(
                f"{tm_path}: missing block types from validator catalog -> {missing_in_tm}"
            )

    if ts_blocks:
        missing_in_ts = sorted(core_block_types - ts_blocks)
        if missing_in_ts:
            errors.append(
                f"{ts_path}: missing block types from validator catalog -> {missing_in_ts}"
            )

    if tm_option_keys:
        missing_option_keys = sorted(core_option_keys - tm_option_keys)
        if missing_option_keys:
            errors.append(
                f"{tm_path}: missing option keys from validator BLOCK_ALLOWED_OPTIONS -> {missing_option_keys}"
            )




INLINE_STYLE_SCOPE = "markup.other.inline-style.blattwerk"


def _check_inline_style_grammar_sync(errors: list[str]) -> None:
    """Die VS-Code-Grammatik muss Inline-Stile mit exakt der Parser-Regex hervorheben.

    Geprueft werden das Muster auf Dokumentebene und das innerhalb der Bloecke
    (`meta.block.blattwerk`): beide muessen `STYLE_MARKER_REGEX` aus
    `app/core/inline_markup/style_spans.py` sein, sonst markiert VS Code etwas
    anderes als der Blattwerk-Editor bzw. der Parser auswertet (AGENTS.md Regel 5).
    """
    from app.core.inline_markup.style_spans import STYLE_MARKER_REGEX

    tm_path = "vscode-extension/blattwerk-language/syntaxes/blattwerk-injection.tmLanguage.json"
    grammar = json.loads(_read(tm_path))
    top_level = [p for p in grammar.get("patterns", []) if p.get("name") == INLINE_STYLE_SCOPE]
    blocks = [p for p in grammar.get("patterns", []) if p.get("name") == "meta.block.blattwerk"]
    in_blocks = [
        p for block in blocks for p in block.get("patterns", []) if p.get("name") == INLINE_STYLE_SCOPE
    ]
    for label, found in (("top-level", top_level), ("block", in_blocks)):
        if len(found) != 1:
            errors.append(f"{tm_path}: expected exactly one {label} pattern '{INLINE_STYLE_SCOPE}', found {len(found)}")
        elif found[0].get("match") != STYLE_MARKER_REGEX:
            errors.append(
                f"{tm_path}: {label} inline-style regex differs from STYLE_MARKER_REGEX "
                f"({found[0].get('match')!r} != {STYLE_MARKER_REGEX!r})"
            )


CONTROL_SCOPE = "keyword.control.blattwerk"


def _check_control_marker_grammar_sync(errors: list[str]) -> None:
    """Die VS-Code-Grammatik muss Kontrollmarker mit der aus `CONTROL_MARKERS` abgeleiteten Regex hervorheben.

    Genau ein Top-Level-Muster mit Capture 2 = `keyword.control.blattwerk` und
    `match` == `control_markers.CONTROL_MARKER_LINE_REGEX` (dieselbe Regex nutzt
    der Blattwerk-Editor). Ein neuer Marker in `CONTROL_MARKERS` ohne
    Grammatik-Update faellt damit sofort auf (AGENTS.md Regel 5).
    """
    from app.core.control_markers import CONTROL_MARKER_LINE_REGEX

    tm_path = "vscode-extension/blattwerk-language/syntaxes/blattwerk-injection.tmLanguage.json"
    grammar = json.loads(_read(tm_path))
    found = [
        p for p in grammar.get("patterns", [])
        if "match" in p and p.get("captures", {}).get("2", {}).get("name") == CONTROL_SCOPE
    ]
    if len(found) != 1:
        errors.append(f"{tm_path}: expected exactly one top-level control-marker pattern, found {len(found)}")
    elif found[0]["match"] != CONTROL_MARKER_LINE_REGEX:
        errors.append(
            f"{tm_path}: control-marker regex differs from CONTROL_MARKER_LINE_REGEX "
            f"({found[0]['match']!r} != {CONTROL_MARKER_LINE_REGEX!r})"
        )
