"""Positionsregeln der Klausur-Trenner (Invariante I5): wo `--hm` stehen darf.

Reine Prüffunktionen über die Blockliste; `exam_parts.resolve_exam_parts`
setzt aus ihren Codes die Probleme zusammen, der Validator meldet sie.
"""

from __future__ import annotations

_TASK_RELATED = frozenset({"task", "subtask", "solution"})


def aid_split_position_problem(blocks, index: int, start: int = 0) -> str | None:
    """Prüft die Positionsregel „nur zwischen Top-Level-Aufgaben“.

    Args:
        blocks: Blockliste des Dokuments.
        index: Blockindex des geprüften Trenners.
        start: Erster Blockindex, der für „Aufgabe davor“ zählt (bei einem
            Deckblatt: direkt nach dem Deckblatt-Trenner, damit Teil A nicht
            leer sein darf).

    Returns:
        ``"KL004"`` (keine Aufgabe davor/danach oder innerhalb von `:::columns`),
        ``"KL005"`` (der nächste aufgabenbezogene Block ist kein `task`) oder ``None``.
    """
    before = [block_type for block_type, _o, _c in blocks[start:index]]
    after = [block_type for block_type, _o, _c in blocks[index + 1 :]]
    if "task" not in before or "task" not in after:
        return "KL004"
    if before.count("columns") > before.count("endcolumns"):
        return "KL004"
    return _next_task_problem(after)


def aid_cover_position_problem(blocks, index: int) -> str | None:
    """Prüft den Deckblatt-Trenner (erster von zwei `--hm`).

    Returns:
        ``"KL007"`` (vor dem Deckblatt-Trenner steht eine Aufgabe, Teilaufgabe
        oder Lösung), ``"KL004"`` (keine Aufgabe danach oder innerhalb von
        `:::columns`), ``"KL005"`` (nächster aufgabenbezogener Block kein `task`)
        oder ``None``.
    """
    before = [block_type for block_type, _o, _c in blocks[:index]]
    after = [block_type for block_type, _o, _c in blocks[index + 1 :]]
    if any(block_type in _TASK_RELATED for block_type in before):
        return "KL007"
    if "task" not in after or before.count("columns") > before.count("endcolumns"):
        return "KL004"
    return _next_task_problem(after)


def _next_task_problem(after) -> str | None:
    """``"KL005"``, wenn der nächste aufgabenbezogene Block kein `task` ist."""
    next_related = next((block_type for block_type in after if block_type in _TASK_RELATED), None)
    return None if next_related == "task" else "KL005"
