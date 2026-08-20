"""Bekannte Blocktypen, erlaubte Optionen und Wertemengen für den Blattwerk-Validator.

Reine Datendatei (Sets/Dicts ohne Logik) — vom 300-Zeilen-Limit ausgenommen.
`BLOCK_ALLOWED_OPTIONS` ist die normative Quelle für "welche `key=value`-
Optionen darf ein `:::blocktyp ...`-Header haben"; analog zur
Geometry-Objekt-Ebene (`GEOMETRY_ENTRY_ALLOWED_KEYS` in
`answer_grid_entries.py`) lebt dieses Wissen nur hier, nicht zusätzlich
verteilt über Validierungscode.
"""

from __future__ import annotations

from dataclasses import dataclass

from .blatt_kern_shared_data import JA_NEIN_BOOLEAN_TOKENS
from .document_types import KNOWN_DOCUMENT_TYPES

REQUIRED_FRONTMATTER_FIELDS = ("Titel", "Fach", "Thema")

MISSING = object()
"""Sentinel für `FrontmatterFieldSpec.default`: "kein Default vorhanden" --
unterscheidbar von einem tatsächlichen Default-Wert `None`."""

TRUTHY_META_BOOLEAN_TOKENS = frozenset(
    {
        "1", "true", "wahr", "ja", "yes", "on",
        "0", "false", "falsch", "nein", "no", "off",
    }
)
"""Exakt das von `_is_truthy_meta_bool` (`blatt_validator_value_helpers.py`,
genutzt von `FM005`) akzeptierte Boolean-Vokabular. **Nicht** identisch mit
`JA_NEIN_BOOLEAN_TOKENS` (`blatt_kern_shared_data.py`, genutzt von `FM006`/
`_meta_bool_ja_nein`: ohne `wahr`/`falsch`, dafür mit `j`/`n`) -- zwei echte,
unterschiedliche Boolean-Parser im Code, absichtlich getrennt geführt statt
künstlich vereinheitlicht."""


@dataclass(frozen=True)
class FrontmatterFieldSpec:
    """Normativer Fakt über ein optionales Frontmatter-Feld -- Validator-Eigentum, keine Prosa.

    `kind` ∈ {"free_text", "scalar_nonempty", "enum", "boolean"}.
    `validated=False` heißt: das Feld existiert (und wird ggf. an anderer
    Stelle im Code funktional gelesen), aber der Validator prüft seinen
    Wert aktuell nicht -- eine ehrliche normative Aussage, kein
    Versäumnis im Katalog. Redaktionelle Beschreibungen/Erklärungen
    gehören bewusst **nicht** hierher, sondern in die
    `PROSE_SECTIONS`-Registry des Doku-Generators
    (`tools/docs/generate_authoring_guides.py`).
    """

    name: str
    kind: str
    allowed_values: frozenset[str] | None
    default: object
    validated: bool

