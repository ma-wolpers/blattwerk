"""Klassifikation alter `.md`-Dateien: explizite Signalmatrix, keine Prioritätskette.

Reine Funktion `classify(name, text)`; GUI-Migrationsleiste und Batch-CLI
nutzen exakt dieselbe Funktion, der Editorzustand fließt nie ein.

Starke Signale (jedes impliziert ein Ziel):
    S_LEGACY_PRES / S_LEGACY_TEST  historisches `mode` (nur über `legacy_decode`)
    S_DT                           gültiger `document_type` eines Blattwerk-Typs
    S_KZ_PATH                      Dateiname endet auf `.kwe.md` (ganzer Name)
    S_KZ_META                      Kurzentwurf-Identitäts-/Support-Keys
    S_KZ_DSL                       Identitätskey + Phasen-Header/DSL-Marker
    S_WS                           Titel+Fach+Thema + Blattwerk-spezifischer Block
Sonder-Signale: M_DT_MD (`document_type: markdown`, kein Ziel),
X_DT_INVALID (ungültiger Marker), schwache Signale (nur "sieht nach Blattwerk aus").

Body-Signale zählen nur auf "Signalzeilen": außerhalb von Code-Fences und
nicht mit ≥ 4 Leerzeichen bzw. Tab eingerückt (potenzielle eingerückte
Codeblöcke). Ein verpasstes Signal führt höchstens zu `unklar`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import yaml

from ..blatt_kern_shared_data import CONTROL_MARKERS
from ..blatt_validator_constants import KNOWN_BLOCK_TYPES
from ..document_semantics import Canonical, Invalid, canonicalize_document_type
from ..frontmatter import frontmatter_bounds, load_frontmatter_yaml
from .kurzentwurf_signals import (
    KURZENTWURF_IDENTITY_DETECTION_KEYS,
    KURZENTWURF_LEGACY_DETECTION_SUPPORT_KEYS,
    KURZENTWURF_MARKER_RE,
    KURZENTWURF_PHASE_HEADER_RE,
)
from .legacy_decode import decode_legacy_target_hint, has_weak_legacy_mode

STATUS_SAFE = "sicher"
STATUS_UNCLEAR = "unklar"
STATUS_CONFLICT = "conflict"
STATUS_NOT_BLATTWERK = "kein_blattwerk"
STATUS_INVALID_MARKER = "ungueltiger_marker"

CLASSIFIER_VERSION = 1

AMBIGUOUS_BLOCK_NAMES = frozenset({"info", "raw", "table", "columns", "space", "help"})
"""Blocknamen, die mit Admonitions/Divs anderer Tools kollidieren (Docusaurus/VitePress
`:::info`, Pandoc `::: columns`) und deshalb nicht für `S_WS` zählen."""

_PSEUDO_BLOCK_TYPES = frozenset(spec.block_type for spec in CONTROL_MARKERS if spec.block_type)
SPECIFIC_BLOCK_NAMES = frozenset(KNOWN_BLOCK_TYPES) - AMBIGUOUS_BLOCK_NAMES - _PSEUDO_BLOCK_TYPES

_BLOCK_LINE_RE = re.compile(r"^:::(\w+)")
_FENCE_RE = re.compile(r"^ {0,3}(```|~~~)")
_LINE_MARKER_RE = re.compile(r"^[§%&](?=\s|$)")


@dataclass(frozen=True)
class Classification:
    """Ergebnis der Klassifikation."""

    status: str
    target_type: str | None = None
    signals: tuple[str, ...] = field(default_factory=tuple)


def iter_signal_lines(body: str):
    """Liefert die Zeilen des Rumpfs, die als Body-Signal zählen dürfen."""
    in_fence = None
    for raw_line in body.split("\n"):
        line = raw_line.rstrip("\r")
        fence = _FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)
            if in_fence is None:
                in_fence = marker
            elif in_fence == marker:
                in_fence = None
            continue
        if in_fence is not None:
            continue
        if line.startswith("\t") or line.startswith("    "):
            continue
        yield line


def _nonempty(meta: dict, key: str) -> bool:
    value = meta.get(key)
    return value is not None and str(value).strip() != ""


def _control_marker_line(line: str) -> bool:
    stripped = line.strip()
    for spec in CONTROL_MARKERS:
        pattern = spec.literal_or_regex
        if hasattr(pattern, "match"):
            if pattern.match(stripped):
                return True
        elif stripped == pattern:
            return True
    return False


def _read_frontmatter(text: str) -> tuple[dict | None, str, bool]:
    """Liefert ``(meta, body, frontmatter_vorhanden)``; meta ``None`` bei kaputtem YAML."""
    bounds = frontmatter_bounds(text)
    if bounds is None:
        return {}, text.removeprefix("﻿"), False
    try:
        meta = load_frontmatter_yaml(bounds.body(text))
    except yaml.YAMLError:
        return None, text[bounds.end :], True
    if meta is None:
        meta = {}
    if not isinstance(meta, dict):
        return None, text[bounds.end :], True
    return meta, text[bounds.end :], True


def collect_signals(name: str, text: str) -> tuple[set[str], dict[str, str], bool, bool]:
    """Sammelt Signale; liefert ``(signale, ziele_je_signal, frontmatter_vorhanden, yaml_ok)``."""
    signals: set[str] = set()
    targets: dict[str, str] = {}
    meta, body, has_frontmatter = _read_frontmatter(text)
    yaml_ok = meta is not None
    meta = meta or {}

    if name.lower().endswith(".kwe.md"):
        signals.add("S_KZ_PATH")
        targets["S_KZ_PATH"] = "kurzentwurf"

    legacy = decode_legacy_target_hint(meta)
    if legacy == "presentation":
        signals.add("S_LEGACY_PRES")
        targets["S_LEGACY_PRES"] = "presentation"
    elif legacy == "exam":
        signals.add("S_LEGACY_TEST")
        targets["S_LEGACY_TEST"] = "exam"
    elif has_weak_legacy_mode(meta):
        signals.add("W_LEGACY_MODE")

    if "document_type" in meta:
        marker = canonicalize_document_type(meta.get("document_type"))
        if isinstance(marker, Invalid):
            signals.add("X_DT_INVALID")
        elif isinstance(marker, Canonical):
            if marker.document_type == "markdown":
                signals.add("M_DT_MD")
            else:
                signals.add("S_DT")
                targets["S_DT"] = marker.document_type

    identity_count = sum(1 for key in KURZENTWURF_IDENTITY_DETECTION_KEYS if _nonempty(meta, key))
    support_count = sum(1 for key in KURZENTWURF_LEGACY_DETECTION_SUPPORT_KEYS if key in meta)
    if identity_count >= 2 or (_nonempty(meta, "Stundenthema") and support_count >= 2):
        signals.add("S_KZ_META")
        targets["S_KZ_META"] = "kurzentwurf"

    lines = list(iter_signal_lines(body))
    if identity_count >= 1 and any(
        KURZENTWURF_PHASE_HEADER_RE.match(line) or KURZENTWURF_MARKER_RE.match(line) for line in lines
    ):
        signals.add("S_KZ_DSL")
        targets["S_KZ_DSL"] = "kurzentwurf"

    block_names = {match.group(1) for line in lines if (match := _BLOCK_LINE_RE.match(line))}
    specific_blocks = block_names & SPECIFIC_BLOCK_NAMES
    if all(_nonempty(meta, key) for key in ("Titel", "Fach", "Thema")) and specific_blocks:
        signals.add("S_WS")
    if block_names & frozenset(KNOWN_BLOCK_TYPES) and not ("S_WS" in signals):
        signals.add("W_BLOCKS")
    if any(_control_marker_line(line) for line in lines):
        signals.add("W_CONTROL_MARKERS")
    if any(_LINE_MARKER_RE.match(line) for line in lines):
        signals.add("W_LINE_MARKERS")
    return signals, targets, has_frontmatter, yaml_ok


def classify(name: str, text: str) -> Classification:
    """Klassifiziert eine `.md`-Datei nach der expliziten Matrix (Plan 2.2).

    Prüfreihenfolge (jede Regel ist eine vollständige Fallunterscheidung):
        1. ungültiger Marker → `ungueltiger_marker`
        2. `document_type: markdown` → `kein_blattwerk` (nur schwache Signale)
           bzw. `conflict` (mit irgendeinem starken Signal)
        3. mehrere verschiedene Ziele aus starken Signalen → `conflict`
        4. genau ein Ziel: kurzentwurf + `S_WS` → `conflict`, sonst `sicher`
        5. kein Ziel, aber `S_WS` → `sicher` worksheet
        6. nur schwache Signale → `unklar`, sonst `kein_blattwerk`
    Kaputtes Frontmatter-YAML ergibt immer `unklar` (Signal `X_YAML`).
    """
    signals, targets, _has_frontmatter, yaml_ok = collect_signals(name, text)
    if not yaml_ok:
        return Classification(STATUS_UNCLEAR, None, tuple(sorted(signals | {"X_YAML"})))
    ordered = tuple(sorted(signals))
    strong = {s for s in signals if s.startswith("S_")}
    weak = {s for s in signals if s.startswith("W_")}

    if "X_DT_INVALID" in signals:
        return Classification(STATUS_INVALID_MARKER, None, ordered)
    if "M_DT_MD" in signals:
        return Classification(STATUS_CONFLICT if strong else STATUS_NOT_BLATTWERK, None, ordered)

    target_set = set(targets.values())
    if len(target_set) > 1:
        return Classification(STATUS_CONFLICT, None, ordered)
    if len(target_set) == 1:
        target = next(iter(target_set))
        if target == "kurzentwurf" and "S_WS" in signals:
            return Classification(STATUS_CONFLICT, None, ordered)
        return Classification(STATUS_SAFE, target, ordered)
    if "S_WS" in signals:
        return Classification(STATUS_SAFE, "worksheet", ordered)
    if weak:
        return Classification(STATUS_UNCLEAR, None, ordered)
    return Classification(STATUS_NOT_BLATTWERK, None, ordered)
