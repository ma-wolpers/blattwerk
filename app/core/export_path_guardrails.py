"""Guardrails for export target paths: validation and the locked-target policy.

`validate_export_output_path` is the one function every exporter calls for its target.
Besides validating, it resolves a *locked* target (e.g. a PDF still open in a viewer)
according to `ExportTargetPolicy` - before anything expensive is rendered:

- `LOCK_POLICY_ERROR`: raise `LockedExportTargetError` immediately.
- `LOCK_POLICY_ALTERNATE`: write to ``Name (neu).pdf`` (then ``Name (neu 2).pdf`` ...).

Detecting a lock needs an OS adapter. `app/core` never imports `app/storage`, so the
probe is injected through the `ExportTargetLockProbe` port (adapter:
`app/storage/file_lock_probe_adapter.py`). Without a probe the pre-check is skipped;
publishing the finished file (`export_staging.publish_export_file`) still detects the
lock exactly by attempting the replace.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Protocol

PROJECT_ROOT = Path(__file__).resolve().parents[2]

LOCK_POLICY_ERROR = "error"
LOCK_POLICY_ALTERNATE = "alternate_name"
LOCK_POLICIES = (LOCK_POLICY_ERROR, LOCK_POLICY_ALTERNATE)
ALTERNATE_NAME_MARK = "neu"
MAX_ALTERNATE_NAMES = 50
_ALTERNATE_SUFFIX_PATTERN = re.compile(rf" \({ALTERNATE_NAME_MARK}(?: \d+)?\)$")


class ExportTargetLockProbe(Protocol):
    """Port: tells whether an existing file cannot be replaced right now."""

    def is_locked(self, path: Path) -> bool: ...


@dataclass(frozen=True)
class ExportTargetPolicy:
    """What to do with a locked export target, plus the probe that detects it.

    Attributes:
        lock_policy: One of `LOCK_POLICIES` (user preference
            ``export_locked_target_policy``).
        probe: OS adapter for the pre-check; ``None`` skips the pre-check.
    """

    lock_policy: str = LOCK_POLICY_ERROR
    probe: ExportTargetLockProbe | None = None


class LockedExportTargetError(RuntimeError):
    """The export target is open in another program and may not be replaced."""

    def __init__(self, target: Path):
        self.target = Path(target)
        super().__init__(
            f"Die Zieldatei „{self.target.name}“ ist noch in einem anderen Programm "
            "geöffnet. Bitte schließen und erneut exportieren (oder in den Einstellungen "
            "„Export → Gesperrte Zieldatei“ auf Ausweichname stellen)."
        )


def alternate_target_names(target: Path) -> Iterator[Path]:
    """Candidates for a locked target: ``Name (neu).pdf``, ``Name (neu 2).pdf``, ...

    An existing ``(neu)``/``(neu n)`` mark is stripped first, so resolving an already
    redirected path never produces ``Name (neu) (neu).pdf``.

    Example:
        >>> [p.name for p in list(alternate_target_names(Path("A (neu).pdf")))[:2]]
        ['A (neu).pdf', 'A (neu 2).pdf']
    """
    target = Path(target)
    base_stem = _ALTERNATE_SUFFIX_PATTERN.sub("", target.stem)
    yield target.with_name(f"{base_stem} ({ALTERNATE_NAME_MARK}){target.suffix}")
    for number in range(2, MAX_ALTERNATE_NAMES + 1):
        yield target.with_name(f"{base_stem} ({ALTERNATE_NAME_MARK} {number}){target.suffix}")


def resolve_locked_target(target: Path, policy: ExportTargetPolicy | None) -> Path:
    """Apply the lock policy to ``target`` (idempotent: an unlocked path stays as is).

    Raises:
        LockedExportTargetError: Locked and policy is `LOCK_POLICY_ERROR`, or no free
            alternate name is left.
    """
    target = Path(target)
    if policy is None or policy.probe is None or not policy.probe.is_locked(target):
        return target
    if policy.lock_policy != LOCK_POLICY_ALTERNATE:
        raise LockedExportTargetError(target)
    for candidate in alternate_target_names(target):
        if candidate != target and not policy.probe.is_locked(candidate):
            return candidate
    raise LockedExportTargetError(target)

_BLOCKED_TOP_LEVEL_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
}


def _is_inside(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _blocked_root_folder_name(path: Path) -> str | None:
    if not _is_inside(path, PROJECT_ROOT):
        return None

    relative = path.resolve().relative_to(PROJECT_ROOT.resolve())
    if not relative.parts:
        return None

    top_level = relative.parts[0]
    if top_level.lower() in {name.lower() for name in _BLOCKED_TOP_LEVEL_DIRS}:
        return top_level
    return None


def validate_export_output_path(
    path_value: str | Path,
    *,
    allowed_suffixes: set[str],
    target_policy: ExportTargetPolicy | None = None,
) -> Path:
    """Validate, normalize and lock-resolve an export target before writing files.

    Call it *before* rendering, so a locked target fails fast instead of after a long
    build. The returned path may differ from the input under `LOCK_POLICY_ALTERNATE`.

    Args:
        path_value: Requested target path.
        allowed_suffixes: Permitted file extensions, e.g. ``{".pdf", ".html"}``.
        target_policy: Locked-target handling; ``None`` = no pre-check.

    Raises:
        ValueError: Invalid target (empty, drive root, folder, suffix, internal dir).
        LockedExportTargetError: See `resolve_locked_target`.
    """

    raw_text = str(path_value or "").strip()
    if not raw_text:
        raise ValueError("Export-Zielpfad ist leer.")

    target = Path(raw_text).expanduser().resolve()

    if target == Path(target.anchor):
        raise ValueError("Export-Ziel darf nicht direkt auf ein Laufwerks-Root zeigen.")

    if target.exists() and target.is_dir():
        raise ValueError("Export-Ziel muss eine Datei sein, kein Ordner.")

    suffix = target.suffix.lower()
    normalized_allowed = {entry.lower() for entry in allowed_suffixes}
    if suffix not in normalized_allowed:
        allowed_label = ", ".join(sorted(normalized_allowed))
        raise ValueError(
            f"Export-Zieldatei hat ungueltige Endung `{suffix or '(leer)'}`. Erlaubt: {allowed_label}."
        )

    blocked = _blocked_root_folder_name(target)
    if blocked:
        raise ValueError(
            "Export-Ziel liegt in einem internen Projektordner und ist nicht erlaubt: "
            f"{blocked}"
        )

    return resolve_locked_target(target, target_policy)