KNOWN_BLOCK_TYPES = {
    "raw",
    "material",
    "info",
    "task",
    "subtask",
    "lines",
    "grid",
    "geometry",
    "dots",
    "space",
    "table",
    "numberline",
    "mc",
    "cloze",
    "matching",
    "wordsearch",
    "solution",
    "columns",
    "nextcol",
    "endcolumns",
    "help",
    "hilfe",
    "qrcode",
    "pagebreak",
    "framebreak",
    "slidechromeoff",
    "sectionmark",
    "vspacer",
}
KNOWN_SHOW_VALUES = {"worksheet", "solution", "both"}
KNOWN_BLOCK_MODE_VALUES = {"worksheet", "solution"}
KNOWN_DOCUMENT_MODES = {"ws", "test", "worksheet", "solution", "presentation"}
KNOWN_PRESENTATION_LAYOUTS = {
    "presentation_16_9",
    "presentation_16_10",
    "presentation_4_3",
}
GRID_MARKER_SHOW_VALUES = {"&", "§", "%"}
KNOWN_GRID_LINE_STYLES = {"solid", "dashed"}
"""Erlaubte Werte für die Block-Option `line=...` bei `:::grid`/`:::geometry`.

Steuert den Linienstil des Rasterhintergrunds selbst (nicht zu verwechseln
mit dem gleichnamigen Objekt-Feld `pairs[].line` in der Geometry-YAML-DSL,
das den Linienstil einzelner Strecken steuert und separat über
`GEOMETRY_ENTRY_ALLOWED_KEYS`/`_validate_geometry_entry_fields` geprüft
wird — beide Ebenen teilen sich nur den Namen, nicht die Validierung.
"""
NUMBERLINE_ANSWER_TYPES = {"numberline"}
MARKER_SHOW_SECTIONS_BY_ANSWER_TYPE = {
    "geometry": ("points", "pairs", "functions"),
    "numberline": ("labels", "answers", "arcs", "jumps", "arrows", "boxes", "blanks"),
}
KNOWN_WORK_VALUES = {
    "single",
    "ea",
    "einzel",
    "einzelarbeit",
    "partner",
    "pa",
    "partnerarbeit",
    "group",
    "ga",
    "gruppe",
    "gruppenarbeit",
}
KNOWN_ACTION_VALUES = {
    "exchange",
    "austauschen",
    "decide",
    "entscheiden",
    "experiment",
    "experimentieren",
    "reflect",
    "reflektieren",
    "read",
    "lesen",
    "calculate",
    "rechnen",
    "match",
    "zuordnen",
    "write",
    "schreiben",
    "draw",
    "zeichnen",
}
KNOWN_HINT_VALUES = {
    "tip",
    "tipp",
    "hint",
    "definition",
    "def",
    "remember",
    "reminder",
    "erinnerung",
    "term",
    "fachwort",
    "expert",
    "expertenaufgabe",
}
ANSWER_BLOCK_TYPES = {
    "lines",
    "grid",
    "geometry",
    "dots",
    "space",
    "table",
    "numberline",
    "mc",
    "cloze",
    "matching",
    "wordsearch",
}
KNOWN_ANSWER_TYPES = ANSWER_BLOCK_TYPES
YAML_ANSWER_TYPES = {
    "geometry",
    "numberline",
    "table",
    "matching",
}

BLOCK_ALLOWED_OPTIONS = {
    "material": {"title", "show", "mode", "align"},
    "info": {"type", "show", "mode", "align"},
    "task": {
        "points",
        "time",
        "work",
        "action",
        "hint",
        "show",
        "mode",
        "title",
        "align",
    },
    "subtask": {"time", "work", "action", "show", "mode", "align"},
    "lines": {
        "show",
        "mode",
        "rows",
        "height",
        "align",
    },
    "grid": {
        "show",
        "mode",
        "rows",
        "cols",
        "scale",
        "line",
        "align",
    },
    "geometry": {
        "show",
        "mode",
        "rows",
        "cols",
        "scale",
        "line",
        "axis",
        "axis_label_x",
        "axis_label_y",
        "origin",
        "step_x",
        "step_y",
        "align",
    },
    "dots": {
        "show",
        "mode",
        "height",
        "align",
    },
    "space": {
        "show",
        "mode",
        "height",
        "align",
    },
    "table": {
        "show",
        "mode",
        "rows",
        "cols",
        "width",
        "widths",
        "alignment",
        "row_height",
        "headers",
        "header_columns",
        "header_cols",
        "row_labels",
    },
    "numberline": {
        "show",
        "mode",
        "height",
        "min",
        "max",
        "minimum",
        "maximum",
        "tick_step",
        "ticks",
        "tick_spacing_mm",
        "tick_spacing_cm",
        "tick_spacing",
        "major_every",
        "max_width_mm",
        "max_width_cm",
        "full_width",
        "positive_sign",
        "signed_positive",
        "align",
    },
    "mc": {
        "show",
        "mode",
        "inline",
        "tf",
        "true_false",
        "correct",
        "options",
        "widths",
        "align",
    },
    "cloze": {
        "show",
        "mode",
        "gap",
        "gap_length",
        "words",
        "words_multi",
        "layout",
        "align",
    },
    "matching": {
        "show",
        "mode",
        "scale",
        "layout",
        "orientation",
        "left",
        "right",
        "top",
        "bottom",
        "matches",
        "links",
        "worksheet_matches",
        "height_mode",
        "align",
        "show_guides",
        "lane_align",
    },
    "wordsearch": {
        "show",
        "mode",
        "min_size",
        "min_rows",
        "min_cols",
        "diagonal",
        "horizontal",
        "vertical",
        "words",
        "align",
    },
    "solution": {"label", "show", "mode", "align"},
    "columns": {"cols", "widths", "ratio", "gap", "align"},
    "nextcol": set(),
    "endcolumns": set(),
    "help": {"title", "level", "show", "mode", "tag"},
    "hilfe": {"title", "level", "show", "mode", "tag"},
    "qrcode": {
        "url",
        "w",
        "h",
        "maxw",
        "width",
        "height",
        "max-width",
        "align",
        "alignment",
        "show",
        "mode",
    },
    "pagebreak": set(),
    "framebreak": set(),
    "slidechromeoff": set(),
    "sectionmark": {"title"},
    "vspacer": {"height"},
}

