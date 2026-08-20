"""Kern-Validierungsschritte für ein geparstes Blattwerk-Dokument.

Zerlegt die eigentliche Dokumentprüfung in fokussierte Schritte, die vom
schlanken Orchestrator in `blatt_validator.py` in fester Reihenfolge pro
Block aufgerufen werden: Frontmatter (`_validate_frontmatter`),
block-typ-spezifische Checks (`_validate_block_type_specifics`) und
YAML-Antwort-Payloads (`_validate_yaml_answer_payload`). Die
Options-Validierung selbst lebt in `blatt_validator_block_options.py`
(ausgelagert, da sie allein bereits ein Drittel dieser Datei ausmachte).
Die Aufteilung folgt exakt der ursprünglichen, in einer einzigen
~400-Zeilen-Funktion verschachtelten Logik — bewusst ohne
Verhaltensänderung, siehe Test-Parität nach dem Split.
"""

from __future__ import annotations

import yaml

from .answer_line_markers import (
    collect_answer_marker_conflict_lines,
    is_effectively_empty_answer_content,
)
from .blatt_validator_constants import (
    ANSWER_BLOCK_TYPES,
    OPTIONAL_FRONTMATTER_FIELDS,
    REQUIRED_FRONTMATTER_FIELDS,
    YAML_ANSWER_TYPES,
)
from .blatt_validator_marker_syntax import _has_explicit_worksheet_marker_without_solution
from .blatt_validator_types import BuildDiagnostic
from .blatt_validator_value_helpers import _get_matching_item_counts
from .blatt_validator_yaml_entries import (
    _validate_geometry_entry_fields,
    _validate_payload_show_markers,
)

# Diagnosecode/Schweregrad/Sonderregeln pro validiertem optionalen Feld.
# Bewusst getrennt von `OPTIONAL_FRONTMATTER_FIELDS` (dort steht nur, WAS
# gültig ist -- geteilt mit dem Doku-Collector); dieses Mapping ist reines
# Validator-Implementierungsdetail (Diagnosecode/Schweregrad sind für die
# generierte Autorenanleitung nicht relevant, siehe `docs/VALIDATOR.md`).
# `skip_when_empty=True` bei `presentation_layout` bewahrt bestehendes
# Verhalten: ein leerer Wert (z. B. `presentation_layout:` ohne Inhalt)
# löst dort keine Diagnose aus, bei `mode` dagegen schon -- eine echte,
# vorbestehende Asymmetrie, kein neu eingeführtes Verhalten.
_ENUM_FIELD_DIAGNOSTICS = {
    "mode": {"code": "FM002", "severity": "warning", "skip_when_empty": False},
    "presentation_layout": {"code": "FM004", "severity": "error", "skip_when_empty": True},
}
_BOOLEAN_FIELD_DIAGNOSTIC_CODES = {
    "presentation_show_mini_header": "FM005",
    "presentation_show_section_footer": "FM005",
    "show_student_header": "FM006",
    "show_document_header": "FM006",
}
_SCALAR_NONEMPTY_FIELD_DIAGNOSTIC_CODES = {
    "tag": "FM003",
}


def _validate_optional_enum_field(field, raw_value):
    rules = _ENUM_FIELD_DIAGNOSTICS[field.name]
    normalized = str(raw_value or "").strip().lower()
    if rules["skip_when_empty"] and not normalized:
        return None
    if normalized in field.allowed_values:
        return None
    return BuildDiagnostic(
        code=rules["code"],
        message=(
            f"Ungueltiger Frontmatter-Wert fuer `{field.name}`: `{raw_value}`. "
            f"Erlaubt: {', '.join(sorted(field.allowed_values))}."
        ),
        severity=rules["severity"],
    )


