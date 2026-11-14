"""Nachbearbeitung geparster Blocklisten: Aufgabennummern, Teilaufgaben, Hilfe-Referenzen, Sichtbarkeit.

Arbeitet auf dem Ergebnis von `blatt_kern_shared_parsing.parse_blocks()`
(Liste aus `(block_type, options, content)`-Tupeln) und reichert sie mit
Render-Metadaten an (interne `_`-Präfix-Optionen), bevor sie an den
Renderer gehen. Enthält auch die Hilfe-Label-Regel (`help_block_labels`)
und die Zuordnung Lernhilfe -> Aufgabe (`assign_help_blocks`), die Karten,
Aufgabenverweise und der Klausur-Validator gemeinsam nutzen.
"""

from __future__ import annotations

from dataclasses import dataclass

from .blatt_kern_shared_data import HELP_BLOCK_TYPE
from .block_mode_policy import (
    SHOW_MODE_SOLUTION,
    SHOW_MODE_WORKSHEET,
    SOLUTION_VARIANT_BLOCK_TYPES,
    block_show_mode,
)
from .document_type_registry import solutions_per_block


def _dedupe_preserve_order(values):
    """Return values without duplicates while preserving first-seen order."""
    unique_values = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values


def _alpha_label(index):
    """Return spreadsheet-like labels: 1→A, 26→Z, 27→AA."""
    value = max(1, int(index))
    chars = []
    while value > 0:
        value -= 1
        chars.append(chr(ord("A") + (value % 26)))
        value //= 26
    return "".join(reversed(chars))


def _help_labels_for_tag(help_count, tag_text):
    """Build deterministic help labels based on global count and optional tag."""
    if help_count <= 0:
        return []

    normalized_tag = str(tag_text or "").strip()
    if help_count == 1:
        return [normalized_tag or None]

    if not normalized_tag:
        return [_alpha_label(index) for index in range(1, help_count + 1)]

    if normalized_tag.isdigit():
        return [
            f"{normalized_tag}{_alpha_label(index)}"
            for index in range(1, help_count + 1)
        ]

    if len(normalized_tag) == 1 and normalized_tag.isalpha():
        return [f"{index}{normalized_tag}" for index in range(1, help_count + 1)]

    if normalized_tag[-1].isdigit():
        return [
            f"{normalized_tag}{_alpha_label(index)}"
            for index in range(1, help_count + 1)
        ]

    if normalized_tag[-1].isalpha():
        return [f"{normalized_tag}{index}" for index in range(1, help_count + 1)]

    return [_alpha_label(index) for index in range(1, help_count + 1)]


def _format_help_reference_text(help_keys):
    """Build compact right-aligned task hint text for linked help blocks."""
    normalized_keys = _dedupe_preserve_order(
        [
            str(value).strip()
            for value in (help_keys or [])
            if value is not None and str(value).strip()
        ]
    )

    if len(help_keys or []) <= 1:
        if normalized_keys:
            return f"→ Lernhilfe {normalized_keys[0]}"
        return "→ Lernhilfe"

    if normalized_keys and len(normalized_keys) == len(help_keys or []):
        return f"→ Lernhilfen {', '.join(normalized_keys)}"

    if normalized_keys:
        return f"→ Lernhilfen {', '.join(normalized_keys)}"

    return "→ Lernhilfen"


def _normalize_help_tag(value):
    normalized = str(value or "").strip()
    return normalized or None


def assign_task_numbers(blocks):
    """Fügt `task`-Blöcken optional fortlaufende Aufgabennummern hinzu."""
    numbered_blocks = []
    task_total = sum(1 for block_type, _, _ in blocks if block_type == "task")
    task_counter = 1

    for block_type, options, content in blocks:
        if block_type == "task":
            updated_options = dict(options)
            updated_options["_show_task_label"] = "1"
            if task_total > 1:
                updated_options["_auto_number"] = str(task_counter)
            task_counter += 1
            numbered_blocks.append((block_type, updated_options, content))
        else:
            numbered_blocks.append((block_type, options, content))

    return numbered_blocks


