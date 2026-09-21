"""Validator-Check für `??Begriff|Erklärung??`-Worterklärungen (Diagnosecode `IM002`).

Der Inline-Markup-Parser meldet eine fehlerhafte Worterklärung (fehlendes
oder doppeltes `|`, leerer Begriff/leere Erklärung) als `ParseDiagnostic`;
die Arbeitsblatt-Pipeline (`markdown_bridge.py`) verwirft Parser-Diagnosen
aber. Damit ein solcher Fehler nicht stillschweigend als Rohtext im
fertigen PDF landet, hebt dieser Check ihn als blockierenden
`BuildDiagnostic` (`severity="error"`) in den Validator.

Bewusst über `protect_all` statt einer eigenen Suche: Code-Spans, Mathe und
Kommentare werden so exakt wie beim Rendern ausgeklammert, ein `??` in
`` `code` `` löst also keinen Fehler aus.
"""

from __future__ import annotations

from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic
from .inline_markup.runs import IM002_MALFORMED_WORD_NOTE
from .inline_markup.spans import protect_all

_BLOCK_TYPES_WITHOUT_INLINE_MARKUP = frozenset({"raw"})


def validate_word_notes(index, block_type, options, content) -> list[BuildDiagnostic]:
    """Liefert je fehlerhafter Worterklärung im Blockinhalt eine `IM002`-Fehler-Diagnose."""
    if block_type in _BLOCK_TYPES_WITHOUT_INLINE_MARKUP or "??" not in (content or ""):
        return []

    *_protected, parse_diagnostics = protect_all(content)
    return [
        BuildDiagnostic(
            code=IM002_MALFORMED_WORD_NOTE,
            message=diagnostic.message,
            severity="error",
            block_index=index,
            block_type=block_type,
            region_id=compute_block_region_id(block_type, options),
            anchor="word_note",
        )
        for diagnostic in parse_diagnostics
        if diagnostic.code == IM002_MALFORMED_WORD_NOTE
    ]
