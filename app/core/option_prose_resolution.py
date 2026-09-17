"""Löst auf, welcher `PROSE_SECTIONS`-Key eine Block-Option redaktionell erklärt.

Verschoben aus `tools/docs/authoring_guide_coverage.py` (semantisch
unverändert) -- `app/core` darf niemals von `tools/docs` abhängen
(Einbahnstraße, siehe `authoring_guide_prose.py`s Moduldocstring), diese
Resolver-Logik wird aber jetzt sowohl vom Doku-Generator als auch von der
Editor-Autocomplete-Detailspalte (`app/core/completion_catalogs.py`)
gebraucht. `tools/docs/authoring_guide_coverage.py` importiert sie
seitdem von hier, statt eine zweite, unabhängig gepflegte Kopie zu führen.

Pro Optionsname wird über alle Blöcke die "Mehrheitsvariante" ermittelt
(`kind`/`allowed_values`/`validated` -- der `default` zählt bewusst nicht
mit). Teilt ein Block diese Mehrheit, gilt der generische
`option:<name>`-Prosa-Key (ein `block:<block>.<name>`-Supplement darf
zusätzlich existieren); weicht er ab (oder gibt es keine Mehrheit), gilt
**nur** der block-eigene `block:<block>.<name>`-Key.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Mapping

from .blatt_validator_constants import BlockOptionSpec
from .markdown_conventions import MarkdownConventionCatalog, collect_markdown_conventions


@dataclass(frozen=True)
class OptionProseResolution:
    """Welcher Prosa-Key gilt für eine Block-Option, und darf zusätzlich ein
    block-spezifisches Supplement existieren? Ersetzt ein früheres
    `tuple[str, bool]` durch ein benanntes Ergebnisobjekt."""

    key: str
    allow_block_supplement: bool


def _option_variant_key(spec: BlockOptionSpec) -> tuple:
    """Fakten, die entscheiden, ob zwei Blöcke 'dieselbe' Option meinen (Default zählt nicht mit)."""
    return (spec.kind, spec.allowed_values, spec.validated)


def build_majority_variant_map(catalog: MarkdownConventionCatalog) -> Mapping[str, tuple]:
    """Für jeden Optionsnamen: die von den meisten Blöcken geteilte Variante (kind/allowed_values/validated).

    Nur wenn diese "Mehrheitsvariante" von **mindestens zwei** Blöcken
    geteilt wird, gilt die Option als generisches, block-übergreifendes
    Konzept (`option:<name>`-Prosa reicht). Bei genau einem Nutzer pro
    Variante (z. B. `alignment` bei `qrcode` vs. `table` -- zwei völlig
    verschiedene Bedeutungen) gibt es keine Mehrheit; jeder Block braucht
    dann eine eigene `block:<block>.<name>`-Erklärung, keine generische.

    Nimmt `catalog` explizit als Parameter entgegen (statt selbst zu
    cachen) -- Aufrufer wie `tools/docs` arbeiten in Tests bewusst mit
    synthetischen/modifizierten Katalogen (siehe
    `test_render_worksheet_presentation_guide_changes_when_catalog_changes`),
    ein interner Cache hier würde das kaputt machen. Der Editor-
    Completion-Pfad, der IMMER den echten, zur Laufzeit unveränderlichen
    Katalog braucht, cacht stattdessen selbst (`_default_majority_variants()`
    unten) -- ohne den Katalog dafür hashen zu müssen.
    """
    counters: dict[str, Counter] = {}
    for block in catalog.blocks:
        for spec in block.options:
            counters.setdefault(spec.name, Counter())[_option_variant_key(spec)] += 1

    majority: dict[str, tuple] = {}
    for name, counter in counters.items():
        variant, count = counter.most_common(1)[0]
        if count >= 2:
            majority[name] = variant
    return majority


_cached_majority_variants: Mapping[str, tuple] | None = None


def _default_majority_variants() -> Mapping[str, tuple]:
    """Einmalig berechnete Mehrheitsvarianten für den echten, laufenden
    Katalog (`collect_markdown_conventions()`) -- `BLOCK_OPTION_SPECS`
    ändert sich zur Laufzeit nie, ein Modul-Singleton wird also nie stale.

    Bewusst kein `functools.lru_cache` auf einer Funktion mit `catalog`-
    Parameter (keine Hashability-Annahme über den Katalog nötig) und kein
    `id(catalog)`-Keying (riskiert nach Garbage Collection eine
    Objekt-Adressen-Kollision mit einem unabhängigen späteren Objekt) --
    stattdessen ein einfacher, expliziter Einmal-Cache genau für DIESEN
    einen, garantiert stabilen Katalog. Wird übersprungen, sobald
    `resolve_option_prose_key()` ein eigenes `majority_variants` bekommt.
    """
    global _cached_majority_variants
    if _cached_majority_variants is None:
        _cached_majority_variants = build_majority_variant_map(collect_markdown_conventions())
    return _cached_majority_variants


def resolve_option_prose_key(
    block_name: str,
    spec: BlockOptionSpec,
    *,
    majority_variants: Mapping[str, tuple] | None = None,
) -> OptionProseResolution:
    """Liefert, welcher Prosa-Key eine Block-Option erklärt.

    `majority_variants`: vorab per `build_majority_variant_map(catalog)`
    berechnet. Ohne Angabe wird die einmalig gecachte Mehrheitsvariante
    des echten, laufenden Katalogs verwendet (`_default_majority_variants()`)
    -- Aufrufer, die mit einem anderen/synthetischen Katalog arbeiten
    (Doku-Generator-Tests), müssen ihre eigene Mehrheitsvariante explizit
    übergeben, statt sich auf diesen Default zu verlassen.
    """
    variants = majority_variants if majority_variants is not None else _default_majority_variants()
    generic_key = f"option:{spec.name}"
    specific_key = f"block:{block_name}.{spec.name}"

    if variants.get(spec.name) == _option_variant_key(spec):
        return OptionProseResolution(key=generic_key, allow_block_supplement=True)
    return OptionProseResolution(key=specific_key, allow_block_supplement=False)