def _validate_optional_boolean_field(field, raw_value):
    # Bewusst nicht `raw_value or ""`: YAML-native `false`/`0` sind falsy in
    # Python und wuerden dadurch faelschlich zu einem leeren String
    # kollabieren (und damit als ungueltig gemeldet werden), obwohl beide
    # gueltige boolesche Schreibweisen sind.
    normalized = str(raw_value).strip().lower() if raw_value is not None else ""
    if normalized in field.allowed_values:
        return None
    return BuildDiagnostic(
        code=_BOOLEAN_FIELD_DIAGNOSTIC_CODES[field.name],
        message=(
            f"Ungueltiger Frontmatter-Wert fuer `{field.name}`. "
            "Erlaubt sind boolesche Werte (z. B. true/false, ja/nein, 1/0)."
        ),
        severity="error",
    )


def _validate_optional_scalar_nonempty_field(field, raw_value):
    code = _SCALAR_NONEMPTY_FIELD_DIAGNOSTIC_CODES[field.name]
    if isinstance(raw_value, (dict, list)):
        return BuildDiagnostic(
            code=code,
            message=(
                f"Ungueltiger Frontmatter-Wert fuer `{field.name}`: "
                "Erlaubt ist ein einfacher Textwert (z. B. `1`, `A`, `TAG`)."
            ),
            severity="error",
        )
    if not str(raw_value).strip():
        return BuildDiagnostic(
            code=code,
            message=(
                f"Ungueltiger Frontmatter-Wert fuer `{field.name}`: leerer Wert ist nicht erlaubt."
            ),
            severity="error",
        )
    return None


def _validate_frontmatter(meta):
    """Validiert Frontmatter-Felder (`FM001`-`FM006`) und liefert die gefundenen Diagnosen.

    Pflichtfelder (`FM001`) kommen direkt aus `REQUIRED_FRONTMATTER_FIELDS`;
    optionale Felder werden generisch über `OPTIONAL_FRONTMATTER_FIELDS`
    geprüft (nur Felder mit `validated=True` und nur, wenn im Dokument
    gesetzt) -- Katalog und Validierungsverhalten können dadurch
    strukturell nicht mehr auseinanderlaufen.
    """
    diagnostics = []
    metadata = meta if isinstance(meta, dict) else {}

    for required_key in REQUIRED_FRONTMATTER_FIELDS:
        value = str(metadata.get(required_key, "")).strip()
        if not value:
            diagnostics.append(
                BuildDiagnostic(
                    code="FM001",
                    message=f"Pflichtfeld im Frontmatter fehlt oder ist leer: `{required_key}`.",
                )
            )

    for field in OPTIONAL_FRONTMATTER_FIELDS:
        if not field.validated or field.name not in metadata:
            continue

        raw_value = metadata.get(field.name)
        if field.kind == "enum":
            diagnostic = _validate_optional_enum_field(field, raw_value)
        elif field.kind == "boolean":
            diagnostic = _validate_optional_boolean_field(field, raw_value)
        elif field.kind == "scalar_nonempty":
            diagnostic = _validate_optional_scalar_nonempty_field(field, raw_value)
        else:
            diagnostic = None

        if diagnostic is not None:
            diagnostics.append(diagnostic)

    return diagnostics