def annotate_standalone_subtasks(blocks):
    """Reichert Top-Level-`subtask`-Blöcke mit Elternkontext und Zählung an."""
    task_contexts = {}
    current_task_key = None
    task_key_counter = 0
    subtask_total_by_task = {}
    subtask_seen_by_task = {}

    for block_type, options, _ in blocks:
        if block_type == "task":
            task_key_counter += 1
            current_task_key = task_key_counter
            task_contexts[current_task_key] = dict(options)
            continue

        if block_type == "subtask" and current_task_key is not None:
            subtask_total_by_task[current_task_key] = (
                subtask_total_by_task.get(current_task_key, 0) + 1
            )

    annotated_blocks = []
    current_task_key = None

    for block_type, options, content in blocks:
        if block_type == "task":
            current_task_key = (
                current_task_key + 1 if current_task_key is not None else 1
            )
            annotated_blocks.append((block_type, options, content))
            continue

        if block_type == "subtask" and current_task_key is not None:
            parent_options = task_contexts.get(current_task_key, {})
            updated_options = dict(options)
            updated_options["_parent_work"] = parent_options.get("work", "single")
            if parent_options.get("action") is not None:
                updated_options["_parent_action"] = parent_options.get("action")

            total = subtask_total_by_task.get(current_task_key, 0)
            seen = subtask_seen_by_task.get(current_task_key, 0)
            updated_options["_subtask_total"] = str(total)
            updated_options["_subtask_index"] = str(seen)
            subtask_seen_by_task[current_task_key] = seen + 1

            if total > 1:
                updated_options["_subtask_letter"] = chr(ord("a") + seen)

            annotated_blocks.append((block_type, updated_options, content))
            continue

        annotated_blocks.append((block_type, options, content))

    return annotated_blocks


def help_block_labels(local_tags, help_tag):
    """Sichtbare Labels für eine Folge von Hilfeblöcken -- die eine Label-Regel.

    Ein Block mit eigenem `tag=` behält ihn; alle übrigen werden über
    `_help_labels_for_tag` durchnummeriert (Frontmatter-`tag` als Präfix),
    in ihrer Reihenfolge. Karten (`collect_labeled_help_blocks`) und die
    Verweise an den Aufgaben (`annotate_task_help_references`) rufen beide
    diese Funktion über *dieselbe* Menge sichtbarer Hilfeblöcke auf, damit
    „→ Lernhilfe B“ immer die Karte „B“ meint.

    Args:
        local_tags: je Hilfeblock dessen normalisierter `tag` oder ``None``.
        help_tag: Frontmatter-`tag` (Präfix der automatischen Labels).

    Returns:
        Label je Hilfeblock (``None`` bei einer einzelnen Karte ohne Tag).
    """
    auto_labels = _help_labels_for_tag(sum(1 for tag in local_tags if not tag), _normalize_help_tag(help_tag))
    labels = []
    auto_label_index = 0
    for local_tag in local_tags:
        if local_tag:
            labels.append(local_tag)
            continue
        labels.append(auto_labels[auto_label_index] if auto_label_index < len(auto_labels) else None)
        auto_label_index += 1
    return labels


@dataclass(frozen=True)
class HelpBlockAssignment:
    """Ein sichtbarer Hilfeblock mit Label und zugehöriger (Teil-)Aufgabe.

    Attributes:
        block_index: Index des Hilfeblocks in der Blockliste.
        label: sichtbares Label (siehe `help_block_labels`).
        target_index: Index der nächsten vorangehenden sichtbaren
            `task`/`subtask`, oder ``None`` (Hilfe vor der ersten Aufgabe).
    """

    block_index: int
    label: str | None
    target_index: int | None


