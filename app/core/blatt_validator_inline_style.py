"""Validator-Check für Inline-Stile `-<SPEC> … -<>` (Diagnosecode `IM004`).

Wie bei Worterklärungen (`blatt_validator_word_notes.py`) meldet der Inline-
Markup-Parser Fehler nur als `ParseDiagnostic`, die die Arbeitsblatt-Pipeline
verwirft. Dieser Check hebt sie als blockierenden `BuildDiagnostic` in den
Validator: unbekannte Schrift oder Farbe, doppelte Angabe, Größe außerhalb
4-120 pt, `-<>` ohne offenen Bereich und ein Bereich, der vor einer Absatz-,
Listen- oder Tabellengrenze bzw. am Blockende nicht geschlossen ist.

Über `protect_all`, damit Code, Formeln, Kommentare und Worterklärungen exakt wie
beim Rendern ausgeklammert sind (ein `-<…>` in `` `code` `` ist kein Fehler).
"""

from __future__ import annotations

from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic
from .inline_markup.runs import IM004_INVALID_INLINE_STYLE
from .inline_markup.spans import protect_all

_BLOCK_TYPES_WITHOUT_INLINE_MARKUP = frozenset({"raw"})


def validate_inline_styles(index, block_type, options, content) -> list[BuildDiagnostic]:
    """Liefert je fehlerhaftem Inline-Stil im Blockinhalt eine `IM004`-Fehler-Diagnose."""
    if block_type in _BLOCK_TYPES_WITHOUT_INLINE_MARKUP or "-<" not in (content or ""):
        return []

    *_protected, parse_diagnostics = protect_all(content)
    return [
        BuildDiagnostic(
            code=IM004_INVALID_INLINE_STYLE,
            message=diagnostic.message,
            severity="error",
            block_index=index,
            block_type=block_type,
            region_id=compute_block_region_id(block_type, options),
            anchor="inline_style",
        )
        for diagnostic in parse_diagnostics
        if diagnostic.code == IM004_INVALID_INLINE_STYLE
    ]
