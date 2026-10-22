"""Gemeinsamer Punktkern (Invariante I4): einzige Interpretation von `points=`.

Validator, Klausuranalyse, Bewertungstabelle, Erwartungshorizont und Editor
lesen Punktangaben ausschließlich hier. Der Renderer zeigt Punktangaben über
`points_label` an: numerische Werte normalisiert mit deutschem Komma
(`0.5` → `0,5`), nicht-numerische Angaben weiterhin als Originaltext.

Effektive Punkte einer Aufgabeneinheit (task + folgende subtasks):

==============================================  ======================  ==========
Fall                                            effektiv                Diagnose
==============================================  ======================  ==========
keine bepunkteten Subtasks                      `task.points`/missing   --
alle Subtasks bepunktet, `task.points` fehlt    Summe                   --
alle bepunktet, `task.points` = Summe           Summe                   --
alle bepunktet, `task.points` ≠ Summe           None (inconsistent)     PK001
nur ein Teil der Subtasks bepunktet             None (inconsistent)     PK004
nicht-numerische Angabe                         None (non_numeric)      PK003
==============================================  ======================  ==========

Kein Konsument löst `inconsistent` durch die Wahl eines Werts auf.

**Bonuspunkte** (`bonus=true` an Teilaufgabe oder Aufgabe): Sie zählen nicht
zur regulären Punktzahl (= 100 %), können aber zusätzlich erreicht werden.
Bonus-Teilaufgaben bleiben in `subtasks` (eigene Lösungsprüfung gegen ihre
Punkte), fließen aber nicht in `effective` ein, sondern in `bonus_points`.
`task.points` muss dann der Summe der regulären Teilaufgaben entsprechen.
Eine Bonus-Aufgabe behält `effective` (für ihre Lösungsprüfung), zählt aber
mit `regular_points` = 0 und `bonus_points` = `effective`. Verbraucher, die
Gesamtpunkte bilden (Klausuranalyse, Bewertungstabelle, Erwartungshorizont),
lesen `regular_points`/`bonus_points` bzw. `SubtaskPoints.is_bonus`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

POINTS_KEY = "points"
STATUS_OK = "ok"
STATUS_MISSING = "missing"
STATUS_INCONSISTENT = "inconsistent"
STATUS_NON_NUMERIC = "non_numeric"

_NUMBER_RE = re.compile(r"^\d+(?:[.,]\d+)?$")
_TRUE_TOKENS = frozenset({"true", "1", "ja", "yes"})
BONUS_KEY = "bonus"


def option_is_true(options: dict | None, key: str) -> bool:
    """Ob eine boolesche Block-Option gesetzt ist (`true`, `1`, `ja`, `yes`; ohne Groß-/Kleinschreibung)."""
    return str((options or {}).get(key) or "").strip().lower() in _TRUE_TOKENS


def is_bonus(options: dict | None) -> bool:
    """Ob eine Aufgabe/Teilaufgabe Bonuspunkte vergibt (`bonus=true`)."""
    return option_is_true(options, BONUS_KEY)


def points_badge(options: dict) -> str | None:
    """Punktanzeige am Aufgaben-/Teilaufgabenkopf: `2 P` bzw. `+2 Bonuspunkte` (``None`` ohne Punkte)."""
    label = points_label(options)
    if label is None:
        return None
    return f"+{label} Bonuspunkte" if is_bonus(options) else f"{label} P"


class NonNumeric:
    """Marker für eine vorhandene, aber nicht-numerische Punktangabe."""


NON_NUMERIC = NonNumeric()


def points_display(options: dict) -> str | None:
    """Originaltext der Punktangabe zur Anzeige (``None``, wenn keine gesetzt ist)."""
    raw = options.get(POINTS_KEY)
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def points_label(options: dict) -> str | None:
    """Anzeigetext der Punktangabe für den Renderer (ohne Einheit „P“).

    Numerische Angaben werden einheitlich mit deutschem Komma und ohne
    unnötige Nachkommastellen dargestellt (`0.5` → `0,5`, `2,50` → `2,5`),
    damit Aufgabenkopf, Bewertungstabelle und Erwartungshorizont dieselbe
    Schreibweise zeigen. Nicht-numerische Angaben (`ca. 5`) bleiben als
    Rohtext erhalten (Diagnose PK003 meldet sie separat). Ohne Angabe
    liefert die Funktion ``None``.
    """
    raw = points_display(options)
    if raw is None:
        return None
    value = parse_points(raw)
    if isinstance(value, Decimal):
        return format_points(value)
    return raw


def parse_points(raw) -> Decimal | NonNumeric | None:
    """`2`, `2,5`, `2.5` → `Decimal`; fehlend → ``None``; sonst `NON_NUMERIC`."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if not _NUMBER_RE.match(text):
        return NON_NUMERIC
    try:
        return Decimal(text.replace(",", "."))
    except InvalidOperation:
        return NON_NUMERIC


def format_points(value: Decimal | None) -> str:
    """Anzeige ohne unnötige Nachkommastellen, deutsches Komma (`1,5`)."""
    if value is None:
        return "?"
    normalized = value.normalize()
    text = format(normalized, "f")
    return text.replace(".", ",")


def format_signed_points(value: Decimal | None) -> str:
    """Wie `format_points`, negative Werte mit typografischem Minus (`−0,5`, U+2212).

    Für Abzüge je Fehler in Lösung und Erwartungshorizont; positive Werte
    bleiben ohne Vorzeichen.
    """
    if value is not None and value < 0:
        return "\u2212" + format_points(-value)
    return format_points(value)


