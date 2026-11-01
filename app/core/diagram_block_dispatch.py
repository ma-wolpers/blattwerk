"""Verbindet die Diagramm-Registrierung mit Rendering, Layoutschätzung und Validierung.

Die Module werden erst beim Gebrauch geladen: Die Aufrufer sitzen im Kern, die
Diagrammmodule importieren selbst Kernbausteine, und so bleibt es ohne Importzyklus.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import import_module
from types import ModuleType

from .blatt_validator_types import BuildDiagnostic
from .diagram_block_catalog import DIAGRAM_BLOCK_NAMES, DIAGRAM_BLOCKS_BY_NAME
from .diagram_validation import validate_block


@lru_cache(maxsize=None)
def _module(name: str) -> ModuleType:
    """Lädt das Modul des Diagrammblocks `name` genau einmal."""
    return import_module(f"app.core.{DIAGRAM_BLOCKS_BY_NAME[name].module}")


def render_diagram_block(name: str, options, content, include_solutions: bool = False) -> str:
    """Rendert einen Diagrammblock aus seinem rohen Inhalt zu HTML."""
    return _module(name).render(options or {}, content, include_solutions)


def estimate_shared_diagram_weight(content) -> float:
    """Gemeinsame Layoutschätzung: Diagramme wachsen mit den Zeilen und brauchen Breite."""
    lines = [line for line in str(content or "").splitlines() if line.strip()]
    if not lines:
        return 0.0
    return 0.8 + 0.18 * len(lines) + max(len(line.strip()) for line in lines) / 55.0


def estimate_diagram_weight(name: str, options, content) -> float:
    """Layoutgewicht für automatische Spaltenbreiten; Module dürfen es selbst bestimmen."""
    estimate = getattr(_module(name), "estimate_weight", None)
    return estimate(options or {}, content) if estimate else estimate_shared_diagram_weight(content)


def validate_diagram_blocks(blocks) -> list[BuildDiagnostic]:
    """Prüft alle Diagrammblöcke eines Dokuments (Einstieg für den Orchestrator)."""
    diagnostics: list[BuildDiagnostic] = []
    for index, (block_type, options, content) in enumerate(blocks):
        if block_type not in DIAGRAM_BLOCK_NAMES:
            continue
        spec = DIAGRAM_BLOCKS_BY_NAME[block_type]
        module = _module(block_type)
        diagnostics.extend(
            validate_block(
                index,
                block_type,
                options,
                content,
                title=spec.title,
                parse=module.parse,
                check=getattr(module, "check", None),
                empty_code=spec.empty_code,
            )
        )
    return diagnostics
