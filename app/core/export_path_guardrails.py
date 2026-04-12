"""Guardrails for export target paths."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

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


def validate_export_output_path(path_value: str | Path, *, allowed_suffixes: set[str]) -> Path:
    """Validate and normalize export output path before writing files."""

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

    return target
