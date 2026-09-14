"""Operatoren-Legende -- die "Garage" im Haus/Garage-Prinzip (siehe DEVELOPMENT_LOG.md).

Einzige Stelle im Code, die weiß, was ein Aufgaben-Operator (`!!...!!`-Marker,
siehe `inline_markup/syntax.py`), ein Fach->Operatorenliste- und ein
Stufe->Gruppe-Bezug fachlich bedeuten. Der Blattwerk-Kern kennt nur den
rein syntaktischen `operator`-Run-Flag und das generische, inhaltlich
bedeutungslose `Stufe`-Frontmatter-Enum (`blatt_validator_constants.py`) --
beides bleibt unverändert nutzbar, wenn dieses Modul nie eine passende
`data/operatoren/<fach>.json` findet oder gar nicht aufgerufen wird.

Drei Konsumenten teilen sich dasselbe `OperatorDataset` und dieselbe
Verfügbarkeits-Logik (`_resolve_available_entries` -> `_resolve_matched_groups`/
`_operator_available`), keiner leitet Operatoren-Wissen unabhängig neu her:
- `collect_used_operators()`, selbst wieder von zwei Stellen aufgerufen:
  `blatt_validator.py::_collect_document_diagnostics` (Validierung, surfaced
  `OPR001`/`OPR003` im Editor/CLI wie jede andere Diagnose) und
  `blatt_kern_layout_render.py::render_html` (Rendering, nutzt nur die
  zurückgegebenen `MatchedOperator`s für die Legende, ignoriert die
  Diagnosen -- die sind zu diesem Zeitpunkt bereits über die Validierung
  gelaufen).
- `list_operator_suggestions()`, von `completion_catalogs.py::get_completion_operator_forms`
  für Editor-Autocomplete innerhalb eines offenen `!!...!!`-Markers aufgerufen.
  Liefert rohe `vorschlag`-Strings, keine UI-Struktur -- das Formatieren zu
  `label`/`insert_text`-Dicts ist Sache von `blatt_ui_editor_completion_context.py`.
  Dieses Modul bleibt dadurch frei von jeder Editor-/UI-Abhängigkeit.

Operator-Matching ist reine Textverarbeitung (kein Zufalls-/Backtracking-
Algorithmus wie beim Crossword) und daher bewusst NICHT über
`block_computation_cache.py` gecacht. `load_operator_data()` hat aber einen
eigenen, kleinen mtime-Cache (siehe dort) -- die Autocomplete-Aufrufstelle
läuft synchron auf jedem Tastendruck, wiederholtes Neu-Parsen derselben
Datei wäre vermeidbares I/O.

Dieses Modul wird durch diese drei Konsumenten NICHT weiter aufgespalten
(z. B. in `operator_catalog.py`/`operator_matching.py`/`operator_suggestions.py`)
-- das bleibt eine sinnvolle fachliche Einheit, solange kein tatsächlich
unabhängiger zweiter Verantwortungsbereich oder ein erkennbares
Größen-/Kopplungsproblem entsteht.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

from .blatt_validator_types import BuildDiagnostic
from .export_path_guardrails import PROJECT_ROOT
from .inline_markup import parse_inline_markup

OPERATOR_DATA_DIR = PROJECT_ROOT / "data" / "operatoren"

_dataset_cache: dict[Path, tuple[int, "OperatorDataset | None"]] = {}
"""`{resolved_path: (mtime_ns, dataset)}` -- see `load_operator_data`. Keyed
by the resolved file path (not the `Fach` name/slug) so a test that
monkeypatches `OPERATOR_DATA_DIR` to a different temp directory can never
collide with a cache entry from an earlier, differently-located file of
the same slug."""

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
    vorschlag: tuple[str, ...] = ()
    """Die offizielle(n) Bezeichnung(en) aus der Tabellenspalte "Operator" der
    Quelle, korrekt großgeschrieben -- für Editor-Autocomplete
    (`list_operator_suggestions`). Bewusst getrennt von `formen`: die
    Konjugationsvarianten dort sind fürs Matching gedacht, nicht dafür,
    dem Autor beim Tippen vorgeschlagen zu werden (siehe DEVELOPMENT_LOG.md)."""
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
    """Loads `data/operatoren/<slug(fach)>.json`, or `None` if no such file exists.

    Cached in-memory by resolved file path, invalidated via `st_mtime_ns`
    (see `_dataset_cache`) -- the completion path (Teil 3, `!!...!!`
    autocomplete) calls this on every keystroke inside an open marker, and
    re-reading + re-parsing the same ~100-line file on every keystroke
    would be avoidable I/O. Editing the JSON file mid-session invalidates
    the cache automatically; no negative-cache for "file doesn't exist" --
    `path.stat()` on a missing path is already a single cheap syscall, the
    actually expensive part (`json.loads`) is already skipped for it.
    """
    fach_slug = _slugify_fach(fach)
    if not fach_slug:
        return None
    path = (OPERATOR_DATA_DIR / f"{fach_slug}.json").resolve()
    try:
        mtime_ns = path.stat().st_mtime_ns
    except OSError:
        return None

    cached = _dataset_cache.get(path)
    if cached is not None and cached[0] == mtime_ns:
        return cached[1]

    dataset = _load_operator_dataset_from_path(path)
    _dataset_cache[path] = (mtime_ns, dataset)
    return dataset


def _load_operator_dataset_from_path(path: Path) -> OperatorDataset | None:
    """Reads and parses one `data/operatoren/<fach>.json` file. No caching here --
    that's `load_operator_data`'s job; this is the actual I/O+parse."""
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
            vorschlag=tuple(str(form).strip() for form in entry.get("vorschlag", [])),
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


def _resolve_available_entries(fach, stufe_value):
    """Loads the operator dataset for `fach` and filters it down to the
    entries available for `stufe_value` (`_resolve_matched_groups`/
    `_operator_available`, the one shared availability decision -- see
    DEVELOPMENT_LOG.md). Returns `None` when no dataset exists for `fach`
    at all (distinct from an empty tuple, which means a dataset exists but
    `stufe_value` filtering excluded every entry).

    Shared by `collect_used_operators` (legend/validator) and
    `list_operator_suggestions` (autocomplete) so both can never
    structurally diverge on which operators are available for a document.
    """
    dataset = load_operator_data(fach)
    if dataset is None:
        return None
    matched_groups = _resolve_matched_groups(stufe_value, dataset.stufengruppen)
    return tuple(
        entry for entry in dataset.operatoren if _operator_available(entry, stufe_value, matched_groups)
    )


def list_operator_suggestions(fach, stufe) -> tuple[str, ...]:
    """Returns the deduplicated, alphabetically sorted official suggestion
    labels (`OperatorEntry.vorschlag`) for every operator available under
    `fach`/`stufe` -- for editor autocomplete inside an open `!!...!!`
    marker (see `blatt_ui_editor_completion_context.py`). Empty tuple if no
    dataset exists for `fach`; no exception either way.

    Deliberately returns raw strings, not a UI-shaped structure (no
    `label`/`insert_text` dict) -- that formatting is the UI layer's job
    (`_build_operator_suggestions`), keeping this module free of any
    editor/completion dependency.
    """
    available_entries = _resolve_available_entries(fach, stufe)
    if available_entries is None:
        return ()
    suggestions = {label for entry in available_entries for label in entry.vorschlag}
    return tuple(sorted(suggestions))


def list_operator_suggestion_details(fach, stufe) -> dict[str, str]:
    """Returns `{vorschlag_label: definition}` for every operator available
    under `fach`/`stufe` -- the explanation text behind the editor
    autocomplete's detail overlay (see `blatt_ui_editor_completion_popup.py`
    / `completion_catalogs.py::get_completion_operator_details`).

    Mirrors `list_operator_suggestions`'s availability resolution exactly
    (same `_resolve_available_entries()` call), so the detail overlay can
    never show a definition for a label the suggestion list itself would
    not offer. `{}` for the same cases `list_operator_suggestions` returns
    `()` for.

    When multiple entries share the same `vorschlag` label (possible for
    grouped operators, e.g. two dataset entries both suggesting
    "Bestimmen"), the first one encountered wins -- deterministic (dataset
    order), but not claimed to be semantically the "right" one for that
    edge case; it simply avoids depending on dict-iteration order.
    """
    available_entries = _resolve_available_entries(fach, stufe)
    if available_entries is None:
        return {}
    details: dict[str, str] = {}
    for entry in available_entries:
        for label in entry.vorschlag:
            details.setdefault(label, entry.definition)
    return details


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
    stufe_value = (meta or {}).get("Stufe") or None
    available_entries = _resolve_available_entries(fach, stufe_value)
    if available_entries is None:
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
    """Renders the Arbeitsblatt-only operator legend as a two-column table
    (operator | definition), matching the source PDF's layout. No heading --
    the table is self-explanatory next to the marked-up operators above it.
    """
    if not matched_operators:
        return ""
    rows = "".join(
        "<tr>"
        f"<td class='operator-legend-key'>{escape(operator.key)}</td>"
        f"<td class='operator-legend-definition'>{escape(operator.definition)}</td>"
        "</tr>"
        for operator in matched_operators
    )
    return f"<table class='operator-legend'><tbody>{rows}</tbody></table>"
