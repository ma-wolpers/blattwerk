"""Methodenkopf (Signatur) in GO-Notation: Parser und HTML-Formatter.

Die Ergänzenden Hinweise zur GO Informatik (Niedersachsen, Neufassung 2025,
S. 5) legen die Form von Operationssignaturen fest::

    Bezeichnung(Parameterbezeichnung: Parametertyp, ...): Rückgabetyp

Beispiele daraus, die dieses Modul alle akzeptiert:

- ``istGerade(x: Ganzzahl): Wahrheitswert``
- ``minimum(a, b: Fließkommazahl): Fließkommazahl`` -- Parameter ohne
  eigenen Typ gehören zur nächsten getypten Gruppe.
- ``sortiere(a: dynamische Reihung vom Inhaltstyp Zeichenkette)`` -- ohne
  Rückgabetyp.
- ``erzeugePixel(): dynamische Reihung vom Inhaltstyp Pixel`` -- ohne
  Parameter.

Bewusst ein reines Modul ohne Blattwerk-Abhängigkeiten: `:::struktogramm`
nutzt es für `signature=`, ein späterer Klassendiagramm-Block (GO S. 7, dort
gleiche Operationsnotation) kann es unverändert wiederverwenden.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape

IDENTIFIER_PATTERN = r"[A-Za-zÄÖÜäöüß_][A-Za-z0-9ÄÖÜäöüß_]*"
"""Bezeichner für Operations- und Parameternamen (Umlaute erlaubt, da die GO
deutschsprachige Bezeichner wie `anzahlRot` oder `istEnthalten` nutzt)."""

_IDENTIFIER_RE = re.compile(rf"^{IDENTIFIER_PATTERN}$")
_SIGNATURE_RE = re.compile(r"^(?P<name>[^()]*)\((?P<params>[^()]*)\)(?P<rest>.*)$", re.DOTALL)
_FORBIDDEN_TYPE_CHARS = frozenset(":,()")

GO_FORM_HINT = "GO-Form: `Bezeichnung(Parameter: Typ, ...): Rückgabetyp`"
"""Gemeinsamer Hinweistext für alle Signatur-Fehlermeldungen."""


@dataclass(frozen=True)
class ParameterGroup:
    """Eine oder mehrere Parameterbezeichnungen mit gemeinsamem Typ.

    `minimum(a, b: Fließkommazahl)` ergibt *eine* Gruppe mit
    `names=("a", "b")`; die Gruppierung bleibt erhalten, damit der Formatter
    die Kurzschreibweise der GO unverändert wiedergibt.
    """

    names: tuple[str, ...]
    type_name: str


@dataclass(frozen=True)
class Signature:
    """Geparster Methodenkopf; `return_type` ist `None` ohne Rückgabewert."""

    name: str
    groups: tuple[ParameterGroup, ...]
    return_type: str | None

    @property
    def parameter_names(self) -> tuple[str, ...]:
        """Alle Parameterbezeichnungen in Schreibreihenfolge (Gruppen aufgelöst)."""
        return tuple(name for group in self.groups for name in group.names)


class SignatureError(ValueError):
    """Signatur verletzt die GO-Form; `code` ist der Validator-Diagnosecode.

    Codes: `SG010` Struktur/Klammern, `SG011` ungültiger oder leerer
    Bezeichner, `SG012` Parameter ohne Typ, `SG013` leerer oder ungültiger
    (Rückgabe-)Typ.
    """

    def __init__(self, code: str, message: str):
        """Speichert Code und deutschsprachige Meldung (inkl. GO-Formhinweis)."""
        super().__init__(f"{message} {GO_FORM_HINT}.")
        self.code = code


def _check_identifier(name: str, role: str) -> str:
    """Prüft einen Bezeichner; `role` erscheint in der Fehlermeldung."""
    if not name:
        raise SignatureError("SG011", f"Signatur: {role} fehlt.")
    if not _IDENTIFIER_RE.match(name):
        raise SignatureError("SG011", f"Signatur: `{name}` ist kein gültiger Bezeichner ({role}).")
    return name


def _check_type(type_name: str, role: str) -> str:
    """Prüft einen (Rückgabe-)Typ: nicht leer, ohne `:`, `,`, `(`, `)`."""
    if not type_name:
        raise SignatureError("SG013", f"Signatur: {role} ist leer.")
    if any(char in _FORBIDDEN_TYPE_CHARS for char in type_name):
        raise SignatureError(
            "SG013", f"Signatur: {role} `{type_name}` darf weder `:` noch `,` noch Klammern enthalten."
        )
    return type_name


def _parse_groups(params_text: str) -> tuple[ParameterGroup, ...]:
    """Zerlegt den Klammerinhalt in Parametergruppen.

    Namen ohne `: Typ` werden gesammelt und der nächsten getypten Angabe
    zugeschlagen (`a, b: Fließkommazahl`). Bleiben am Ende Namen ohne Typ
    übrig, ist das `SG012`.
    """
    if not params_text.strip():
        return ()
    groups: list[ParameterGroup] = []
    pending: list[str] = []
    for item in params_text.split(","):
        name_part, has_type, type_part = item.partition(":")
        name = _check_identifier(name_part.strip(), "Parameterbezeichnung")
        pending.append(name)
        if has_type:
            type_name = _check_type(type_part.strip(), f"Typ von `{name}`")
            groups.append(ParameterGroup(tuple(pending), type_name))
            pending = []
    if pending:
        raise SignatureError("SG012", f"Signatur: Parameter `{', '.join(pending)}` ohne Typ.")
    return tuple(groups)


def parse_signature(text: str) -> Signature:
    """Parst eine Signatur in GO-Notation oder wirft `SignatureError`.

    Leerraum wird normalisiert (`a,b:Typ` ist gültig und wird vom Formatter
    als `a, b: Typ` ausgegeben); inhaltlich muss die Signatur aber exakt der
    GO-Grammatik folgen: genau ein Klammerpaar, danach nichts oder
    `: Rückgabetyp`.

    Example:
        >>> parse_signature("minimum(a, b: Fließkommazahl): Fließkommazahl").parameter_names
        ('a', 'b')
    """
    raw = " ".join(str(text or "").split())
    match = _SIGNATURE_RE.match(raw)
    if not match:
        raise SignatureError("SG010", "Signatur braucht genau ein Klammerpaar nach der Bezeichnung.")
    name = _check_identifier(match.group("name").strip(), "Bezeichnung der Operation")
    groups = _parse_groups(match.group("params"))
    rest = match.group("rest").strip()
    if not rest:
        return Signature(name, groups, None)
    if not rest.startswith(":"):
        raise SignatureError("SG010", f"Signatur: nach `)` darf nur `: Rückgabetyp` folgen, nicht `{rest}`.")
    return_type = _check_type(rest[1:].strip(), "Rückgabetyp")
    return Signature(name, groups, return_type)


def _group_text(group: ParameterGroup) -> str:
    """`a, b: Typ` -- normalisierte Schreibweise einer Gruppe."""
    return f"{', '.join(group.names)}: {group.type_name}"


def format_signature_html(signature: Signature, css_prefix: str = "stg-sig") -> str:
    """Formatiert die Signatur als HTML mit kontrollierten Umbruchstellen.

    Jedes Stück ist ein `inline-block` (CSS-Klasse `{css_prefix}-part`); nur
    *zwischen* den Stücken darf der Browser umbrechen, also an
    Parametergrenzen und nach `):` vor dem Rückgabetyp (wie GO Beispiel 2).
    Die öffnende Klammer hängt am Namen und die schließende am letzten
    Parameter, damit nie eine Klammer allein in eine Zeile rutscht. Ist ein
    einzelnes Stück breiter als die Zeile, bricht es innen normal um.
    """
    closing = "):" if signature.return_type else ")"
    pieces: list[str] = []
    if not signature.groups:
        pieces.append(f"{signature.name}(" + closing)
    for position, group in enumerate(signature.groups):
        text = _group_text(group)
        if position == 0:
            text = f"{signature.name}({text}"
        text += closing if position == len(signature.groups) - 1 else ","
        pieces.append(text)
    if signature.return_type:
        pieces.append(signature.return_type)
    parts = " ".join(f"<span class='{css_prefix}-part'>{escape(piece)}</span>" for piece in pieces)
    return f"<div class='{css_prefix}'>{parts}</div>"


def format_signature_text(signature: Signature) -> str:
    """Normalisierte Einzeilen-Textform (für Tests und Diagnosemeldungen)."""
    params = ", ".join(_group_text(group) for group in signature.groups)
    suffix = f": {signature.return_type}" if signature.return_type else ""
    return f"{signature.name}({params}){suffix}"
