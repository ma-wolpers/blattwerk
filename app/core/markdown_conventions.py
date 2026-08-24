"""Introspektions-Collector für die Blattwerk-Markdown-Konventionen (Arbeitsblatt/Präsentation + Kurzentwurf).

**Zentrale Leitplanke:** Dieses Modul darf vorhandenes Wissen aus Parser,
Validator und Kurzentwurf-Runtime sichtbar machen, aber **kein neues
DSL-Wissen erfinden**. Jedes Feld in `MarkdownConventionCatalog` ist eine
reine Re-Verpackung einer bereits an anderer Stelle normativen Konstante:

```
Parser / Validator / Runtime (bestehende normative Konstanten)
        -> markdown_conventions.py (dieses Modul, reine Re-Verpackung)
        -> tools/docs/generate_authoring_guides.py (Katalog + Prosa)
        -> docs/ANLEITUNG_*.md
```

Quellen im Einzelnen:
- `blatt_validator_constants.py`: Frontmatter-Felder (`REQUIRED_FRONTMATTER_FIELDS`/
  `OPTIONAL_FRONTMATTER_FIELDS`), Blocktypen/-optionen inkl. Pro-Options-
  Fakten (`BLOCK_OPTION_SPECS`, davon `BLOCK_ALLOWED_OPTIONS` abgeleitet),
  Wertlisten (`KNOWN_WORK_VALUES`/`KNOWN_ACTION_VALUES`/`KNOWN_HINT_VALUES`),
  Grid-/Geometry-Linienstile (`KNOWN_GRID_LINE_STYLES`).
- `blatt_kern_shared_data.py`: Control-Marker-Syntax (`CONTROL_MARKERS`) --
  dieselbe Quelle, die auch der Parser (`blatt_kern_shared_parsing.py`) und
  der Validator (`blatt_validator_patterns.py`) verwenden.
- `block_insert_snippets.py` (`BLOCK_INSERT_SNIPPETS`): dieselben Ctrl+B-
  Einfüge-Vorlagen, die der Editor (`app/ui/blatt_ui_editor.py`) tatsächlich
  einfügt -- re-verpackt als `BlockSpec.insert_snippet`.
- `answer_grid_entries.py`: Geometry-Objekt-Felder (`GEOMETRY_ENTRY_ALLOWED_KEYS`)
  -- dieselbe Quelle, die auch Renderer und Validator (`AN011`-`AN014`)
  verwenden.
- `kurzentwurf_runtime/model.py` (`PHASE_SPECS`, davon `ALLOWED_PHASES`
  abgeleitet; `LINE_MARKER_SPECS`) und `kurzentwurf_runtime/dsl_frontmatter.py`
  (`TITLE_KEYS`/`SUBTITLE_KEYS`/`START_KEYS`): die tatsächlich vom
  Kurzentwurf-DSL-Parser verstandenen Phasen (inkl. `#`-Hashtag, nicht nur
  Anzeigename), Zeilenmarker und Identitäts-Metadaten-Keys. `validator.py`
  bezieht seine `_PHASE_LOOKUP`/`_OPTIONAL_TIME_PHASES` ebenfalls aus
  `PHASE_SPECS` -- eine einzige Quelle für Hashtag-Zuordnung.
- `document_types.py` (`KURZENTWURF_LEGACY_DETECTION_SUPPORT_KEYS`): Keys,
  die **nur** zur Alt-Erkennung beitragen, nicht zur funktionalen DSL
  gehören -- werden deshalb separat als `legacy_detection_only_keys`
  geführt, nicht mit den echten Identitäts-Keys vermischt.
"""

from __future__ import annotations

from dataclasses import dataclass

from .answer_grid_entries import GEOMETRY_ENTRY_ALLOWED_KEYS
from .blatt_kern_shared_data import CONTROL_MARKERS, ControlMarkerSpec
from .block_insert_snippets import BLOCK_INSERT_SNIPPETS
from .blatt_validator_constants import (
    BLOCK_OPTION_SPECS,
    KNOWN_ACTION_VALUES,
    KNOWN_BLOCK_TYPES,
    KNOWN_GRID_LINE_STYLES,
    KNOWN_HINT_VALUES,
    KNOWN_WORK_VALUES,
    OPTIONAL_FRONTMATTER_FIELDS,
    REQUIRED_FRONTMATTER_FIELDS,
    BlockOptionSpec,
    FrontmatterFieldSpec,
)
from .document_types import KURZENTWURF_LEGACY_DETECTION_SUPPORT_KEYS
from .kurzentwurf_runtime.dsl_frontmatter import START_KEYS, SUBTITLE_KEYS, TITLE_KEYS
from .kurzentwurf_runtime.model import ALLOWED_PHASES, LINE_MARKER_SPECS, PHASE_SPECS, LineMarkerSpec, PhaseSpec


@dataclass(frozen=True)
class BlockSpec:
    """Ein Blattwerk-`:::`-Blocktyp mit seinen Optionen -- inklusive Pro-Options-Fakten.

    Reine Re-Verpackung von `BLOCK_OPTION_SPECS[name]` -- keine
    zusätzlichen Felder wie `requires`/`mutually_exclusive`, da diese
    Informationen im Code nirgends normativ existieren. `insert_snippet`
    ist die reine Re-Verpackung von `BLOCK_INSERT_SNIPPETS.get(name)` --
    ein *minimales, bequemes Beispiel* (dasselbe, das Ctrl+B im Editor
    einfügt), keine vollständige Grammatikspezifikation; `None`, wenn der
    Blocktyp keinen Ctrl+B-Menüeintrag hat.
    """

    name: str
    options: tuple[BlockOptionSpec, ...]
    insert_snippet: str | None


