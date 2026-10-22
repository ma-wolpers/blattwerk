"""Aus `CONTROL_MARKERS` abgeleitete Erkennung von Kontrollmarker-Zeilen.

`CONTROL_MARKERS` (`blatt_kern_shared_data.py`) bleibt die einzige normative
Quelle der Syntax; dieses Modul leitet daraus ab, was sonst an mehreren
Stellen von Hand gepflegt würde:

* `is_control_marker_line` -- Validator BL005 („Trenner in offenem Block“).
  Ein Marker mit `detect_prefix` zählt schon über sein Präfix (auch ein
  ungültiger `--#` ohne Titel ist ein Trenner-Versuch).
* `CONTROL_MARKER_LINE_REGEX` -- Hervorhebung im Blattwerk-Editor und
  (per Guardrail `_check_control_marker_grammar_sync` erzwungen) in der
  VS-Code-Grammatik. Gruppe 1 = Einrückung, Gruppe 2 = Marker; `(?<=\\S)`
  hält nachgestellte Leerzeichen aus Gruppe 2 heraus (auch nach `--# Titel`).
"""

from __future__ import annotations

import re

from .blatt_kern_shared_data import CONTROL_MARKERS, ControlMarkerSpec

_CAPTURE_GROUP_OPEN = re.compile(r"(?<!\\)\((?!\?)")


def control_marker_fragment(spec: ControlMarkerSpec) -> str:
    """Regex-Fragment eines Markers ohne Anker und ohne Capture-Gruppen.

    Literale werden escaped; bei Mustern entfallen `^`, ein abschließendes
    `\\s*` und `$` (die Zeilen-Regex ergänzt sie einheitlich), Capture-Gruppen
    werden nicht-erfassend, damit die Gruppen der Zeilen-Regex stabil bleiben.
    """
    if spec.kind == "literal":
        return re.escape(spec.literal_or_regex)
    source = spec.literal_or_regex.pattern
    source = source.removeprefix("^").removesuffix("$").removesuffix(r"\s*")
    return _CAPTURE_GROUP_OPEN.sub("(?:", source)


CONTROL_MARKER_LINE_REGEX = r"^(\s*)(" + "|".join(control_marker_fragment(spec) for spec in CONTROL_MARKERS) + r")(?<=\S)\s*$"
_CONTROL_MARKER_LINE_PATTERN = re.compile(CONTROL_MARKER_LINE_REGEX)


def control_marker_line_match(line: str) -> re.Match | None:
    """Treffer einer gültigen Kontrollmarker-Zeile (für die Hervorhebung)."""
    return _CONTROL_MARKER_LINE_PATTERN.match(line)


def is_control_marker_line(stripped_line: str) -> bool:
    """Ob eine (bereits gestrippte) Zeile ein Kontrollmarker oder ein Versuch davon ist."""
    for spec in CONTROL_MARKERS:
        if spec.detect_prefix and stripped_line.startswith(spec.detect_prefix):
            return True
        if spec.kind == "literal" and stripped_line == spec.literal_or_regex:
            return True
        if spec.kind == "pattern" and spec.literal_or_regex.match(stripped_line):
            return True
    return False
