"""Gemeinsame Helfer für Migrationstests (nur synthetische Dateien in tmp_path)."""

from pathlib import Path

from app.core.migration.plan import scan
from app.core.migration.runner import new_run_dir, write_plan
from app.core.migration.side_state import InMemorySideStateStore

WORKSHEET = "---\nTitel: T\nFach: M\nThema: X\n---\n:::task\nA\n:::\n"
PRESENTATION = "---\nTitel: T\nFach: M\nThema: X\nmode: presentation\n---\n:::task\nA\n:::\n"


class ScriptedResolver:
    """Liefert vorab festgelegte Antworten und protokolliert die Rückfragen."""

    def __init__(self, *answers: str, default: str | None = None) -> None:
        self.answers = list(answers)
        self.default = default
        self.calls: list[tuple[str, str, tuple[str, ...]]] = []

    def resolve(self, kind, item_label, choices):
        self.calls.append((kind, item_label, choices))
        if self.answers:
            return self.answers.pop(0)
        if self.default is not None:
            return self.default
        raise AssertionError(f"unerwartete Rueckfrage: {kind} {item_label}")


def make_tree(tmp_path: Path, files: dict[str, bytes | str]) -> Path:
    root = tmp_path / "root"
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
    root.mkdir(exist_ok=True)
    return root


def planned_run(tmp_path: Path, root: Path, **scan_kwargs):
    plan = scan(root, **scan_kwargs)
    run_dir = new_run_dir(tmp_path / "runs")
    write_plan(plan, run_dir)
    return plan, run_dir


def store_with(*paths: Path) -> InMemorySideStateStore:
    return InMemorySideStateStore(
        recent_files=[p.as_posix() for p in paths],
        acknowledged={p.as_posix(): ["abc"] for p in paths},
    )