def _validate_block_type_specifics(diagnostics, index, block_type, content, qrcode_url_value):
    """Prüft block-typ-spezifische Invarianten nach der Options-Validierung.

    Liefert `True`, wenn `block_type` ein Antwort-Blocktyp ist (dann folgt
    im Orchestrator noch `_validate_yaml_answer_payload`), sonst `False`.
    """
    if block_type == "qrcode" and not qrcode_url_value:
        diagnostics.append(
            BuildDiagnostic(
                code="QR001",
                message="Block `qrcode` benoetigt die Pflichtoption `url=...`.",
                severity="error",
                block_index=index,
                block_type=block_type,
            )
        )

    if block_type in {"task", "subtask"} and _has_explicit_worksheet_marker_without_solution(
        content
    ):
        diagnostics.append(
            BuildDiagnostic(
                code="AN010",
                message=(
                    f"Block `{block_type}` nutzt `§`-Marker ohne sichtbares "
                    "Loesungs-Gegenstueck. Pruefe, ob zu jedem nur im "
                    "Arbeitsblatt sichtbaren Aufgabenteil auch eine explizite "
                    "Loesung vorhanden ist (z. B. mit `%`-Marker)."
                ),
                block_index=index,
                block_type=block_type,
            )
        )

    if block_type not in ANSWER_BLOCK_TYPES:
        return False

    if is_effectively_empty_answer_content(content):
        diagnostics.append(
            BuildDiagnostic(
                code="AN005",
                message=(
                    "Answer-Block ist leer. Best Practice: Antwortfelder mit "
                    "Startimpulsen oder Strukturierung vorfuellen."
                ),
                block_index=index,
                block_type=block_type,
            )
        )

    marker_conflicts = collect_answer_marker_conflict_lines(content)
    if marker_conflicts:
        preview = ", ".join(str(value) for value in marker_conflicts[:5])
        remainder = len(marker_conflicts) - 5
        remainder_text = f" (+{remainder} weitere)" if remainder > 0 else ""
        diagnostics.append(
            BuildDiagnostic(
                code="AN006",
                message=(
                    "Answer-Zeilen mit ungueltiger §/%/&-Token-Syntax gefunden "
                    f"(Zeilen: {preview}{remainder_text}). "
                    "Bitte Marker als §{...}, %{...} oder &{...} schliessen."
                ),
                block_index=index,
                block_type=block_type,
            )
        )

    if _has_explicit_worksheet_marker_without_solution(content):
        diagnostics.append(
            BuildDiagnostic(
                code="AN010",
                message=(
                    f"Block `{block_type}` nutzt `§`-Marker ohne sichtbares "
                    "Loesungs-Gegenstueck. Pruefe, ob zu jedem nur im "
                    "Arbeitsblatt sichtbaren Aufgabenteil auch eine explizite "
                    "Loesung vorhanden ist (z. B. mit `%`-Marker)."
                ),
                block_index=index,
                block_type=block_type,
            )
        )

    return True


def _validate_yaml_answer_payload(diagnostics, index, block_type, options, content):
    """Parst und validiert den YAML-Payload eines Antwortblocks (`AN003`/`AN004`/`AN007`/`MA001`).

    Bricht (per `return`) vor der `matching`-Elementzahlprüfung ab, wenn
    das YAML nicht parsebar war — analog zum ursprünglichen `continue` in
    der monolithischen Schleife, das denselben Effekt hatte.
    """
    answer_type = block_type

    if answer_type in YAML_ANSWER_TYPES and (content or "").strip():
        try:
            parsed = yaml.safe_load(content)
        except yaml.YAMLError as error:
            diagnostics.append(
                BuildDiagnostic(
                    code="AN003",
                    message=f"YAML-Fehler in answer `{answer_type}`: {error}",
                    severity="error",
                    block_index=index,
                    block_type=block_type,
                )
            )
            return

        if parsed is not None and not isinstance(parsed, dict):
            diagnostics.append(
                BuildDiagnostic(
                    code="AN004",
                    message=(
                        f"Answer `{answer_type}` erwartet YAML-Mapping (Key-Value), "
                        "kein Skalar oder Listen-Root."
                    ),
                    block_index=index,
                    block_type=block_type,
                )
            )

        if isinstance(parsed, dict):
            _validate_payload_show_markers(diagnostics, index, answer_type, parsed)
            _validate_geometry_entry_fields(diagnostics, index, answer_type, parsed)

    if answer_type == "matching":
        first_count, second_count = _get_matching_item_counts(options, content)
        if first_count == 1 or second_count == 1:
            diagnostics.append(
                BuildDiagnostic(
                    code="MA001",
                    message=(
                        "Matching mit nur einem Element auf einer Seite ist "
                        "didaktisch nicht sinnvoll (1↔N)."
                    ),
                    block_index=index,
                    block_type=block_type,
                )
            )
