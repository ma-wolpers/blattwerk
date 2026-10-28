"""Klausuren: Lernhilfe-Abzug `(−xP Lh)` -- Typ, KL013, SL023, Erwartungshorizont."""

from __future__ import annotations

import re

from app.core.blatt_validator import inspect_markdown_text
from app.core.exam_expectation_horizon import build_expectation_horizon_html
from app.core.expectation_kinds import deduction_label_for, is_deduction_only_kind, resolve_expectation_kind

HEAD = "---\nTitel: T\nFach: M\nThema: X\n---\n"
HELP = ":::help title=\"Tipp\"\nDenk an die Formel.\n:::\n"


def _codes(body, document_type="exam"):
    diagnostics = inspect_markdown_text(HEAD + body, document_type=document_type).diagnostics
    return [d.code for d in diagnostics if d.code in {"KL013", "SL023"}]


def _task(solution_lines, extra=""):
    return f":::task points=2 afb=1\nA\n:::\n{extra}:::solution\n" + "".join(f"{line}\n" for line in solution_lines) + ":::\n"


def test_lernhilfe_kind_is_deduction_only_with_own_label():
    kind = resolve_expectation_kind("Lh")
    assert kind is not None and kind.key == "lernhilfe"
    assert is_deduction_only_kind("lernhilfe")
    assert not is_deduction_only_kind("ansatz")
    assert deduction_label_for("lernhilfe") == "Abzug bei Nutzung der Lernhilfe"
    assert deduction_label_for("begruendung") == "Abzug je Fehler"
    assert deduction_label_for(None) == "Abzug je Fehler"


def test_task_with_help_but_without_help_deduction_warns():
    assert _codes(_task(["1. Ergebnis (2P)"], HELP)) == ["KL013"]


def test_help_deduction_silences_kl013():
    assert _codes(_task(["1. Ergebnis (2P)", "2. Lernhilfe genutzt (−1P Lh)"], HELP)) == []


def test_ordinary_deduction_does_not_count_as_help_deduction():
    assert _codes(_task(["1. Ergebnis (2P)", "2. Je Fehler (−0,5P)"], HELP)) == ["KL013"]


def test_subtask_help_accepts_deduction_in_task_solution():
    body = (
        ":::task afb=1\nA\n:::\n:::subtask points=1 afb=1\na\n:::\n" + HELP
        + ":::subtask points=1 afb=1\nb\n:::\n"
        ":::solution target=task\n1. Lernhilfe genutzt (−1P Lh)\n:::\n"
        ":::solution target=a\n1. Ergebnis (1P)\n:::\n:::solution target=b\n1. Ergebnis (1P)\n:::\n"
    )
    assert _codes(body) == []


def test_no_check_outside_exams_and_without_help():
    assert _codes(_task(["1. Ergebnis (2P)"], HELP), document_type="worksheet") == []
    assert _codes(_task(["1. Ergebnis (2P)"])) == []


def test_lernhilfe_type_without_minus_is_sl023():
    assert _codes(_task(["1. Ergebnis (2P Lh)"], HELP)) == ["SL023", "KL013"]


def test_expectation_horizon_labels_the_help_deduction():
    html, _diagnostics = build_expectation_horizon_html(
        HEAD + _task(["1. Ergebnis (2P)", "2. Lernhilfe genutzt (−1P Lh)", "3. Je Fehler (−0,5P)"], HELP)
    )

    assert "Abzug bei Nutzung der Lernhilfe:</span> <span class='kind' title='Lernhilfe'>🛟</span>" in html
    assert "Abzug je Fehler:</span>" in html
    legend = re.search(r"<h2>Erwartungstypen</h2>.*?</table>", html, re.S).group(0)
    assert "Lernhilfe" in legend
