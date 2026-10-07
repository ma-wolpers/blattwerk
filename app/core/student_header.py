"""Schülerkopfzeile (Name / Lerngruppe / Datum) mit Vorbefüllung aus dem Frontmatter.

Die Kopfzeile erscheint nur bei `show_student_header: ja`. `Lerngruppe` und
`Datum` werden aus dem Frontmatter vorbefüllt, wenn dort ein gültiger,
nicht-leerer Wert steht; sonst bleibt die Schreiblinie leer.

Typregeln (bewusst ohne implizites `str()`):

* `Lerngruppe`: nur ein YAML-String wird übernommen. Andere Typen -- z. B.
  `Lerngruppe: 11.6`, das YAML als Zahl liest (und aus `11.10` still `11.1`
  machen würde) -- werden nicht vorbefüllt und als `FM011` gemeldet.
* `Datum`: `date`/`datetime` (YAML-ISO wie `2026-09-25`) → `TT.MM.JJJJ`;
  ein String bleibt unverändert; andere Typen → nicht vorbefüllt + `FM011`.
* `None`, leere Strings und die Template-Platzhalter
  (`document_type_templates.HEADER_PLACEHOLDERS`) gelten als leer, ohne
  Diagnose.
"""

from __future__ import annotations

from datetime import date
from html import escape

from .blatt_kern_shared_meta import _meta_bool_ja_nein
from .document_type_templates import HEADER_PLACEHOLDERS

HEADER_TEXT_KIND = "header_text"
HEADER_DATE_KIND = "header_date"
HEADER_FIELD_KINDS = frozenset({HEADER_TEXT_KIND, HEADER_DATE_KIND})

_FIELD_KINDS = {"Lerngruppe": HEADER_TEXT_KIND, "Datum": HEADER_DATE_KIND}


class InvalidHeaderValue(ValueError):
    """Wert eines Kopf-Feldes hat einen nicht erlaubten YAML-Typ."""


def resolve_header_value(kind: str, raw_value) -> str | None:
    """Liefert den Anzeigetext eines Kopf-Feldes oder ``None`` (leer lassen).

    Wirft `InvalidHeaderValue`, wenn der YAML-Typ für die Feldart nicht
    erlaubt ist; der Renderer behandelt das als leer, der Validator meldet
    `FM011`. Platzhalter und leere Werte liefern ``None`` ohne Fehler.
    """
    if raw_value is None:
        return None
    if kind == HEADER_DATE_KIND and isinstance(raw_value, date):
        return raw_value.strftime("%d.%m.%Y")
    if not isinstance(raw_value, str):
        raise InvalidHeaderValue(type(raw_value).__name__)
    text = raw_value.strip()
    if not text or text in HEADER_PLACEHOLDERS:
        return None
    return text


def header_value_problem(kind: str, raw_value) -> str | None:
    """Beschreibt einen Typfehler eines Kopf-Feldes für `FM011` (sonst ``None``)."""
    try:
        resolve_header_value(kind, raw_value)
    except InvalidHeaderValue as error:
        hint = "Text oder Datum" if kind == HEADER_DATE_KIND else "Text"
        return f"erwartet {hint}, gefunden {error}. Wert in Anführungszeichen setzen, z. B. \"11.6\"."
    return None


def _field_html(label: str, value: str | None) -> str:
    """Ein Feld der Kopfzeile: Beschriftung plus Schreiblinie, ggf. vorbefüllt."""
    if value is None:
        line = "<span class=\"student-line\"></span>"
    else:
        line = f"<span class=\"student-line student-line-filled\">{escape(value)}</span>"
    return f"<div class=\"student-field\"><span class=\"student-label\">{label}</span>{line}</div>"


def _safe_value(meta: dict, name: str) -> str | None:
    """Vorbefüllung für `name`; ungültige Typen bleiben im Dokument leer (Diagnose: FM011)."""
    try:
        return resolve_header_value(_FIELD_KINDS[name], meta.get(name))
    except InvalidHeaderValue:
        return None


def render_student_header(meta: dict | None) -> str:
    """Rendert die Schülerkopfzeile oder ``""``, wenn `show_student_header` aus ist.

    `Name` bleibt immer leer (wird von Hand ausgefüllt); `Lerngruppe` und
    `Datum` werden nach den Typregeln im Moduldocstring vorbefüllt.
    """
    metadata = meta if isinstance(meta, dict) else {}
    if not _meta_bool_ja_nein(metadata.get("show_student_header"), default=False):
        return ""
    fields = [
        _field_html("Name", None),
        _field_html("Lerngruppe", _safe_value(metadata, "Lerngruppe")),
        _field_html("Datum", _safe_value(metadata, "Datum")),
    ]
    return f"<div class=\"student-header\">{''.join(fields)}</div>"
