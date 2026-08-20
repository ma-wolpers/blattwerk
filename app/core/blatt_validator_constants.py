"""Bekannte Blocktypen, erlaubte Optionen und Wertemengen für den Blattwerk-Validator.

Reine Datendatei (Sets/Dicts ohne Logik) — vom 300-Zeilen-Limit ausgenommen.
`BLOCK_ALLOWED_OPTIONS` ist die normative Quelle für "welche `key=value`-
Optionen darf ein `:::blocktyp ...`-Header haben"; analog zur
Geometry-Objekt-Ebene (`GEOMETRY_ENTRY_ALLOWED_KEYS` in
`answer_grid_entries.py`) lebt dieses Wissen nur hier, nicht zusätzlich
verteilt über Validierungscode.
"""

from __future__ import annotations

REQUIRED_FRONTMATTER_FIELDS = ("Titel", "Fach", "Thema")

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
