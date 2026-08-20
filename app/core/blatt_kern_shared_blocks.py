"""Nachbearbeitung geparster Blocklisten: Aufgabennummern, Teilaufgaben, Hilfe-Referenzen, Sichtbarkeit.

Arbeitet auf dem Ergebnis von `blatt_kern_shared_parsing.parse_blocks()`
(Liste aus `(block_type, options, content)`-Tupeln) und reichert sie mit
Render-Metadaten an (interne `_`-Präfix-Optionen), bevor sie an den
Renderer gehen. Enthält auch die kleinen Hilfe-Label-Helfer, die
ausschließlich von `annotate_task_help_references` genutzt werden.
"""

from __future__ import annotations

from .blatt_kern_shared_data import HELP_BLOCK_TYPES
from .blatt_kern_shared_meta import normalize_document_mode


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


def annotate_task_help_references(
    blocks,
    include_solutions=False,
    help_tag=None,
    document_mode="worksheet",
):
    """Annotate task/subtask blocks with rendered help-reference hint text."""
    references_by_block_index = {}
    visible_help_entries = []

    for current_index, (block_type, options, _content) in enumerate(blocks):
        if block_type not in HELP_BLOCK_TYPES:
            continue
        if not should_render_block(
            block_type,
            options,
            include_solutions,
            document_mode=document_mode,
        ):
            continue

        target_index = None
        for previous_index in range(current_index - 1, -1, -1):
            previous_type, previous_options, _previous_content = blocks[previous_index]
            if previous_type not in {"task", "subtask"}:
                continue
            if not should_render_block(
                previous_type,
                previous_options,
                include_solutions,
                document_mode=document_mode,
            ):
                continue
            target_index = previous_index
            break

        if target_index is None:
            continue

        local_tag = _normalize_help_tag((options or {}).get("tag"))
        visible_help_entries.append(
            {
                "target_index": target_index,
                "local_tag": local_tag,
            }
        )

    auto_tag_entries = [entry for entry in visible_help_entries if not entry["local_tag"]]
    auto_labels = _help_labels_for_tag(len(auto_tag_entries), help_tag)
    auto_label_index = 0

    for entry in visible_help_entries:
        target_index = entry["target_index"]
        if entry["local_tag"]:
            help_label = entry["local_tag"]
        else:
            help_label = (
                auto_labels[auto_label_index]
                if auto_label_index < len(auto_labels)
                else None
            )
            auto_label_index += 1
        references_by_block_index.setdefault(target_index, []).append(help_label)

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


def should_render_block(block_type, options, include_solutions, document_mode="worksheet"):
    """Entscheidet, ob ein Block in der aktuellen Ausgabe sichtbar sein soll."""
    mode_raw = (options.get("mode") or "").strip().lower()
    if mode_raw in {"worksheet", "solution"}:
        show_mode = mode_raw
    else:
        # Legacy-Fallback for existing documents.
        show_mode_raw = (options.get("show") or "").strip().lower()
        if show_mode_raw in {"worksheet", "solution", "both"}:
            show_mode = show_mode_raw
        else:
            show_mode = "both"

    normalized_mode = normalize_document_mode(document_mode, default="worksheet")

    if normalized_mode == "presentation" and show_mode == "solution":
        return False

    if show_mode == "worksheet" and include_solutions:
        return False
    if show_mode == "solution" and not include_solutions:
        return False

    if block_type == "solution":
        return include_solutions

    return True
