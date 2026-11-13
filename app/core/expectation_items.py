"""Erwartungen: einzige Zuordnung von `:::expectation` zu (Teil-)Aufgaben und einzige Punktsumme.

Zuordnungsregel:

* **Ohne `target=`:** Ziel ist der nächste vorangehende `task`- oder
  `subtask`-Block; andere Blöcke dazwischen werden übersprungen. Die Suche
  stoppt an jedem Teil-Trenner (`aidsplit`/`choicesplit`) -- eine Erwartung wird nie einer
  Aufgabe des anderen Teils zugeordnet. Keine vorangehende Aufgabe → SL001.
* **`target=task`** → Task der aktuellen Einheit; **`target=a|b|…`** → die
  Teilaufgabe mit genau diesem angezeigten Bezeichner (ohne Groß/Klein) in
  derselben Einheit. Ungültig → SL008 (Fehler).
* Mehrere Erwartungsblöcke mit demselben Ziel werden in Dokumentreihenfolge
  zusammengeführt.

Items sind die Erwartungen aus `expectation_structure.classify_expectations`;
die Grammatik der Punktklammer steht ausschließlich in `points_suffix`.
`:::solution` ist reiner Lösungstext und wird nie bewertet -- stehen dort noch
Punktangaben, meldet der Validator SL024 (`solution_has_points`).

Abzüge je Fehler (`(−0,5P)`, negative `points`) gehören zu keiner Summe
und zu keinem Weg; sie werden im Erwartungshorizont getrennt ausgewiesen.

Alternative Lösungswege: Ein Buchstabe im Suffix (`(0,5aP)`, `(1bP)`)
ordnet den Punkt einem Weg zu; Punkte ohne Buchstabe gelten für alle Wege.
Erreichbar ist dann Σ(ohne Buchstabe) + max über die Wege von Σ(Weg)
(`expectation_points_total`).

Summative Optionen: `(x/kP)` -- alle Optionen eines Ziels zählen zusammen,
höchstens k Punkte („von diesen vier Begründungen brauchst du zwei“).
Erreichbar ist insgesamt gemeinsam + bester Weg + min(Σ Optionen, k).
Geltungsbereich (für Wege und Optionen) ist genau ein Ziel
(`ExpectationTarget`): Mehrere Erwartungsblöcke desselben Ziels teilen sich die
Buchstaben, Aufgabenebene und jede Teilaufgabe sind getrennt, am `--hm`
wird zurückgesetzt.

GRENZE: eine Wahlentscheidung je Ziel. Zwei unabhängige Entscheidungen in
derselben (Teil-)Aufgabe lassen sich mit Buchstaben nicht ausdrücken und
gehören auf zwei Teilaufgaben verteilt (Nutzerentscheidung 2026-10-16).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .exam_parts_position import PART_SPLIT_BLOCKS
from .expectation_structure import classify_expectations
from .points_model import iter_units
from .points_suffix import SUFFIX_NONE, parse_points_suffix, strip_valid_suffix

EXPECTATION_BLOCK = "expectation"
"""Blocktyp, aus dem allein Erwartungen und Teilpunkte gelesen werden."""


@dataclass
class ExpectationItem:
    """Eine Erwartung (Text ohne gültiges Punkt-Suffix).

    Attributes:
        text: Sichtbarer Text (alle Zeilen verbunden, ohne Kommentare und ohne
            gültiges Suffix; ein unlesbares Suffix bleibt im Text).
        points: Punktzahl, **nur** bei gültigem Suffix (`points_suffix`),
            sonst ``None`` -- unlesbare Suffixe gehen so in keine Summe ein.
            Negativ = Abzug je Fehler (`is_deduction`).
        path: Weg-Buchstabe des Suffixes oder ``None`` (gilt für alle Wege).
        suffix_status: Status aus `points_suffix` (`none`/`valid`/`invalid`).
        suffix_text: Wortlaut der Suffix-Klammer (für Diagnosetexte), sonst leer.
        kind: Erwartungstyp (Schlüssel aus `expectation_kinds`) oder ``None``.
        kind_token: Typ-Token wie geschrieben; gesetzt, aber `kind` ``None`` = unbekannter Typ (SL017).
        cap: Höchstwert k einer summativen Option `(x/kP)`, sonst ``None``.
        label: Optionale Nummer der Erwartung (`"1"` bei `1. …`) oder ``None``.
    """

    text: str
    points: Decimal | None
    path: str | None = None
    suffix_status: str = SUFFIX_NONE
    suffix_text: str = ""
    kind: str | None = None
    kind_token: str | None = None
    cap: Decimal | None = None
    label: str | None = None

    @property
    def is_option(self) -> bool:
        """Ob die Erwartung eine summative Option `(x/kP)` ist."""
        return self.cap is not None

    @property
    def is_deduction(self) -> bool:
        """Ob die Erwartung ein Abzug je Fehler ist (negativer Zahlenwert)."""
        return self.points is not None and self.points < 0


@dataclass
class ExpectationTarget:
    """Zusammengeführte Erwartungen eines Ziels (Task oder Teilaufgabe)."""

    unit_index: int
    subtask_letter: str | None
    subtask_position: int | None
    items: list[ExpectationItem] = field(default_factory=list)
    block_indices: list[int] = field(default_factory=list)

    @property
    def is_task_level(self) -> bool:
        """Ob die Erwartungen zur Aufgabe selbst statt zu einer Teilaufgabe gehören."""
        return self.subtask_position is None


@dataclass
class ExpectationIssue:
    """Zuordnungsproblem eines einzelnen `:::expectation`-Blocks (SL001/SL008)."""

    code: str
    block_index: int
    message: str


def parse_expectation_items(content: str) -> list[ExpectationItem]:
    """Liefert die Erwartungen eines Blockinhalts (Zerlegung allein aus `classify_expectations`)."""
    items = []
    for entry in classify_expectations(content).entries:
        visible = [line.strip() for line in entry.visible_lines()]
        suffix_line = entry.suffix_line()
        suffix = parse_points_suffix(suffix_line)
        body = [part for part in visible if part]
        body[-1] = strip_valid_suffix(suffix_line, suffix).strip()
        items.append(ExpectationItem(
            " ".join(part for part in body if part), suffix.value, suffix.path, suffix.status,
            suffix.text_in(suffix_line), suffix.kind, suffix.kind_token, suffix.cap, entry.label,
        ))
    return items


def solution_has_points(content: str) -> bool:
    """Ob ein `:::solution`-Inhalt noch Punktangaben trägt (SL024) -- dieselbe Grammatik wie Erwartungen."""
    return any(item.suffix_status != SUFFIX_NONE for item in parse_expectation_items(content))


@dataclass(frozen=True)
class PointsTotal:
    """Erreichbare Punkte eines Ziels (`expectation_points_total`).

    Attributes:
        total: gemeinsam + bester Weg.
        shared: Summe der Punkte ohne Weg-Buchstaben.
        paths: Summe je Weg-Buchstabe (alphabetisch).
        best_path: Buchstabe des Wegs mit der höchsten Summe (bei Gleichstand
            der alphabetisch erste) oder ``None`` ohne Wege.
        options: Summe aller Optionen `(x/kP)` (ungekappt).
        option_caps: alle vorkommenden Höchstwerte k (gültig ist genau einer, sonst SL019).
    """

    total: Decimal
    shared: Decimal
    paths: dict[str, Decimal]
    best_path: str | None
    options: Decimal = Decimal(0)
    option_caps: frozenset[Decimal] = frozenset()


def expectation_points_total(items) -> PointsTotal:
    """Erreichbare Punkte: Σ(ohne Buchstabe) + max über die Wege von Σ(Weg) + min(Σ Optionen, k).

    Berücksichtigt nur Punkte mit Zahlenwert (gültiges Suffix); Abzüge je
    Fehler (negative Werte) zählen nie mit, auch nicht mit Buchstabe. Alle Werte
    sind `Decimal` aus `points_model.parse_points` (aus Strings, nie `float`),
    der Vergleich mit `points=` ist daher exakt.

    GRENZE: Alle Buchstaben eines Ziels bilden *eine* Wahlentscheidung
    (siehe Moduldocstring).
    """
    shared, paths, options, caps = Decimal(0), {}, Decimal(0), set()
    for item in items:
        if item.points is None or item.points < 0:
            continue
        if item.is_option:
            options += item.points
            caps.add(item.cap)
        elif item.path is None:
            shared += item.points
        else:
            paths[item.path] = paths.get(item.path, Decimal(0)) + item.points
    ordered = dict(sorted(paths.items()))
    best = max(ordered, key=lambda letter: ordered[letter]) if ordered else None
    # Bei mehreren Höchstwerten (SL019) zählt der größte -- der Validator meldet das vor jeder Summenprüfung.
    capped = min(options, max(caps)) if caps else Decimal(0)
    total = shared + (ordered[best] if best else Decimal(0)) + capped
    return PointsTotal(total, shared, ordered, best, options, frozenset(caps))


def collect_expectation_targets(blocks) -> tuple[list[ExpectationTarget], list[ExpectationIssue]]:
    """Ordnet alle `:::expectation`-Blöcke ihren Zielen zu (siehe Moduldoku)."""
    units = iter_units(blocks)
    unit_by_task_index = {unit.block_index: position for position, unit in enumerate(units)}
    targets: dict[tuple[int, int | None], ExpectationTarget] = {}
    issues: list[ExpectationIssue] = []
    current_unit: int | None = None
    last_target: tuple[int, int | None] | None = None
    for index, (block_type, options, content) in enumerate(blocks):
        if block_type == "task":
            current_unit = unit_by_task_index[index]
            last_target = (current_unit, None)
        elif block_type in PART_SPLIT_BLOCKS:
            current_unit, last_target = None, None
        elif block_type == "subtask" and current_unit is not None:
            position = next(i for i, sub in enumerate(units[current_unit].subtasks) if sub.block_index == index)
            last_target = (current_unit, position)
        elif block_type == EXPECTATION_BLOCK:
            key = _resolve_target(options, current_unit, last_target, units, index, issues)
            if key is None:
                continue
            target = targets.setdefault(key, _new_target(units, key))
            target.items.extend(parse_expectation_items(content))
            target.block_indices.append(index)
    return sorted(targets.values(), key=lambda t: (t.unit_index, -1 if t.subtask_position is None else t.subtask_position)), issues


def _new_target(units, key) -> ExpectationTarget:
    """Leeres Ziel für `(unit_index, subtask_position)` mit angezeigtem Teilaufgaben-Buchstaben."""
    unit_index, position = key
    letter = None if position is None else units[unit_index].subtasks[position].letter
    return ExpectationTarget(unit_index, letter, position)


def _resolve_target(options, current_unit, last_target, units, index, issues):
    """Ziel einer Erwartung nach `target=` bzw. der vorangehenden Aufgabe; meldet SL001/SL008 in `issues`."""
    raw_target = options.get("target")
    if raw_target is None:
        if last_target is None:
            issues.append(ExpectationIssue("SL001", index, "Erwartung ohne vorangehende Aufgabe wird keiner Aufgabe zugeordnet."))
        return last_target
    wanted = str(raw_target).strip().lower()
    if current_unit is None:
        issues.append(ExpectationIssue("SL008", index, f"`target={raw_target}`: keine Aufgabe in diesem Teil vor der Erwartung."))
        return None
    if wanted == "task":
        return (current_unit, None)
    for position, sub in enumerate(units[current_unit].subtasks):
        if sub.letter is not None and sub.letter == wanted:
            return (current_unit, position)
    issues.append(ExpectationIssue("SL008", index, f"`target={raw_target}` passt zu keiner Teilaufgabe dieser Aufgabe."))
    return None
