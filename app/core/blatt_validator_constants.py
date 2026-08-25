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
    "crossword",
    "ordering",
    "checkgrid",
    "mindmap",
    "selfcheck",
    "writebox",
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
KNOWN_ALIGN_VALUES = {
    "left",
    "l",
    "links",
    "linksbundig",
    "linksbuendig",
    "right",
    "r",
    "rechts",
    "rechtsbundig",
    "rechtsbuendig",
    "center",
    "c",
    "centre",
    "middle",
    "mitte",
    "m",
    "zentriert",
    "justify",
    "j",
    "block",
    "blocksatz",
    "b",
}
"""Erlaubte Werte für die Objekt-Ausrichtungsoption `align`/`alignment`
(deutsche und englische Schreibweisen). Normative Quelle für
`_is_valid_object_align` (`blatt_validator_value_helpers.py`) -- lebt hier
statt als Inline-Literal, damit `BLOCK_OPTION_SPECS` (unten) dieselbe
Menge referenzieren kann, ohne sie zu duplizieren. Gilt **nicht** für
`table`/`matching`, die ihre eigene, abweichende `align`-Semantik haben
(siehe `BLOCK_OPTION_SPECS`-Eintrag dort)."""

NUMBERLINE_ANSWER_TYPES = {"numberline"}
MARKER_SHOW_SECTIONS_BY_ANSWER_TYPE = {
    "geometry": ("points", "pairs", "functions"),
    "numberline": ("labels", "answers", "arcs", "jumps", "arrows", "boxes", "blanks"),
}
KNOWN_WORK_VALUES = {
    "single",
    "sgl",
    "ea",
    "einzel",
    "partner",
    "pa",
    "group",
    "grp",
    "ga",
    "gruppe",
}
KNOWN_ACTION_VALUES = {
    "exchange",
    "exc",
    "austauschen",
    "aus",
    "decide",
    "dec",
    "entscheiden",
    "ent",
    "experiment",
    "experimentieren",
    "exp",
    "reflect",
    "reflektieren",
    "ref",
    "read",
    "rd",
    "lesen",
    "les",
    "calculate",
    "calc",
    "rechnen",
    "rech",
    "match",
    "mat",
    "zuordnen",
    "zuo",
    "write",
    "wrt",
    "schreiben",
    "schr",
    "draw",
    "drw",
    "zeichnen",
    "zei",
}
KNOWN_HINT_VALUES = {
    "tip",
    "tipp",
    "tp",
    "hint",
    "definition",
    "def",
    "remember",
    "rem",
    "reminder",
    "erinnerung",
    "eri",
    "term",
    "tm",
    "fachwort",
    "fw",
    "expert",
    "experte",
    "exp",
}
"""`gruppenarbeit`/`einzelarbeit`/`partnerarbeit`/`expertenaufgabe` sind
bewusst entfernt (nicht nur aus der Completion): Data-noise-Langformen ohne
kürzeres eigenständiges Konzept, ersetzt durch `gruppe`/`einzel`/`partner`/
`experte`. Alte Werte lösen künftig `OP002` aus -- echte Syntaxänderung,
siehe `OPTION_VALUE_STYLE_CATALOGS`-Migrationsnotiz unten."""

