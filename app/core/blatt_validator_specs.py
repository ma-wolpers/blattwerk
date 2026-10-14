"""Datentypen des normativen Validator-Katalogs: Frontmatter-Felder und Block-Optionen.

Die Kataloge selbst (reine Daten) stehen in `blatt_validator_constants.py`, das diese
Namen re-exportiert.
"""

from __future__ import annotations

from dataclasses import dataclass


MISSING = object()
"""Sentinel für `FrontmatterFieldSpec.default`: "kein Default vorhanden" --
unterscheidbar von einem tatsächlichen Default-Wert `None`."""


@dataclass(frozen=True)
class FrontmatterFieldSpec:
    """Normativer Fakt über ein optionales Frontmatter-Feld -- Validator-Eigentum, keine Prosa.

    `kind` ∈ {"free_text", "scalar_nonempty", "enum", "boolean", "header_text",
    "header_date"}; die beiden `header_*`-Arten sind die vorbefüllbaren Felder
    der Schülerkopfzeile (Typregeln in `student_header.py`, Diagnose `FM011`).
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