def assign_help_blocks(blocks, include_solutions=False, help_tag=None, document_type="worksheet"):
    """Ordnet jeden sichtbaren Hilfeblock seinem Label und seiner (Teil-)Aufgabe zu.

    Einzige Quelle für „welche Lernhilfe gehört zu welcher Aufgabe“: genutzt
    von `annotate_task_help_references` (Verweistext an der Aufgabe) und vom
    Klausur-Validator (`KL013`, Lernhilfe-Abzug in der Lösung). Die Labels
    werden über *alle* sichtbaren Hilfeblöcke vergeben, auch über solche vor
    der ersten Aufgabe -- genau wie bei den Karten.

    Returns:
        `HelpBlockAssignment`-Liste in Dokumentreihenfolge.
    """
    visible = [
        (index, options)
        for index, (block_type, options, _content) in enumerate(blocks)
        if block_type == HELP_BLOCK_TYPE
        and should_render_block(block_type, options, include_solutions, document_type=document_type)
    ]
    labels = help_block_labels([_normalize_help_tag((options or {}).get("tag")) for _, options in visible], help_tag)
    return [
        HelpBlockAssignment(
            block_index=index,
            label=label,
            target_index=_preceding_visible_task_index(blocks, index, include_solutions, document_type),
        )
        for (index, _options), label in zip(visible, labels)
    ]


def _preceding_visible_task_index(blocks, index, include_solutions, document_type):
    """Index der nächsten sichtbaren `task`/`subtask` vor `index`, sonst ``None``."""
    for previous_index in range(index - 1, -1, -1):
        previous_type, previous_options, _previous_content = blocks[previous_index]
        if previous_type in {"task", "subtask"} and should_render_block(
            previous_type, previous_options, include_solutions, document_type=document_type
        ):
            return previous_index
    return None


def annotate_task_help_references(
    blocks,
    include_solutions=False,
    help_tag=None,
    document_type="worksheet",
):
    """Annotate task/subtask blocks with rendered help-reference hint text.

    Labels und Zuordnung kommen aus `assign_help_blocks`; Hilfeblöcke ohne
    vorangehende Aufgabe bekommen keinen Verweis, zählen aber beim Labeln mit.
    """
    references_by_block_index = {}
    for assignment in assign_help_blocks(blocks, include_solutions, help_tag, document_type):
        if assignment.target_index is not None:
            references_by_block_index.setdefault(assignment.target_index, []).append(assignment.label)

    if not references_by_block_index:
        return list(blocks)

    annotated_blocks = []
    for index, (block_type, options, content) in enumerate(blocks):
        if index in references_by_block_index and block_type in {"task", "subtask"}:
            updated_options = dict(options)
            updated_options["_help_reference_text"] = _format_help_reference_text(
                references_by_block_index[index]
            )
            annotated_blocks.append((block_type, updated_options, content))
            continue

        annotated_blocks.append((block_type, options, content))

    return annotated_blocks


def should_render_block(block_type, options, include_solutions, document_type="worksheet"):
    """Entscheidet, ob ein Block in der aktuellen Ausgabe sichtbar sein soll.

    `:::expectation` erscheint nie -- nur der Erwartungshorizont liest ihn
    (`expectation_items`). In Typen mit Lösungen pro Block (Präsentation) ist
    jeder andere Block sichtbar, `:::solution` eingeschlossen; was ein Block
    dort zeigt, entscheidet `block_shows_solutions`. Sonst gilt die Fassung:
    `:::solution` nur in der Lösungsfassung (seine `mode`/`show` ignoriert,
    `OP004`), alle übrigen Blöcke nach `block_mode_policy.block_show_mode`.
    """
    if block_type == "expectation":
        return False
    if solutions_per_block(document_type):
        return True
    if block_type == "solution":
        return bool(include_solutions)
    show_mode = block_show_mode(block_type, options)
    if show_mode == SHOW_MODE_WORKSHEET:
        return not include_solutions
    if show_mode == SHOW_MODE_SOLUTION:
        return bool(include_solutions)
    return True


def block_shows_solutions(block_type, options, include_solutions, document_type="worksheet") -> bool:
    """Ob ein sichtbarer Block seine Lösungsvariante zeigt (ausgefüllte Lücken, `%`-Teile …).

    Mit eigener Lösungsfassung ist das die Fassung selbst (`include_solutions`).
    Bei Lösungen pro Block (Präsentation) nur für lösungsfähige Blöcke mit
    `mode=solution`; ohne Angabe bleiben ihre Lösungen leer, und `task`/`subtask`
    zeigen immer die Aufgabenfassung (`AN055`).
    """
    if not solutions_per_block(document_type):
        return bool(include_solutions)
    return block_type in SOLUTION_VARIANT_BLOCK_TYPES and block_show_mode(block_type, options) == SHOW_MODE_SOLUTION