_WORK_VALUE_STYLES = (
    {"english": "single", "abbreviation_english": "sgl", "german": "einzel", "abbreviation_german": "ea"},
    {"english": "partner", "abbreviation_english": "pa", "german": "partner", "abbreviation_german": "pa"},
    {"english": "group", "abbreviation_english": "grp", "german": "gruppe", "abbreviation_german": "ga"},
)
_ACTION_VALUE_STYLES = (
    {"english": "exchange", "abbreviation_english": "exc", "german": "austauschen", "abbreviation_german": "aus"},
    {"english": "decide", "abbreviation_english": "dec", "german": "entscheiden", "abbreviation_german": "ent"},
    {"english": "experiment", "abbreviation_english": "exp", "german": "experimentieren", "abbreviation_german": "exp"},
    {"english": "reflect", "abbreviation_english": "ref", "german": "reflektieren", "abbreviation_german": "ref"},
    {"english": "read", "abbreviation_english": "rd", "german": "lesen", "abbreviation_german": "les"},
    {"english": "calculate", "abbreviation_english": "calc", "german": "rechnen", "abbreviation_german": "rech"},
    {"english": "match", "abbreviation_english": "mat", "german": "zuordnen", "abbreviation_german": "zuo"},
    {"english": "write", "abbreviation_english": "wrt", "german": "schreiben", "abbreviation_german": "schr"},
    {"english": "draw", "abbreviation_english": "drw", "german": "zeichnen", "abbreviation_german": "zei"},
)
_ALIGN_VALUE_STYLES = (
    {"english": "left", "abbreviation_english": "l", "german": "links", "abbreviation_german": "l"},
    {"english": "right", "abbreviation_english": "r", "german": "rechts", "abbreviation_german": "r"},
    {"english": "center", "abbreviation_english": "c", "german": "mitte", "abbreviation_german": "m"},
    {"english": "justify", "abbreviation_english": "j", "german": "blocksatz", "abbreviation_german": "b"},
)
_HINT_VALUE_STYLES = (
    {"english": "tip", "german": "tipp", "abbreviation_german": "tp"},
    {"english": "definition", "abbreviation_english": "def", "german": "definition", "abbreviation_german": "def"},
    {"english": "remember", "abbreviation_english": "rem", "german": "erinnerung", "abbreviation_german": "eri"},
    {"english": "term", "abbreviation_english": "tm", "german": "fachwort", "abbreviation_german": "fw"},
    {"english": "expert", "abbreviation_english": "exp", "german": "experte", "abbreviation_german": "exp"},
)

OPTION_VALUE_STYLE_CATALOGS = (
    (KNOWN_WORK_VALUES, _WORK_VALUE_STYLES),
    (KNOWN_ACTION_VALUES, _ACTION_VALUE_STYLES),
    (KNOWN_ALIGN_VALUES, _ALIGN_VALUE_STYLES),
    (KNOWN_HINT_VALUES, _HINT_VALUE_STYLES),
)
"""Kuratierter Katalog: pro Konzept je ein deutscher und englischer Wert samt
sprachspezifischer Abkürzung (`abbreviation_english`/`abbreviation_german`).
Handverlesene Daten, **keine automatisch aus der Wortlänge abgeleitete
Abkürzung** -- der Resolver (`completion_catalogs.py`) liest diese Tabellen
nur aus, er berechnet nichts selbst. Zuordnung zur jeweiligen `KNOWN_*_VALUES`-
Menge erfolgt über Mengengleichheit (nicht über den Optionsnamen-String),
damit z. B. `table`s eigene, abweichende `alignment`-Menge unberührt bleibt.
Jeder hier referenzierte Wert (Sprachform wie Abkürzung) muss in der
zugehörigen `KNOWN_*_VALUES`-Menge enthalten sein -- per Guardrail-Test
abgesichert (`tests/test_blatt_validator_constants.py`)."""

