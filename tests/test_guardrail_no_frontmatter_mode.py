"""Guardrail für Invariante I3: Im aktuellen System gibt es kein Frontmatter-`mode`.

Nur der migrationsinterne Altbestands-Decoder (`app/core/migration/legacy_decode.py`)
darf den historischen Key dekodieren. Die Block-Option `mode=` (z. B. auf `task`)
ist etwas anderes und bleibt erlaubt -- deshalb prüft der Test nur Zugriffe auf
Frontmatter-Variablen (`meta`, `metadata`, `front_matter`, `frontmatter`).
"""

import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
ALLOWED_MODE_READERS = {Path("core/migration/legacy_decode.py")}
FRONTMATTER_NAMES = {"meta", "metadata", "front_matter", "frontmatter", "merged_meta"}
REMOVED_SYMBOLS = {"normalize_document_mode", "DOCUMENT_MODES", "DOCUMENT_MODE_ALIASES", "KNOWN_DOCUMENT_MODES"}


def _python_files():
    for path in sorted(APP_ROOT.rglob("*.py")):
        yield path, path.relative_to(APP_ROOT), ast.parse(path.read_text(encoding="utf-8-sig"))


def _receiver_name(node) -> str | None:
    target = node
    while isinstance(target, ast.BoolOp):  # (meta or {}).get("mode")
        target = target.values[0]
    return target.id if isinstance(target, ast.Name) else None


def test_no_frontmatter_mode_reader_outside_migration_decoder():
    offenders = []
    for path, relative, tree in _python_files():
        if relative in ALLOWED_MODE_READERS:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value == "mode":
                if _receiver_name(node.value) in FRONTMATTER_NAMES:
                    offenders.append(f"{relative}:{node.lineno}")
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "mode"
                and _receiver_name(node.func.value) in FRONTMATTER_NAMES
            ):
                offenders.append(f"{relative}:{node.lineno}")
    assert offenders == []


def test_removed_mode_symbols_do_not_exist():
    offenders = []
    for path, relative, tree in _python_files():
        for node in ast.walk(tree):
            name = getattr(node, "id", None) or getattr(node, "name", None) or getattr(node, "attr", None)
            if name in REMOVED_SYMBOLS:
                offenders.append(f"{relative}:{getattr(node, 'lineno', 0)}:{name}")
    assert offenders == []


def test_no_document_mode_parameter_in_app():
    offenders = []
    for path, relative, tree in _python_files():
        for node in ast.walk(tree):
            if isinstance(node, ast.arg) and node.arg == "document_mode":
                offenders.append(f"{relative}:{node.lineno}")
            if isinstance(node, ast.keyword) and node.arg == "document_mode":
                offenders.append(f"{relative}:{node.value.lineno}")
    assert offenders == []


def test_legacy_decoder_is_only_imported_from_migration_package():
    offenders = []
    for path, relative, tree in _python_files():
        if relative.parts[:2] == ("core", "migration"):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and "legacy_decode" in node.module:
                offenders.append(f"{relative}:{node.lineno}")
    assert offenders == []
