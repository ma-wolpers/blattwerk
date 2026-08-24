"""Prosa-Coverage-Erzwingung für die generierten Autoren-Anleitungen.

`assert_prose_coverage()` verhindert, dass ein neues DSL-Element (neuer
Blocktyp, neues Frontmatter-Feld, neuer Control-Marker, neue Geometry-
Sektion, neue Kurzentwurf-Phase/-Zeilenmarker/-Legacy-Feld) unbemerkt ohne
redaktionelle Erklärung in die generierte Anleitung rutscht.

Greift wie `authoring_guide_render_shared.py` bewusst qualifiziert auf
`authoring_guide_prose.PROSE_SECTIONS` zu, damit Tests das Modul per
`monkeypatch` austauschen können, ohne dass diese Prüfung eine eigene,
unabhängige Kopie des Namens liest.
"""

from __future__ import annotations

from collections import Counter

import authoring_guide_prose

from app.core.markdown_conventions import MarkdownConventionCatalog  # noqa: E402


class ProseCoverageError(Exception):
    """Ein Katalogeintrag hat keine zugehörige Prosa-Erklärung in `PROSE_SECTIONS`."""


def _option_variant_key(spec: object) -> tuple:
    """Fakten, die entscheiden, ob zwei Blöcke 'dieselbe' Option meinen (Default zählt nicht mit)."""
    return (spec.kind, spec.allowed_values, spec.validated)


def _majority_variant_by_option_name(catalog: MarkdownConventionCatalog) -> dict[str, tuple]:
    """Für jeden Optionsnamen: die von den meisten Blöcken geteilte Variante (kind/allowed_values/validated).

    Nur wenn diese "Mehrheitsvariante" von **mindestens zwei** Blöcken
    geteilt wird, gilt die Option als generisches, block-übergreifendes
    Konzept (`option:<name>`-Prosa reicht). Bei genau einem Nutzer pro
    Variante (z. B. `alignment` bei `qrcode` vs. `table` -- zwei völlig
    verschiedene Bedeutungen) gibt es keine Mehrheit; jeder Block braucht
    dann eine eigene `block:<block>.<name>`-Erklärung, keine generische.
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


def _option_prose_keys(catalog: MarkdownConventionCatalog, block_name: str, spec: object) -> tuple[str, bool]:
    """Liefert (bevorzugter Prosa-Key, ob zusätzlich noch ein Shared-Key existieren darf) für eine Option.

    Rückgabe `(key, allow_shared_supplement)`: wenn die Option des Blocks
    der Mehrheitsvariante entspricht, ist `key` der generische
    `option:<name>`-Key (ein optionales `block:<block>.<name>`-Supplement
    darf zusätzlich existieren). Weicht der Block von der Mehrheit ab
    (oder gibt es gar keine Mehrheit), ist `key` der block-eigene
    `block:<block>.<name>`-Key, der dann **alleinstehend** gilt (kein
    Shared-Text, der inhaltlich falsch wäre).
    """
    majority = _majority_variant_by_option_name(catalog)
    generic_key = f"option:{spec.name}"
    specific_key = f"block:{block_name}.{spec.name}"

    if majority.get(spec.name) == _option_variant_key(spec):
        return generic_key, True
    return specific_key, False


def _geometry_prose_keys() -> tuple[str, ...]:
    return (
        "geometry:block_options",
        "geometry:points",
        "geometry:sequence",
        "geometry:pairs",
        "geometry:functions",
    )


def _kurzentwurf_prose_keys(catalog: MarkdownConventionCatalog) -> tuple[str, ...]:
    keys = [
        "kurzentwurf:phases",
        "kurzentwurf:identity_meta",
        "kurzentwurf:legacy_detection_only",
        "kurzentwurf:markers",
    ]
    keys.extend(f"kurzentwurf:phase:{spec.hashtag}" for spec in catalog.kurzentwurf.phase_specs)
    keys.extend(f"kurzentwurf:marker:{spec.token}" for spec in catalog.kurzentwurf.line_markers)
    keys.extend(f"kurzentwurf:legacy:{name}" for name in catalog.kurzentwurf.legacy_detection_only_keys)
    return tuple(keys)


def assert_prose_coverage(catalog: MarkdownConventionCatalog) -> None:
    """Wirft `ProseCoverageError`, wenn ein Katalogeintrag keine Prosa-Erklärung hat.

    Prüft auf zwei Ebenen: jeder Blocktyp braucht `block:<name>` (die
    einleitende Blockbeschreibung); jede Option jedes Blocks braucht
    *mindestens* die von `_option_prose_keys` bestimmte Erklärung (generisch
    `option:<name>` für Mehrheitsvarianten, sonst zwingend die block-eigene
    `block:<block>.<name>`) -- ein block-spezifisches Supplement zusätzlich
    zum generischen Text ist immer erlaubt, aber nie Pflicht.
    """
    required_keys: list[str] = []
    required_keys.extend(f"block:{block.name}" for block in catalog.blocks)
    required_keys.extend(f"frontmatter:{name}" for name in catalog.required_frontmatter_fields)
    required_keys.extend(f"frontmatter:{field.name}" for field in catalog.optional_frontmatter_fields)
    required_keys.extend(f"marker:{marker.name}" for marker in catalog.control_markers)
    required_keys.extend(_geometry_prose_keys())
    required_keys.extend(_kurzentwurf_prose_keys(catalog))
    required_keys.append("presentation:visibility")
    required_keys.append("blocks:closing_rule")

    missing = [key for key in required_keys if key not in authoring_guide_prose.PROSE_SECTIONS]

    for block in catalog.blocks:
        for spec in block.options:
            key, _allow_supplement = _option_prose_keys(catalog, block.name, spec)
            if key not in authoring_guide_prose.PROSE_SECTIONS:
                missing.append(key)

    if missing:
        raise ProseCoverageError(
            "Fehlende Prosa-Abschnitte in tools/docs/authoring_guide_prose.py: "
            + ", ".join(sorted(set(missing)))
        )