BLOCK_OPTION_KEY_ALIASES = {
    "table": frozenset({"header_cols"}),
    "numberline": frozenset({"minimum", "maximum", "signed_positive"}),
    "mc": frozenset({"true_false"}),
    "matching": frozenset({"orientation", "links"}),
    "columns": frozenset({"ratio"}),
    "qrcode": frozenset({"width", "height", "max-width"}),
}
"""Je Blocktyp ausschließlich die aus der Editor-Completion **auszublendenden
Alias-Schlüssel** (nicht die kanonische Form -- die ergibt sich implizit
daraus, dass sie in `BLOCK_ALLOWED_OPTIONS[block_type]` bleibt und hier
nicht aufgeführt ist). Rein Completion-seitig: Alias-Schlüssel bleiben in
`BLOCK_OPTION_SPECS`/`BLOCK_ALLOWED_OPTIONS` vollständig gültig und werden
vom Validator weiterhin akzeptiert -- im Gegensatz zu den oben entfernten
`work`/`hint`-Werten ist dies **keine** Syntaxänderung. Absichtlich
blockbezogen (nicht global), da z. B. `qrcode`s `width` ein Alias von `w`
ist, `table`s eigenes `width` aber primär/kanonisch. `tick_spacing_mm`/
`tick_spacing_cm`/`tick_spacing`, `max_width_mm`/`max_width_cm` (numberline)
sowie `matches`/`worksheet_matches` (matching) sind bewusst NICHT hier
aufgeführt: unterschiedliche Einheiten bzw. Konzepte, keine austauschbaren
Namen für denselben Wert."""

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
    "crossword",
    "ordering",
    "checkgrid",
}
KNOWN_ANSWER_TYPES = ANSWER_BLOCK_TYPES
YAML_ANSWER_TYPES = {
    "geometry",
    "numberline",
    "table",
    "matching",
    "crossword",
    "checkgrid",
}

@dataclass(frozen=True)
class BlockOptionSpec:
    """Normativer Fakt über eine `:::blocktyp key=value`-Option -- Validator-Eigentum, keine Prosa.

    **`kind` und `validated` sind unabhängige Dimensionen, nicht gekoppelt:**
    `kind` beschreibt, welche Art von Wert der Code an dieser Stelle
    tatsächlich erwartet/verarbeitet -- auch wenn das nur im *Renderer*
    steckt (z. B. `rows` wird über `_safe_int(...)` gelesen -> `kind=
    "integer"`, unabhängig davon, ob der Validator das prüft). `validated`
    sagt ausschließlich, ob der **Validator** dieses Format/diese Werte
    aktuell durchsetzt (d. h. ein falscher Wert eine Diagnose auslöst).
    `BlockOptionSpec(name="height", kind="css_length", validated=False)`
    heißt also präzise: *"wird als CSS-Länge interpretiert, aber der
    Validator prüft das Format nicht"* -- keine automatische normative
    Verschärfung. `kind` ∈ {"enum", "boolean", "integer", "number",
    "css_length", "url", "text"}; `"text"` ist der ehrliche Rückfall, wenn
    der Code den Wert nur als Rohstring durchreicht bzw. keine spezifischere
    Klassifizierung im Code belegt ist.

    **`default`-Sentinel:** `MISSING` = kein dokumentierbarer expliziter
    Default im Code gefunden; ein konkreter Wert = der Code verwendet
    exakt diesen Default; `None` wird nur gesetzt, wenn im Code
    tatsächlich semantisch "nichts" der Default ist (z. B. `action`/`hint`
    bei `task`: ohne Angabe wird schlicht kein Symbol gerendert). Ein
    dynamischer Theme-/Renderer-Fallback (kein fester Wert, z. B. Geometry-
    `color`/`thickness` ohne gültigen Wert) wird **nicht** hier codiert,
    sondern bleibt `MISSING` und wird in der redaktionellen Prosa als
    dynamisches Verhalten beschrieben.
    """

    name: str
    kind: str
    allowed_values: frozenset[str] | None
    validated: bool
    default: object


# -- Wiederverwendete Optionskonzepte (identische Bedeutung über mehrere Blöcke) --
# Instanzen werden in mehreren Block-Tupeln unten referenziert statt dupliziert.