@dataclass
class SubtaskPoints:
    """Punkte einer Teilaufgabe innerhalb einer Einheit."""

    block_index: int
    letter: str | None
    raw: str | None
    value: Decimal | NonNumeric | None
    options: dict

    @property
    def is_bonus(self) -> bool:
        """Ob die Teilaufgabe Bonuspunkte vergibt (zählt nicht zur regulären Punktzahl)."""
        return is_bonus(self.options)


@dataclass
class TaskUnit:
    """Eine Aufgabeneinheit: task-Block plus direkt folgende subtasks."""

    block_index: int
    number: str
    options: dict
    raw: str | None
    value: Decimal | NonNumeric | None
    subtasks: list[SubtaskPoints] = field(default_factory=list)
    effective: Decimal | None = None
    status: str = STATUS_MISSING
    codes: list[str] = field(default_factory=list)
    subtask_bonus: Decimal = Decimal(0)

    @property
    def is_bonus(self) -> bool:
        """Ob die ganze Aufgabe Bonuspunkte vergibt (`bonus=true` am Task)."""
        return is_bonus(self.options)

    @property
    def regular_points(self) -> Decimal | None:
        """Punkte, die zur regulären Punktzahl zählen (0 bei einer Bonus-Aufgabe)."""
        if self.effective is None:
            return None
        return Decimal(0) if self.is_bonus else self.effective

    @property
    def bonus_points(self) -> Decimal:
        """Zusätzlich erreichbare Bonuspunkte (Bonus-Aufgabe ganz, sonst ihre Bonus-Teilaufgaben)."""
        if self.is_bonus:
            return (self.effective or Decimal(0)) + self.subtask_bonus
        return self.subtask_bonus

    @property
    def subtasks_pointed(self) -> bool:
        """Ob alle Teilaufgaben bepunktet sind (und es welche gibt)."""
        return bool(self.subtasks) and all(sub.value is not None for sub in self.subtasks)


def iter_units(blocks):
    """Zerlegt die flache Blockliste in Aufgabeneinheiten.

    Eine Einheit beginnt bei `task` und endet beim nächsten `task` oder am
    Hilfsmittel-Trenner (`aidsplit`). Teilaufgaben vor der ersten Aufgabe
    gehören zu keiner Einheit.
    """
    units: list[TaskUnit] = []
    current: TaskUnit | None = None
    for index, (block_type, options, _content) in enumerate(blocks):
        if block_type == "task":
            raw = points_display(options)
            current = TaskUnit(index, str(len(units) + 1), options, raw, parse_points(raw))
            units.append(current)
        elif block_type == "aidsplit":
            current = None
        elif block_type == "subtask" and current is not None:
            raw = points_display(options)
            current.subtasks.append(SubtaskPoints(index, None, raw, parse_points(raw), options))
    for unit in units:
        if len(unit.subtasks) > 1:
            for position, sub in enumerate(unit.subtasks):
                sub.letter = chr(ord("a") + position)
    return units


def build_points_model(blocks) -> list[TaskUnit]:
    """Berechnet effektive Punkte und Status aller Aufgabeneinheiten."""
    units = iter_units(blocks)
    for unit in units:
        pointed = [sub for sub in unit.subtasks if sub.value is not None]
        if not pointed:
            _resolve_single(unit)
        elif len(pointed) < len(unit.subtasks):
            unit.status, unit.effective = STATUS_INCONSISTENT, None
            unit.codes.append("PK004")
        else:
            _resolve_from_subtasks(unit)
    return units


def _resolve_single(unit: TaskUnit) -> None:
    """Status und effektive Punkte einer Einheit ohne bepunktete Teilaufgaben (aus `task.points`)."""
    if unit.value is None:
        unit.status = STATUS_MISSING
    elif isinstance(unit.value, NonNumeric):
        unit.status = STATUS_NON_NUMERIC
        unit.codes.append("PK003")
    else:
        unit.status, unit.effective = STATUS_OK, unit.value


def _resolve_from_subtasks(unit: TaskUnit) -> None:
    """Status und effektive Punkte aus vollständig bepunkteten Teilaufgaben (PK001/PK003)."""
    if any(isinstance(sub.value, NonNumeric) for sub in unit.subtasks) or isinstance(unit.value, NonNumeric):
        unit.status, unit.effective = STATUS_NON_NUMERIC, None
        unit.codes.append("PK003")
        return
    total = sum((sub.value for sub in unit.subtasks if not sub.is_bonus), Decimal(0))
    unit.subtask_bonus = sum((sub.value for sub in unit.subtasks if sub.is_bonus), Decimal(0))
    if unit.value is not None and unit.value != total:
        unit.status, unit.effective = STATUS_INCONSISTENT, None
        unit.codes.append("PK001")
        return
    if unit.is_bonus:  # Bonus-Aufgabe: alle Teilaufgaben sind Bonus
        total, unit.subtask_bonus = total + unit.subtask_bonus, Decimal(0)
    unit.status, unit.effective = STATUS_OK, total


def subtask_effective(unit: TaskUnit, sub: SubtaskPoints) -> Decimal | None:
    """Effektive Punkte einer Teilaufgabe (nur bei konsistent bepunkteten Teilaufgaben)."""
    if unit.status == STATUS_OK and unit.subtasks_pointed and isinstance(sub.value, Decimal):
        return sub.value
    return None