@dataclass(frozen=True)
class GeometryEntrySpec:
    """Erlaubte YAML-Keys einer Geometry-Objekt-Sektion (`points`/`sequence`/`pairs`/`functions`).

    Reine Re-Verpackung von `GEOMETRY_ENTRY_ALLOWED_KEYS[section]`
    (`answer_grid_entries.py`) -- der Wertsyntax von `color`/`thickness`
    wird bewusst **nicht** hier codiert (kein Enum, keine Regex-
    Nachbildung); das wäre erfundenes DSL-Wissen. Die redaktionelle Prosa
    beschreibt sie stattdessen in Worten (CSS-Farbwert bzw. positive Zahl).
    """

    section: str
    allowed_keys: frozenset[str]


@dataclass(frozen=True)
class GeometrySpec:
    """Vollständige Geometry-DSL-Fakten: Block-Linienstil plus die vier Objekt-Sektionen."""

    line_styles: frozenset[str]
    entries: tuple[GeometryEntrySpec, ...]


@dataclass(frozen=True)
class KurzentwurfSpec:
    """Kurzentwurf-DSL-Fakten: Phasen, echte Identitäts-Keys, reine Alt-Erkennungs-Keys.

    `identity_meta_keys` sind die vom DSL-Parser tatsächlich verstandenen
    Aliase für Titel/Untertitel/Startzeit (`TITLE_KEYS`/`SUBTITLE_KEYS`/
    `START_KEYS`, `kurzentwurf_runtime/dsl_frontmatter.py`).
    `legacy_detection_only_keys` werden dagegen von `kurzentwurf_runtime`
    nirgends gelesen/gerendert -- reine Heuristik zur automatischen
    Dokumenttyp-Erkennung alter Dokumente (`document_types.py`). Diese
    Trennung ist bewusst, damit die generierte Anleitung die zweite
    Gruppe nicht fälschlich als aktive DSL-Felder bewirbt.
    """

    phases: tuple[str, ...]
    phase_specs: tuple[PhaseSpec, ...]
    line_markers: tuple[LineMarkerSpec, ...]
    identity_meta_keys: frozenset[str]
    legacy_detection_only_keys: frozenset[str]


@dataclass(frozen=True)
class MarkdownConventionCatalog:
    """Vollständige, aus dem Code introspektierte Sammlung der Blattwerk-Markdown-Konventionen.

    Konsumiert ausschließlich von `tools/docs/generate_authoring_guides.py`
    zur Erzeugung der Autoren-Anleitungen unter `docs/`.
    """

    required_frontmatter_fields: tuple[str, ...]
    optional_frontmatter_fields: tuple[FrontmatterFieldSpec, ...]
    blocks: tuple[BlockSpec, ...]
    work_values: frozenset[str]
    action_values: frozenset[str]
    hint_values: frozenset[str]
    control_markers: tuple[ControlMarkerSpec, ...]
    geometry: GeometrySpec
    kurzentwurf: KurzentwurfSpec


def collect_markdown_conventions() -> MarkdownConventionCatalog:
    """Baut den vollständigen Konventions-Katalog ausschließlich aus bestehenden Code-Konstanten.

    Reine Introspektion, kein I/O, keine eigene Validierungslogik --
    dieselben Konstanten, die Parser/Validator/Runtime bereits zur
    Laufzeit verwenden, werden hier nur in eine für die Doku-Generierung
    geeignete Form gebracht. `"raw"` (interner Pseudo-Blocktyp für
    Markdown außerhalb von `:::`-Blöcken, kein von Autor:innen selbst
    gesetzter Blocktyp) wird bewusst aus `blocks` ausgeschlossen.
    """
    blocks = tuple(
        BlockSpec(
            name=block_name,
            options=tuple(BLOCK_OPTION_SPECS.get(block_name, ())),
            insert_snippet=BLOCK_INSERT_SNIPPETS.get(block_name),
        )
        for block_name in sorted(KNOWN_BLOCK_TYPES)
        if block_name != "raw"
    )

    geometry_entries = tuple(
        GeometryEntrySpec(section=section, allowed_keys=frozenset(allowed_keys))
        for section, allowed_keys in GEOMETRY_ENTRY_ALLOWED_KEYS.items()
    )

    return MarkdownConventionCatalog(
        required_frontmatter_fields=tuple(REQUIRED_FRONTMATTER_FIELDS),
        optional_frontmatter_fields=tuple(OPTIONAL_FRONTMATTER_FIELDS),
        blocks=blocks,
        work_values=frozenset(KNOWN_WORK_VALUES),
        action_values=frozenset(KNOWN_ACTION_VALUES),
        hint_values=frozenset(KNOWN_HINT_VALUES),
        control_markers=tuple(CONTROL_MARKERS),
        geometry=GeometrySpec(
            line_styles=frozenset(KNOWN_GRID_LINE_STYLES),
            entries=geometry_entries,
        ),
        kurzentwurf=KurzentwurfSpec(
            phases=tuple(ALLOWED_PHASES),
            phase_specs=tuple(PHASE_SPECS),
            line_markers=tuple(LINE_MARKER_SPECS),
            identity_meta_keys=frozenset(TITLE_KEYS | SUBTITLE_KEYS | START_KEYS),
            legacy_detection_only_keys=frozenset(KURZENTWURF_LEGACY_DETECTION_SUPPORT_KEYS),
        ),
    )