_OPT_SHOW = BlockOptionSpec("show", "enum", frozenset(KNOWN_SHOW_VALUES), True, "both")
_OPT_MODE = BlockOptionSpec("mode", "enum", frozenset(KNOWN_BLOCK_MODE_VALUES), True, MISSING)
_OPT_ALIGN = BlockOptionSpec("align", "enum", frozenset(KNOWN_ALIGN_VALUES), True, MISSING)
_OPT_ALIGNMENT_GENERIC = BlockOptionSpec(
    "alignment", "enum", frozenset(KNOWN_ALIGN_VALUES), True, MISSING
)
_OPT_WORK = BlockOptionSpec("work", "enum", frozenset(KNOWN_WORK_VALUES), True, "single")
_OPT_ACTION = BlockOptionSpec("action", "enum", frozenset(KNOWN_ACTION_VALUES), True, None)
_OPT_HINT = BlockOptionSpec("hint", "enum", frozenset(KNOWN_HINT_VALUES), True, None)
_OPT_LINE = BlockOptionSpec("line", "enum", frozenset(KNOWN_GRID_LINE_STYLES), True, "solid")
_OPT_TITLE = BlockOptionSpec("title", "text", None, False, MISSING)
_OPT_WIDTHS = BlockOptionSpec("widths", "text", None, False, MISSING)
_OPT_SCALE = BlockOptionSpec("scale", "css_length", None, False, "0.5cm")

QRCODE_SIZE_OPTION_KEYS = {"w", "h", "maxw", "width", "height", "max-width"}
_OPT_QRCODE_SIZE_HINT = "CSS-Größe wie `3cm`, `120px`, `60%` oder `auto`"

