"""Lösungspunkte: einzige Zuordnung von `:::solution` zu (Teil-)Aufgaben und einzige `(xP)`-Regex.

Zuordnungsregel:

* **Ohne `target=`:** Ziel ist der nächste vorangehende `task`- oder
  `subtask`-Block; andere Blöcke dazwischen werden übersprungen. Die Suche
  stoppt am Hilfsmittel-Trenner (`aidsplit`) -- eine Lösung wird nie einer
  Aufgabe des anderen Teils zugeordnet. Keine vorangehende Aufgabe → SL001.
* **`target=task`** → Task der aktuellen Einheit; **`target=a|b|…`** → die
  Teilaufgabe mit genau diesem angezeigten Bezeichner (ohne Groß/Klein) in
  derselben Einheit. Ungültig → SL008 (Fehler).
* Mehrere Lösungen mit demselben Ziel werden in Dokumentreihenfolge
  zusammengeführt.

Items sind die Lösungspunkte aus `solution_structure.classify_solution` --
dieselbe Zerlegung, aus der `solution_display` die oberste Liste rendert.
Unterlisten gehören als Fortsetzung zum Eltern-Item. `(xP)` zählt nur am
Zeilenende der Kopfzeile eines Punkts (SL004 sonst).

Teilpunkte für alternative Lösungswege: `(x/nP)` bedeutet „x von n
erreichbaren Punkten“. Alternative Wege sind nicht summativ -- die Summe
der Zähler darf deshalb die Punktzahl n des Ziels übersteigen (Überzahl ist
der beabsichtigte Normalfall). `n` landet in `SolutionItem.of_total`; die
Prüfregeln dazu stehen in `blatt_validator_points` (SL009–SL013).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

from .points_model import iter_units, parse_points
from .solution_structure import LIST_LINE_RE, classify_solution

POINTS_SUFFIX_RE = re.compile(r"\((\d+(?:[.,]\d+)?)(?:\s*/\s*(\d+(?:[.,]\d+)?))?\s*P\)\s*$")


@dataclass
class SolutionItem:
    """Ein nummerierter Erwartungspunkt (Text ohne Punkt-Suffix).

    `points` ist x aus `(xP)` bzw. `(x/nP)`; `of_total` ist n bei der
    Teilpunkt-Schreibweise für alternative Lösungswege, sonst ``None``.
    """

    text: str
    points: Decimal | None
    of_total: Decimal | None = None


@dataclass
class SolutionTarget:
    """Zusammengeführte Lösungs-Items eines Ziels (Task oder Teilaufgabe)."""

    unit_index: int
    subtask_letter: str | None
    subtask_position: int | None
    items: list[SolutionItem] = field(default_factory=list)
    block_indices: list[int] = field(default_factory=list)
    misplaced_points: bool = False

    @property
    def is_task_level(self) -> bool:
        """Ob die Lösung zur Aufgabe selbst statt zu einer Teilaufgabe gehört."""
        return self.subtask_position is None


@dataclass
class SolutionIssue:
    """Zuordnungsproblem einer einzelnen `:::solution` (SL001/SL008)."""

    code: str
    block_index: int
    message: str


def parse_solution_items(content: str) -> tuple[list[SolutionItem], bool]:
    """Liefert die Items und ob `(xP)` an einer nicht zählenden Stelle stand (SL004).

    Die Punkte kommen ausschließlich aus `classify_solution` (Kopfzeile plus
    Fortsetzung). Nicht zählend ist ein Suffix in einer Listen- oder
    Aufzählungszeile, die keine Kopfzeile ist -- außerhalb geschützter
    Bereiche (Mathe, Kommentar, Codezaun), die nie ausgewertet werden.
    """
    layout = classify_solution(content)
    head_lines = {entry.head_line for entry in layout.entries}
    misplaced = any(
        LIST_LINE_RE.match(line) and POINTS_SUFFIX_RE.search(line)
        for number, line in enumerate(layout.lines)
        if number not in head_lines and number not in layout.protected_lines
    )
    items = []
    for entry in layout.entries:
        visible_head, *visible_rest = entry.visible_lines()
        match = POINTS_SUFFIX_RE.search(visible_head)
        value = parse_points(match.group(1)) if match else None
        of_total = parse_points(match.group(2)) if match and match.group(2) else None
        head = POINTS_SUFFIX_RE.sub("", visible_head).rstrip() if match else visible_head
        continuation = " ".join(part.strip() for part in visible_rest if part.strip())
        items.append(SolutionItem((head + (" " + continuation if continuation else "")).strip(), value, of_total))
    return items, misplaced


def collect_solution_targets(blocks) -> tuple[list[SolutionTarget], list[SolutionIssue]]:
    """Ordnet alle `:::solution`-Blöcke ihren Zielen zu (siehe Moduldoku)."""
    units = iter_units(blocks)
    unit_by_task_index = {unit.block_index: position for position, unit in enumerate(units)}
    targets: dict[tuple[int, int | None], SolutionTarget] = {}
    issues: list[SolutionIssue] = []
    current_unit: int | None = None
    last_target: tuple[int, int | None] | None = None
    for index, (block_type, options, content) in enumerate(blocks):
        if block_type == "task":
            current_unit = unit_by_task_index[index]
            last_target = (current_unit, None)
        elif block_type == "aidsplit":
            current_unit, last_target = None, None
        elif block_type == "subtask" and current_unit is not None:
            position = next(i for i, sub in enumerate(units[current_unit].subtasks) if sub.block_index == index)
            last_target = (current_unit, position)
        elif block_type == "solution":
            key = _resolve_target(options, current_unit, last_target, units, index, issues)
            if key is None:
                continue
            target = targets.setdefault(key, _new_target(units, key))
            items, misplaced = parse_solution_items(content)
            target.items.extend(items)
            target.block_indices.append(index)
            target.misplaced_points = target.misplaced_points or misplaced
    return sorted(targets.values(), key=lambda t: (t.unit_index, -1 if t.subtask_position is None else t.subtask_position)), issues


def _new_target(units, key) -> SolutionTarget:
    """Leeres Ziel für `(unit_index, subtask_position)` mit angezeigtem Teilaufgaben-Buchstaben."""
    unit_index, position = key
    letter = None if position is None else units[unit_index].subtasks[position].letter
    return SolutionTarget(unit_index, letter, position)


def _resolve_target(options, current_unit, last_target, units, index, issues):
    """Ziel einer Lösung nach `target=` bzw. der vorangehenden Aufgabe; meldet SL001/SL008 in `issues`."""
    raw_target = options.get("target")
    if raw_target is None:
        if last_target is None:
            issues.append(SolutionIssue("SL001", index, "Loesung ohne vorangehende Aufgabe wird keiner Aufgabe zugeordnet."))
        return last_target
    wanted = str(raw_target).strip().lower()
    if current_unit is None:
        issues.append(SolutionIssue("SL008", index, f"`target={raw_target}`: keine Aufgabe in diesem Teil vor der Loesung."))
        return None
    if wanted == "task":
        return (current_unit, None)
    for position, sub in enumerate(units[current_unit].subtasks):
        if sub.letter is not None and sub.letter == wanted:
            return (current_unit, position)
    issues.append(SolutionIssue("SL008", index, f"`target={raw_target}` passt zu keiner Teilaufgabe dieser Aufgabe."))
    return None