QRCODE_SIZE_OPTION_KEYS = {"w", "h", "maxw", "width", "height", "max-width"}

OBJECT_ALIGN_VALUE_HINT = "left|right|center|block"

CRITICAL_DIAGNOSTIC_CODES = {
    "AN003",  # Invalid YAML in schema-driven answer blocks.
}

OPTIONAL_FRONTMATTER_FIELDS = (
    FrontmatterFieldSpec("mode", "enum", frozenset(KNOWN_DOCUMENT_MODES), "worksheet", True),
    FrontmatterFieldSpec(
        "presentation_layout", "enum", frozenset(KNOWN_PRESENTATION_LAYOUTS), MISSING, True
    ),
    FrontmatterFieldSpec(
        "presentation_show_mini_header", "boolean", TRUTHY_META_BOOLEAN_TOKENS, True, True
    ),
    FrontmatterFieldSpec(
        "presentation_show_section_footer", "boolean", TRUTHY_META_BOOLEAN_TOKENS, True, True
    ),
    FrontmatterFieldSpec("tag", "scalar_nonempty", None, MISSING, True),
    FrontmatterFieldSpec(
        "show_student_header", "boolean", JA_NEIN_BOOLEAN_TOKENS, False, True
    ),
    FrontmatterFieldSpec(
        "show_document_header", "boolean", JA_NEIN_BOOLEAN_TOKENS, True, True
    ),
    FrontmatterFieldSpec(
        "document_type", "enum", frozenset(KNOWN_DOCUMENT_TYPES), "worksheet", False
    ),
    FrontmatterFieldSpec("lochen", "boolean", JA_NEIN_BOOLEAN_TOKENS, False, False),
    FrontmatterFieldSpec("copyright", "free_text", None, MISSING, False),
    FrontmatterFieldSpec("Stufe", "free_text", None, MISSING, False),
    FrontmatterFieldSpec("worksheet_type", "free_text", None, MISSING, False),
    FrontmatterFieldSpec("font_profile", "free_text", None, MISSING, False),
)
"""Vollständiger normativer Katalog optionaler Frontmatter-Felder.

`show_student_header`/`show_document_header` referenzieren bewusst
`JA_NEIN_BOOLEAN_TOKENS` (nicht `TRUTHY_META_BOOLEAN_TOKENS`), weil sie
über `_meta_bool_ja_nein` gelesen werden (siehe `FM006` in
`blatt_validator_document.py`) -- ein anderes Vokabular als das der
bereits bestehenden `FM005`-Felder. `document_type`/`lochen` sind
funktional genutzt, aber bewusst `validated=False` (siehe
`docs/ANLEITUNG_ARBEITSBLATT_PRAESENTATION.md`, Vier-Zustands-Raster).
`Stufe`/`worksheet_type`/`font_profile` sind `validated=False` **und**
werden aktuell an keiner Stelle aus dem Dokument-Meta gelesen (verifiziert
per Repo-weitem Grep) -- toter, aber weiterhin syntaktisch akzeptierter
Frontmatter-Inhalt."""