BLOCK_OPTION_SPECS: dict[str, tuple[BlockOptionSpec, ...]] = {
    "material": (_OPT_TITLE, _OPT_SHOW, _OPT_MODE, _OPT_ALIGN),
    "info": (
        BlockOptionSpec("type", "enum", frozenset({"default", "warning", "note"}), True, "default"),
        _OPT_SHOW,
        _OPT_MODE,
        _OPT_ALIGN,
    ),
    "task": (
        BlockOptionSpec("points", "text", None, False, MISSING),
        BlockOptionSpec("time", "text", None, False, MISSING),
        _OPT_WORK,
        _OPT_ACTION,
        _OPT_HINT,
        _OPT_SHOW,
        _OPT_MODE,
        _OPT_TITLE,
        _OPT_ALIGN,
    ),
    "subtask": (
        BlockOptionSpec("time", "text", None, False, MISSING),
        _OPT_WORK,
        _OPT_ACTION,
        _OPT_SHOW,
        _OPT_MODE,
        _OPT_ALIGN,
    ),
    "lines": (
        _OPT_SHOW,
        _OPT_MODE,
        BlockOptionSpec("rows", "integer", None, False, 3),
        BlockOptionSpec("height", "css_length", None, False, MISSING),
        _OPT_ALIGN,
    ),
    "grid": (
        _OPT_SHOW,
        _OPT_MODE,
        BlockOptionSpec("rows", "integer", None, False, 5),
        BlockOptionSpec(
            "cols", "integer", None, False, MISSING
        ),  # ohne Angabe automatisch aus Druckbreite/scale berechnet
        _OPT_SCALE,
        _OPT_LINE,
        _OPT_ALIGN,
    ),
    "geometry": (
        _OPT_SHOW,
        _OPT_MODE,
        BlockOptionSpec("rows", "integer", None, False, 5),
        BlockOptionSpec("cols", "integer", None, False, 20),
        _OPT_SCALE,
        _OPT_LINE,
        BlockOptionSpec("axis", "boolean", None, False, False),
        BlockOptionSpec("axis_label_x", "text", None, False, "x"),
        BlockOptionSpec("axis_label_y", "text", None, False, "y"),
        BlockOptionSpec("origin", "text", None, False, MISSING),  # Format "col,row"
        BlockOptionSpec("step_x", "number", None, False, 1.0),
        BlockOptionSpec("step_y", "number", None, False, 1.0),
        _OPT_ALIGN,
    ),
    "dots": (
        _OPT_SHOW,
        _OPT_MODE,
        BlockOptionSpec("height", "css_length", None, False, "4cm"),
        _OPT_ALIGN,
    ),
    "space": (
        _OPT_SHOW,
        _OPT_MODE,
        BlockOptionSpec("height", "css_length", None, False, "3cm"),
        _OPT_ALIGN,
    ),
    "table": (
        _OPT_SHOW,
        _OPT_MODE,
        BlockOptionSpec("rows", "integer", None, False, MISSING),
        BlockOptionSpec("cols", "integer", None, False, MISSING),
        BlockOptionSpec("width", "css_length", None, False, MISSING),
        _OPT_WIDTHS,
        BlockOptionSpec(
            "alignment",
            "enum",
            frozenset({"left", "right", "center", "justify", "l", "r", "c", "j"}),
            False,
            MISSING,
        ),  # eigene Semantik (auch pro Spalte, Kurzformen l/r/c/j) -- NICHT über _is_valid_object_align geprüft
        BlockOptionSpec("row_height", "css_length", None, False, MISSING),
        BlockOptionSpec("headers", "text", None, False, MISSING),
        BlockOptionSpec("header_columns", "integer", None, False, MISSING),
        BlockOptionSpec("header_cols", "integer", None, False, MISSING),  # Alias von header_columns
        BlockOptionSpec("row_labels", "text", None, False, MISSING),
    ),
    "numberline": (
        _OPT_SHOW,
        _OPT_MODE,
        BlockOptionSpec("height", "css_length", None, False, "2.7cm"),
        BlockOptionSpec("min", "number", None, False, MISSING),
        BlockOptionSpec("max", "number", None, False, MISSING),
        BlockOptionSpec("minimum", "number", None, False, MISSING),  # Alias von min
        BlockOptionSpec("maximum", "number", None, False, MISSING),  # Alias von max
        BlockOptionSpec("tick_step", "number", None, False, MISSING),
        BlockOptionSpec("ticks", "text", None, False, MISSING),
        BlockOptionSpec("tick_spacing_mm", "number", None, False, MISSING),
        BlockOptionSpec("tick_spacing_cm", "number", None, False, MISSING),
        BlockOptionSpec("tick_spacing", "number", None, False, MISSING),
        BlockOptionSpec("major_every", "integer", None, False, 0),
        BlockOptionSpec("max_width_mm", "number", None, False, MISSING),
        BlockOptionSpec("max_width_cm", "number", None, False, MISSING),
        BlockOptionSpec("full_width", "boolean", None, False, MISSING),
        BlockOptionSpec("positive_sign", "boolean", None, False, MISSING),
        BlockOptionSpec("signed_positive", "boolean", None, False, MISSING),  # Alias von positive_sign
        _OPT_ALIGN,
    ),
    "mc": (
        _OPT_SHOW,
        _OPT_MODE,
        BlockOptionSpec("inline", "boolean", None, False, False),
        BlockOptionSpec("tf", "boolean", None, False, False),
        BlockOptionSpec("true_false", "boolean", None, False, False),  # Alias von tf
        BlockOptionSpec("correct", "text", None, False, MISSING),
        BlockOptionSpec("options", "text", None, False, MISSING),
        _OPT_WIDTHS,
        _OPT_ALIGN,
    ),
    "cloze": (
        _OPT_SHOW,
        _OPT_MODE,
        BlockOptionSpec(
            "gap", "enum", frozenset({"fixed", "equal", "same", "uniform", "gleich", "approx"}), False, "approx"
        ),
        BlockOptionSpec("gap_length", "integer", None, False, 10),
        BlockOptionSpec("words", "text", None, False, MISSING),  # Wortbank-Position, nicht die Lückenwörter selbst
        BlockOptionSpec("words_multi", "boolean", None, False, True),
        BlockOptionSpec("layout", "text", None, False, MISSING),
        _OPT_ALIGN,
    ),
    "matching": (
        _OPT_SHOW,
        _OPT_MODE,
        _OPT_SCALE,
        BlockOptionSpec("layout", "text", None, False, MISSING),
        BlockOptionSpec("orientation", "text", None, False, MISSING),  # Alias von layout
        BlockOptionSpec("left", "text", None, False, MISSING),
        BlockOptionSpec("right", "text", None, False, MISSING),
        BlockOptionSpec("top", "text", None, False, MISSING),
        BlockOptionSpec("bottom", "text", None, False, MISSING),
        BlockOptionSpec("matches", "text", None, False, MISSING),
        BlockOptionSpec("links", "text", None, False, MISSING),  # Alias von left
        BlockOptionSpec("worksheet_matches", "text", None, False, MISSING),
        BlockOptionSpec("height_mode", "enum", frozenset({"content", "uniform"}), False, "content"),
        BlockOptionSpec(
            "align", "enum", frozenset({"center"}), False, "center"
        ),  # eigene, engere Semantik -- NICHT über _is_valid_object_align geprüft
        BlockOptionSpec("show_guides", "boolean", None, False, False),
        BlockOptionSpec("lane_align", "enum", frozenset({"start", "center", "end"}), False, "center"),
    ),
    "wordsearch": (
        _OPT_SHOW,
        _OPT_MODE,
        BlockOptionSpec("min_size", "integer", None, False, MISSING),
        BlockOptionSpec("min_rows", "integer", None, False, MISSING),
        BlockOptionSpec("min_cols", "integer", None, False, MISSING),
        BlockOptionSpec("diagonal", "boolean", None, False, False),
        BlockOptionSpec("horizontal", "boolean", None, False, False),  # akzeptiert auch Richtungslisten
        BlockOptionSpec("vertical", "boolean", None, False, False),  # akzeptiert auch Richtungslisten
        BlockOptionSpec("words", "text", None, False, MISSING),
        BlockOptionSpec("position", "enum", frozenset({"left", "right", "above", "below", "auto"}), True, "below"),
        _OPT_ALIGN,
    ),
    "crossword": (
        _OPT_SHOW,
        _OPT_MODE,
        BlockOptionSpec("maxw", "integer", None, False, MISSING),  # Default aus Printable-Width, siehe crossword_placement.py
        BlockOptionSpec("maxh", "integer", None, False, MISSING),  # Default aus Printable-Height, siehe crossword_placement.py
        BlockOptionSpec("scale", "css_length", None, False, "0.72cm"),
        BlockOptionSpec("prefill", "integer", None, False, 0),
        BlockOptionSpec("position", "enum", frozenset({"left", "right", "above", "below", "auto"}), True, "auto"),
        BlockOptionSpec("code", "text", None, False, MISSING),
        BlockOptionSpec("code_row", "boolean", None, False, False),
        _OPT_ALIGN,
    ),
    "ordering": (
        _OPT_SHOW,
        _OPT_MODE,
        BlockOptionSpec("numbering", "enum", frozenset({"numeric", "letters"}), True, "numeric"),
        _OPT_ALIGN,
    ),
    "checkgrid": (
        _OPT_SHOW,
        _OPT_MODE,
        _OPT_ALIGN,
    ),
    "mindmap": (
        _OPT_SHOW,
        _OPT_MODE,
        BlockOptionSpec("branches", "integer", None, False, 6),
        BlockOptionSpec("shape", "enum", frozenset({"oval", "rect", "cloud"}), False, "oval"),
        BlockOptionSpec("subbranches", "integer", None, False, 0),
        _OPT_ALIGN,
    ),
    "selfcheck": (
        _OPT_SHOW,
        _OPT_MODE,
        BlockOptionSpec("scale", "enum", frozenset({"smiley", "ampel", "sterne", "zahlen"}), False, "smiley"),
        BlockOptionSpec("steps", "integer", None, False, 3),
        _OPT_ALIGN,
    ),
    "writebox": (
        _OPT_SHOW,
        _OPT_MODE,
        BlockOptionSpec("style", "enum", frozenset({"bubble", "cloud", "frame", "letter"}), False, "frame"),
        BlockOptionSpec("lines", "integer", None, False, 5),
        _OPT_ALIGN,
    ),
    "solution": (
        BlockOptionSpec("label", "boolean", None, False, True),
        _OPT_SHOW,
        _OPT_MODE,
        _OPT_ALIGN,
    ),
    "columns": (
        BlockOptionSpec("cols", "integer", None, False, 2),
        _OPT_WIDTHS,
        BlockOptionSpec("ratio", "text", None, False, MISSING),  # Alias von widths
        BlockOptionSpec("gap", "css_length", None, False, MISSING),
        _OPT_ALIGN,
    ),
    "nextcol": (),
    "endcolumns": (),
    "help": (
        _OPT_TITLE,
        BlockOptionSpec("level", "integer", None, False, MISSING),
        _OPT_SHOW,
        _OPT_MODE,
        BlockOptionSpec("tag", "text", None, False, MISSING),
    ),
    "hilfe": (
        _OPT_TITLE,
        BlockOptionSpec("level", "integer", None, False, MISSING),
        _OPT_SHOW,
        _OPT_MODE,
        BlockOptionSpec("tag", "text", None, False, MISSING),
    ),
    "qrcode": (
        BlockOptionSpec("url", "url", None, True, MISSING),
        BlockOptionSpec("w", "css_length", None, True, MISSING),
        BlockOptionSpec("h", "css_length", None, True, MISSING),
        BlockOptionSpec("maxw", "css_length", None, True, MISSING),
        BlockOptionSpec("width", "css_length", None, True, MISSING),  # Alias von w
        BlockOptionSpec("height", "css_length", None, True, MISSING),  # Alias von h
        BlockOptionSpec("max-width", "css_length", None, True, MISSING),  # Alias von maxw
        _OPT_ALIGN,
        _OPT_ALIGNMENT_GENERIC,
        _OPT_SHOW,
        _OPT_MODE,
    ),
    "pagebreak": (),
    "framebreak": (),
    "slidechromeoff": (),
    "sectionmark": (_OPT_TITLE,),
    "vspacer": (
        BlockOptionSpec("height", "css_length", None, False, MISSING),
    ),  # als `:::vspacer height=...`-Blockoption unvalidiert; nur die `-=<länge>`-Kurzform (Control-Marker) wird per `BL006` geprüft
}
"""Vollständiger normativer Optionskatalog je Blocktyp (alle `KNOWN_BLOCK_TYPES`
außer `"raw"`, inklusive optionsloser Blöcke als leere Tupel). `kind`/
`validated`/`default` sind für die validierten Optionen (`show`, `mode`,
`align` außer bei `table`/`matching`, `work`, `action`, `hint`, `line`,
`type` bei `info`, `qrcode`s `url`/Größenoptionen) direkt am Validierungscode verifiziert;
für alle anderen Optionen an der tatsächlichen Renderer-Verarbeitung
(`_safe_int`-Aufrufe -> `"integer"`, CSS-Längen-Parsing -> `"css_length"`,
`_option_is_enabled`-Aufrufe -> `"boolean"`) oder, wo auch das nicht
eindeutig belegt ist, als ehrlicher `"text"`-Rückfall."""

BLOCK_ALLOWED_OPTIONS = {
    block: frozenset(spec.name for spec in specs) for block, specs in BLOCK_OPTION_SPECS.items()
}
"""Abgeleitet aus `BLOCK_OPTION_SPECS` (s. o.) -- keine zweite, separat
gepflegte Quelle mehr. Bestehende Konsumenten (`blatt_validator_block_options.py`,
`completion_catalogs.py`, `markdown_conventions.py`) brauchen nur die
Namensmenge und bleiben unverändert lauffähig."""

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
