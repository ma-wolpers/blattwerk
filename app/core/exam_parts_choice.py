"""Wahlbereiche aus den Wahlteil-Trennern `--w[k] Titel` / `--w Titel` bestimmen.

Regeln (Nutzerentscheidung, Wunschliste Schritt 6b):

* `--w[k]` eröffnet einen Wahlbereich, jedes folgende `--w` startet einen
  weiteren Wahlteil desselben Bereichs.
* Der Bereich endet am nächsten `--hm` (A/B-Trenner) oder am Dokumentende;
  danach kann ein neuer Bereich mit `--w[k]` beginnen.
* Strukturfehler: `--w` ohne offenen Bereich (`KL008`), `--w[k]` in einem
  offenen Bereich (`KL009`), `k` keine ganze Zahl mit 1 ≤ k < n (`KL010`),
  Position (`KL004`/`KL005`, siehe `exam_parts_position.choice_position_problem`).

Gleiche Punkte je Bereich prüft der Validator (`KL011`), weil dafür das
Punktmodell nötig ist.
"""

from __future__ import annotations

from dataclasses import dataclass

from .exam_parts_position import AID_SPLIT_BLOCK, CHOICE_SPLIT_BLOCK, choice_position_problem

_K_PATTERN_DIGITS = "0123456789"


@dataclass(frozen=True)
class ChoiceRegion:
    """Ein Wahlbereich: Blockindizes seiner `--w`-Trenner und die Anzahl `k`."""

    marker_indices: tuple[int, ...]
    k: int


def choice_split_indices(blocks) -> list[int]:
    """Blockindizes aller `choicesplit`-Pseudoblöcke in Dokumentreihenfolge."""
    return [index for index, (block_type, _o, _c) in enumerate(blocks) if block_type == CHOICE_SPLIT_BLOCK]


def parse_choice_k(raw: str) -> int | None:
    """`[k]` (mit Klammern, wie vom Parser erfasst) → ganze Zahl oder ``None``."""
    inner = str(raw or "").strip()[1:-1].strip()
    return int(inner) if inner and all(ch in _K_PATTERN_DIGITS for ch in inner) else None


def resolve_choice_regions(blocks, separator_indices: list[int]):
    """Wahlbereiche und Strukturprobleme der `--w`-Trenner.

    Args:
        blocks: Blockliste des Dokuments.
        separator_indices: Alle Teil-Trenner in Dokumentreihenfolge, also
            `--w` und der A/B-`--hm` (ohne Deckblatt-Trenner).

    Returns:
        ``(regions, problems)`` mit `problems` als Liste ``(code, blockindex)``.
    """
    problems: list[tuple[str, int]] = []
    regions: list[ChoiceRegion] = []
    open_markers: list[int] = []
    open_k: str | None = None
    ends = separator_indices[1:] + [len(blocks)]
    for index, end in zip(separator_indices, ends):
        block_type, options, _content = blocks[index]
        if block_type == AID_SPLIT_BLOCK:
            _close(open_markers, open_k, regions, problems)
            open_markers, open_k = [], None
            continue
        raw_k = str((options or {}).get("k") or "")
        if raw_k and open_markers:
            problems.append(("KL009", index))
        elif raw_k:
            open_markers, open_k = [], raw_k
        elif not open_markers:
            problems.append(("KL008", index))
            continue
        open_markers.append(index)
        position = choice_position_problem(blocks, index, end)
        if position:
            problems.append((position, index))
    _close(open_markers, open_k, regions, problems)
    return regions, problems


def _close(markers: list[int], raw_k: str | None, regions: list[ChoiceRegion], problems: list) -> None:
    """Schließt einen offenen Bereich ab und prüft `k` gegen die Teilanzahl."""
    if not markers:
        return
    k = parse_choice_k(raw_k or "")
    if k is None or not 1 <= k < len(markers):
        problems.append(("KL010", markers[0]))
        return
    regions.append(ChoiceRegion(tuple(markers), k))
