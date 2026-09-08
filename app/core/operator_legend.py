"""Operatoren-Legende -- die "Garage" im Haus/Garage-Prinzip (siehe DEVELOPMENT_LOG.md).

Einzige Stelle im Code, die weiß, was ein Aufgaben-Operator (`!!...!!`-Marker,
siehe `inline_markup/syntax.py`), ein Fach->Operatorenliste- und ein
Stufe->Gruppe-Bezug fachlich bedeuten. Der Blattwerk-Kern kennt nur den
rein syntaktischen `operator`-Run-Flag und das generische, inhaltlich
bedeutungslose `Stufe`-Frontmatter-Enum (`blatt_validator_constants.py`) --
beides bleibt unverändert nutzbar, wenn dieses Modul nie eine passende
`data/operatoren/<fach>.json` findet oder gar nicht aufgerufen wird.

Zwei Aufrufstellen teilen sich `collect_used_operators()`:
- `blatt_validator.py::_collect_document_diagnostics` (Validierung, surfaced
  `OPR001`/`OPR003` im Editor/CLI wie jede andere Diagnose),
- `blatt_kern_layout_render.py::render_html` (Rendering, nutzt nur die
  zurückgegebenen `MatchedOperator`s für die Legende, ignoriert die
  Diagnosen -- die sind zu diesem Zeitpunkt bereits über die Validierung
  gelaufen). Operator-Matching ist reine Textverarbeitung (kein
  Zufalls-/Backtracking-Algorithmus wie beim Crossword) und daher bewusst
  NICHT über `block_computation_cache.py` gecacht -- zweimal berechnen ist
  hier billiger als eine Cache-Infrastruktur dafür.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from html import escape

from .blatt_validator_types import BuildDiagnostic
from .export_path_guardrails import PROJECT_ROOT
from .inline_markup import parse_inline_markup

OPERATOR_DATA_DIR = PROJECT_ROOT / "data" / "operatoren"

# Operator-Diagnosen sind dokumentweit (Fach/Stufe-getrieben, nicht an einen
# einzelnen Block gebunden) -- derselbe generische Dokument-Bucket wie bei
# den strukturellen Marker-Syntax-Diagnosen (`blatt_validator_marker_syntax.py`).
_OPERATOR_REGION_ID = "worksheet:document-text"


@dataclass(frozen=True)
class OperatorEntry:
    """Ein Operator aus einer `data/operatoren/<fach>.json`-Datei."""

    key: str
    definition: str
    formen: tuple[str, ...] = ()
    """Normalisierte (kleingeschrieben) Oberflächenformen, gegen die markierter
    Text exakt verglichen wird -- keine Stamm-/Präfix-Heuristik (siehe
    DEVELOPMENT_LOG.md: bewusst verworfen zugunsten expliziter Formen)."""
    stufen: tuple[str, ...] = ()
    """Namen von Gruppen aus `OperatorDataset.stufengruppen` (oder, wenn die
    Datei keine `stufengruppen` definiert, direkt rohe `Stufe`-Werte), für
    die dieser Operator verfügbar ist. Leer = für alle Stufen verfügbar."""


@dataclass(frozen=True)
class OperatorDataset:
    """Der geladene Inhalt einer `data/operatoren/<fach>.json`-Datei."""

    operatoren: tuple[OperatorEntry, ...]
    stufengruppen: dict = field(default_factory=dict)
    """`{Gruppenname: (Stufe-Wert, ...)}`. Leer, wenn die Datei keine
    Gruppen definiert -- dann werden `OperatorEntry.stufen`-Einträge als
    rohe `Stufe`-Werte interpretiert (Identitäts-Fallback, siehe
    `_resolve_matched_groups`)."""


@dataclass(frozen=True)
class MatchedOperator:
    """Ein im Dokument tatsächlich verwendeter, aufgelöster Operator."""

    key: str
    definition: str


def _slugify_fach(fach) -> str:
    """Normalizes a `Fach` name to the lowercase, filesystem-safe slug used
    as `data/operatoren/<slug>.json`'s filename (e.g. "Mathematik" -> "mathematik").

    `str(...)`-wrapped before any string method: YAML parses an unquoted
    numeric-looking frontmatter value as an `int`, not a `str` (the same
    issue that made `Stufe: 11` unquoted crash `_resolve_matched_groups`
    below), so `fach` isn't guaranteed to already be a string here.
    """
    text = str(fach or "").strip().lower()
    return "".join(ch if ch.isalnum() else "_" for ch in text)


def load_operator_data(fach: str) -> OperatorDataset | None:
    """Loads `data/operatoren/<slug(fach)>.json`, or `None` if no such file exists."""
    fach_slug = _slugify_fach(fach)
    if not fach_slug:
        return None
    path = OPERATOR_DATA_DIR / f"{fach_slug}.json"
    if not path.is_file():
        return None

    raw = json.loads(path.read_text(encoding="utf-8"))
    stufengruppen = {
        str(name): tuple(str(value) for value in values)
        for name, values in (raw.get("stufengruppen") or {}).items()
    }
    operatoren = tuple(
        OperatorEntry(
            key=str(entry.get("key", "")),
            definition=str(entry.get("definition", "")),
            formen=tuple(str(form).strip().lower() for form in entry.get("formen", [])),
            stufen=tuple(str(value) for value in entry.get("stufen", [])),
        )
        for entry in raw.get("operatoren", [])
        if entry.get("key")
    )
    return OperatorDataset(operatoren=operatoren, stufengruppen=stufengruppen)


def _resolve_matched_groups(stufe_value, stufengruppen):
    """Resolves a document's `Stufe` value to the set of group names it belongs to.

    No `stufengruppen` defined in the dataset -> identity fallback, the raw
    `stufe_value` itself is treated as its own (singleton) group name. A
    `stufe_value` may legitimately belong to more than one group (plain set
    membership, not a partition) -- availability is a union check, so this
    can never produce a conflict (see DEVELOPMENT_LOG.md).

    Comparisons are case-insensitive throughout: the core `Stufe` enum
    (`blatt_validator_constants.py`) accepts its values case-insensitively
    (`q1`/`Q1` both valid), so the raw frontmatter value can arrive in
    either case -- group names/values authored in the JSON keep their
    original display casing, only the comparison itself is lowercased.

    `str(...)`-wrapped before `.strip()`: YAML parses an unquoted numeric
    frontmatter value like `Stufe: 11` as an `int`, not a `str` -- without
    this, `stufe_value.strip()` raised `AttributeError` for exactly that
    (real-world-found) case.
    """
    if not stufe_value:
        return set()
    normalized_stufe = str(stufe_value).strip().lower()
    if not stufengruppen:
        return {normalized_stufe}
    return {
        name
        for name, values in stufengruppen.items()
        if normalized_stufe in {value.lower() for value in values}
    }


def _operator_available(entry, stufe_value, matched_groups):
    """True if `entry` should be considered for matching in this document.

    No `Stufe` set on the document at all -> every operator is available,
    regardless of its own `stufen` (no filtering possible without a
    document-level Stufe to filter by). `Stufe` set but not covered by any
    group in this dataset (or the dataset defines no groups at all) still
    only narrows entries that actually declare `stufen` -- unrestricted
    entries remain available either way.
    """
    if not stufe_value:
        return True
    if not entry.stufen:
        return True
    normalized_entry_stufen = {value.lower() for value in entry.stufen}
    normalized_matched_groups = {group.lower() for group in matched_groups}
    return bool(normalized_entry_stufen & normalized_matched_groups)


def _normalize_marked_text(text):
    return text.strip().strip(".,:;!?").lower()


def collect_used_operators(blocks, meta):
    """Scans `blocks` for `!!...!!`-marked operator text and resolves it
    against the `Fach`/`Stufe`-appropriate operator dataset.

    Returns `(matched_operators, diagnostics)`:
    - `matched_operators`: deduplicated `MatchedOperator`s in first-seen
      order, for building the Arbeitsblatt-only legend.
    - `diagnostics`: `OPR001` (unmatched marker text) / `OPR003` (no
      dataset for this `Fach`) `BuildDiagnostic`s, meant to be surfaced by
      the validator like any other diagnostic code.

    Cheap no-op guard: if no block contains an `operator=True` run at all,
    returns `([], [])` immediately without touching the filesystem --
    the Haus/Garage contract that a document never using the marker
    behaves exactly as if this module didn't exist.
    """
    parsed_blocks = [parse_inline_markup(content or "")[0] for _block_type, _options, content in blocks]
    if not any(run.operator for runs in parsed_blocks for run in runs):
        return [], []

    fach = (meta or {}).get("Fach", "")
    dataset = load_operator_data(fach)
    if dataset is None:
        return [], [
            BuildDiagnostic(
                code="OPR003",
                message=(
                    f"`!!...!!`-Operator-Marker verwendet, aber keine Operatoren-Datei für "
                    f"Fach „{fach}“ gefunden (`data/operatoren/`)."
                ),
                region_id=_OPERATOR_REGION_ID,
                anchor="",
            )
        ]

    stufe_value = (meta or {}).get("Stufe") or None
    matched_groups = _resolve_matched_groups(stufe_value, dataset.stufengruppen)
    available_entries = [
        entry for entry in dataset.operatoren if _operator_available(entry, stufe_value, matched_groups)
    ]
    form_lookup = {form: entry for entry in available_entries for form in entry.formen}

    matched: list[MatchedOperator] = []
    seen_keys: set[str] = set()
    diagnostics: list[BuildDiagnostic] = []
    for runs in parsed_blocks:
        for run in runs:
            if not run.operator:
                continue
            entry = form_lookup.get(_normalize_marked_text(run.text))
            if entry is None:
                diagnostics.append(
                    BuildDiagnostic(
                        code="OPR001",
                        message=(
                            f"Operator-Marker „{run.text}“ passt zu keinem bekannten Operator "
                            f"(Fach „{fach}“)."
                        ),
                        region_id=_OPERATOR_REGION_ID,
                        anchor=_normalize_marked_text(run.text),
                    )
                )
                continue
            if entry.key not in seen_keys:
                seen_keys.add(entry.key)
                matched.append(MatchedOperator(key=entry.key, definition=entry.definition))

    return matched, diagnostics


def render_operator_legend_html(matched_operators):
    """Renders the Arbeitsblatt-only operator legend as a simple `key: definition` list."""
    if not matched_operators:
        return ""
    items = "".join(
        f"<li><span class='operator-legend-key'>{escape(operator.key)}</span>: "
        f"<span class='operator-legend-definition'>{escape(operator.definition)}</span></li>"
        for operator in matched_operators
    )
    return (
        "<div class='operator-legend'>"
        "<h4 class='operator-legend-heading'>Operatoren</h4>"
        f"<ul class='operator-legend-list'>{items}</ul>"
        "</div>"
    )
