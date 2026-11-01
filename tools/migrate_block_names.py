"""Stellt frühere deutsche Blocknamen in Blattwerk-Dokumenten auf die englischen um.

Beispiele:
- :::hilfe title="Tipp"      -> :::help title="Tipp"
- :::struktogramm width=80%  -> :::structogram width=80%

Ohne `--write` zeigt das Werkzeug nur an, was es ändern würde. Zeilen in
Code-Zäunen (```) bleiben unberührt. Die Namen kommen aus `REMOVED_BLOCK_NAMES`,
die Endungen aus `BLATTWERK_EXTENSIONS`.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.blatt_validator_constants import REMOVED_BLOCK_NAMES  # noqa: E402
from app.core.document_type_registry import BLATTWERK_EXTENSIONS  # noqa: E402

_HEADER_RE = re.compile(r"^(\s*:::)(" + "|".join(REMOVED_BLOCK_NAMES) + r")(?=\s|:::|$)", flags=re.MULTILINE)
_FENCE_RE = re.compile(r"^\s*```")


def rewrite_content(text: str) -> tuple[str, int]:
    """Ersetzt alte Blocknamen in den Kopfzeilen außerhalb von Code-Zäunen.

    Args:
        text: Vollständiger Dokumenttext; Zeilenenden bleiben erhalten.

    Returns:
        `(neuer_text, anzahl_ersetzungen)`.
    """
    result: list[str] = []
    count = 0
    in_fence = False
    for line in text.splitlines(keepends=True):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
        if not in_fence:
            line, replaced = _HEADER_RE.subn(lambda match: match.group(1) + REMOVED_BLOCK_NAMES[match.group(2)], line)
            count += replaced
        result.append(line)
    return "".join(result), count


def iter_documents(root: Path) -> list[Path]:
    """Alle Blattwerk-Dokumente unter `root`, sortiert; `root` darf auch eine Datei sein."""
    if root.is_file():
        return [root]
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in BLATTWERK_EXTENSIONS)


def migrate(root: Path, *, write: bool) -> list[tuple[Path, int]]:
    """Stellt alle Dokumente unter `root` um (oder prüft sie nur).

    Args:
        root: Datei oder Ordner.
        write: `True` schreibt die Änderungen, `False` ist ein reiner Probelauf.

    Returns:
        Betroffene Dateien mit der Anzahl ihrer Ersetzungen.
    """
    changed: list[tuple[Path, int]] = []
    for path in iter_documents(root):
        original = path.read_bytes().decode("utf-8")
        updated, count = rewrite_content(original)
        if not count:
            continue
        changed.append((path, count))
        if write:
            path.write_bytes(updated.encode("utf-8"))
    return changed


def main(argv: list[str] | None = None) -> int:
    """Kommandozeile: Pfad angeben, `--write` schreibt."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path, help="Datei oder Ordner mit Blattwerk-Dokumenten")
    parser.add_argument("--write", action="store_true", help="Änderungen schreiben (sonst nur Probelauf)")
    args = parser.parse_args(argv)

    changed = migrate(args.path, write=args.write)
    for path, count in changed:
        print(f"{path}: {count}")
    mode = "geändert" if args.write else "würden geändert"
    print(f"{len(changed)} Datei(en) {mode}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
