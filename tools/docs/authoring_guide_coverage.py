"""Prosa-Coverage-Erzwingung für die generierten Autoren-Anleitungen.

`assert_prose_coverage()` verhindert, dass ein neues DSL-Element (neuer
Blocktyp, neues Frontmatter-Feld, neuer Control-Marker, neue Geometry-
Sektion, neue Kurzentwurf-Phase/-Zeilenmarker/-Legacy-Feld) unbemerkt ohne
redaktionelle Erklärung in die generierte Anleitung rutscht.

Greift wie `authoring_guide_render_shared.py` bewusst qualifiziert auf
`authoring_guide_prose.PROSE_SECTIONS` zu, damit Tests das Modul per
`monkeypatch` austauschen können, ohne dass diese Prüfung eine eigene,
unabhängige Kopie des Namens liest.

Die Options-Prosa-Auflösung selbst (`resolve_option_prose_key`/
`build_majority_variant_map`) lebt in `app.core.option_prose_resolution`
-- gemeinsam genutzt mit der Editor-Autocomplete-Detailspalte, keine
zweite, unabhängig gepflegte Kopie hier.
"""

from __future__ import annotations

from app.core import authoring_guide_prose
from app.core.markdown_conventions import MarkdownConventionCatalog
from app.core.option_prose_resolution import build_majority_variant_map, resolve_option_prose_key


class ProseCoverageError(Exception):
    """Ein Katalogeintrag hat keine zugehörige Prosa-Erklärung in `PROSE_SECTIONS`."""


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
    *mindestens* die von `resolve_option_prose_key` bestimmte Erklärung (generisch
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
    required_keys.extend(f"inline_mark:{mark.name}" for mark in catalog.inline_marks)
    required_keys.append("presentation:visibility")
    required_keys.append("blocks:closing_rule")

    missing = [key for key in required_keys if key not in authoring_guide_prose.PROSE_SECTIONS]

    majority_variants = build_majority_variant_map(catalog)
    for block in catalog.blocks:
        for spec in block.options:
            resolution = resolve_option_prose_key(block.name, spec, majority_variants=majority_variants)
            if resolution.key not in authoring_guide_prose.PROSE_SECTIONS:
                missing.append(resolution.key)

    if missing:
        raise ProseCoverageError(
            "Fehlende Prosa-Abschnitte in tools/docs/authoring_guide_prose.py: "
            + ", ".join(sorted(set(missing)))
        )
