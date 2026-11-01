"""Validierung von `:::structogram`-Blöcken (Diagnosecodes `SG001`–`SG023`).

Drei Ebenen, alle aus derselben Quelle wie der Renderer
(`struktogramm_parse.parse_struktogramm`, `struktogramm_signature`):

1. **Struktur** (`SG001`–`SG008`): Einrückung, verwaiste `sonst`/`fall`/
   `bis`, `wiederhole` ohne `bis`, leere Rümpfe, fehlende Texte. Kommen
   direkt als `ParseIssue` aus dem Parser.
2. **Methodenkopf** (`SG010`–`SG013`, `SG020`): `signature=` muss der
   GO-Form folgen; fehlt die Option, warnt `SG020`, weil GO-Struktogramme
   immer einen Methodenkopf tragen.
3. **Kopf ↔ Rumpf** (`SG021`–`SG023`): Rückgaben nur mit Rückgabetyp; mit
   Rückgabetyp muss jeder Ablaufpfad mit einer Rückgabe enden; jeder
   Parameter muss im Struktogramm vorkommen.

Eingebunden über `diagram_block_dispatch.validate_diagram_blocks` im Orchestrator
`blatt_validator._collect_document_diagnostics` (wie `validate_geometry_labels`).
"""

from __future__ import annotations

import re

from .blatt_validator_types import BuildDiagnostic
from .diagram_block_catalog import DIAGRAM_BLOCKS_BY_NAME
from .diagram_validation import DiagnosticCollector, validate_block
from .struktogramm_parse import Branch, Loop, Statement, Switch, iter_cells, parse_struktogramm
from .struktogramm_signature import IDENTIFIER_PATTERN, SignatureError, parse_signature

_IDENTIFIER_RE = re.compile(IDENTIFIER_PATTERN)
_LITERAL_RETURN_RE = re.compile(r"^\s*gib\b.*\bzurück\s*$", re.IGNORECASE)


def ends_with_return(elements: list) -> bool:
    """True, wenn *jeder* Ablaufpfad durch `elements` sicher eine Rückgabe erreicht.

    Regeln: Rückgabe = ja; Folge = irgendein Element darin endet sicher;
    Verzweigung = beide Zweige (fehlendes/leeres `sonst` = nein); Auswahl =
    alle `fall` *und* ein vorhandenes `sonst`; kopfgesteuerte Schleife = nein
    (kann 0-mal laufen); fußgesteuerte Schleife = ihr Rumpf (läuft mind.
    einmal). Bewusst konservativ: `wiederhole 100-mal` mit Rückgabe im Rumpf
    zählt nicht, weil die Anzahl nicht ausgewertet wird.
    """
    return any(_element_returns(element) for element in elements)


def _element_returns(element) -> bool:
    """Einzelfall von `ends_with_return` für genau ein Element."""
    if isinstance(element, Statement):
        return element.kind == "return"
    if isinstance(element, Branch):
        return ends_with_return(element.yes) and ends_with_return(element.no)
    if isinstance(element, Switch):
        if element.default is None or not element.cases:
            return False
        bodies = [case.body for case in element.cases] + [element.default]
        return all(ends_with_return(body) for body in bodies)
    if isinstance(element, Loop):
        return element.kind == "foot" and ends_with_return(element.body)
    return False


def _iter_statements(elements):
    """Alle `Statement`s des Baums in Tiefensuche."""
    for element in elements:
        if isinstance(element, Statement):
            yield element
        elif isinstance(element, Branch):
            yield from _iter_statements(element.yes)
            yield from _iter_statements(element.no)
        elif isinstance(element, Switch):
            for case in element.cases:
                yield from _iter_statements(case.body)
            yield from _iter_statements(element.default or [])
        elif isinstance(element, Loop):
            yield from _iter_statements(element.body)


def _check_returns(collect: DiagnosticCollector, signature, elements: list) -> None:
    """`SG021` (Rückgabe ohne Rückgabetyp) und `SG022` (Pfad ohne Rückgabe)."""
    returns = [s for s in _iter_statements(elements) if s.kind == "return"]
    if signature.return_type is None:
        if returns:
            lines = ", ".join(str(s.line) for s in returns)
            collect.add(
                "SG021",
                f"`rückgabe` (Zeile {lines} im Block), aber die Signatur hat keinen Rückgabetyp.",
                severity="error",
                anchor=f"SG021:{lines}",
            )
        return
    if ends_with_return(elements):
        return
    message = f"Die Signatur gibt `{signature.return_type}` zurück, aber nicht jeder Ablauf endet mit einer `rückgabe`."
    if any(s.kind == "plain" and _LITERAL_RETURN_RE.match(s.cell.text) for s in _iter_statements(elements)):
        message += " Rückgaben als `rückgabe …` schreiben, nicht als `gib … zurück`."
    collect.add("SG022", message)


def _check_parameters(collect: DiagnosticCollector, signature, elements: list) -> None:
    """`SG023`: jeder Parameter muss als ganzes Wort im Struktogramm vorkommen."""
    used = {word for cell in iter_cells(elements) for word in _IDENTIFIER_RE.findall(cell.text)}
    unused = [name for name in signature.parameter_names if name not in used]
    if unused:
        names = ", ".join(f"`{name}`" for name in unused)
        collect.add("SG023", f"Parameter {names} wird nicht verwendet.", anchor=f"SG023:{','.join(unused)}")


def check_structogram(collect: DiagnosticCollector, options, elements: list) -> None:
    """Fachliche Prüfungen: Signatur (`SG010`-`SG013`, `SG020`), Rückgaben, Parameter.

    Args:
        collect: Sammler des Blocks.
        options: Blockoptionen; relevant ist `signature`.
        elements: Nicht leerer Elementbaum aus `parse_struktogramm`.
    """
    raw_signature = str(options.get("signature") or "").strip()
    if not raw_signature:
        collect.add("SG020", "Ohne `signature=` fehlt der Methodenkopf, den GO-Struktogramme immer haben.")
        return
    try:
        signature = parse_signature(raw_signature)
    except SignatureError as error:
        collect.add(error.code, str(error), severity="error")
        return
    _check_returns(collect, signature, elements)
    _check_parameters(collect, signature, elements)


def validate_struktogramm_block(index, block_type, options, content) -> list[BuildDiagnostic]:
    """Prüft einen `:::structogram`-Block vollständig (siehe `diagram_validation.validate_block`)."""
    spec = DIAGRAM_BLOCKS_BY_NAME["structogram"]
    return validate_block(
        index,
        block_type,
        options,
        content,
        title=spec.title,
        parse=parse_struktogramm,
        check=check_structogram,
        empty_code=spec.empty_code,
    )
