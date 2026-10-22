"""Invarianten eines `ExamPartLayout` (wechselseitige Konsistenz von Teilen und Gruppen).

Ein Verstoß ist ein Programmierfehler im Resolver, keine Nutzerdiagnose:
`check_layout` wirft `ValueError` mit sprechender Meldung. Geprüft wird

* Teile: nicht leer, `order` lückenlos 0…n-1, `part_id` eindeutig, bekannte
  Teilart, Bereiche lückenlos ab Block 0 und nicht leer, Trenner im eigenen
  Bereich, nur der erste Teil ohne Trenner, Deckblatt-Trenner = Trenner des
  ersten Teils;
* Gruppen: `group_id` eindeutig, nicht leer, kein Teil doppelt oder in zwei
  Gruppen, nur bekannte `part_id`s, 1 ≤ k < n, Teile in `order` lückenlos;
* Teil ↔ Gruppe: jedes `choice`-Teil verweist auf genau die Gruppe, die es
  enthält; `aid`-Teile haben keine Gruppe und stehen in keiner.
"""

from __future__ import annotations

PART_KIND_AID = "aid"
PART_KIND_CHOICE = "choice"
PART_KINDS = frozenset({PART_KIND_AID, PART_KIND_CHOICE})


def check_layout(layout) -> None:
    """Prüft alle Invarianten; wirft beim ersten Verstoß `ValueError`."""
    _check_parts(layout.parts, layout.cover_end)
    membership = _check_groups(layout.groups, {part.part_id: part for part in layout.parts})
    _check_part_group_links(layout.parts, membership)


def _check_parts(parts, cover_end) -> None:
    """Reihenfolge, Eindeutigkeit, Teilart und lückenlose Bereiche."""
    if not parts:
        raise ValueError("ExamPartLayout ohne Teile")
    if [part.order for part in parts] != list(range(len(parts))):
        raise ValueError(f"order nicht lückenlos: {[part.order for part in parts]}")
    _require_unique([part.part_id for part in parts], "part_id")
    expected_start = 0
    for part in parts:
        if part.kind not in PART_KINDS:
            raise ValueError(f"Teil {part.part_id}: unbekannte Teilart {part.kind!r}")
        if part.start_block != expected_start or part.end_block <= part.start_block:
            raise ValueError(f"Teil {part.part_id}: Bereich {part.start_block}–{part.end_block} nicht lückenlos ab {expected_start}")
        if part.marker_block is None and part.order != 0:
            raise ValueError(f"Teil {part.part_id}: nur der erste Teil darf ohne Trenner beginnen")
        if part.marker_block is not None and not part.contains(part.marker_block):
            raise ValueError(f"Teil {part.part_id}: Trenner {part.marker_block} außerhalb des eigenen Bereichs")
        expected_start = part.end_block
    if cover_end is not None and cover_end != parts[0].marker_block:
        raise ValueError(f"Deckblatt-Trenner {cover_end} ist nicht der Trenner des ersten Teils")


def _check_groups(groups, parts_by_id) -> dict[str, str]:
    """Gruppenregeln; liefert `part_id → group_id` für die Verknüpfungsprüfung."""
    _require_unique([group.group_id for group in groups], "group_id")
    membership: dict[str, str] = {}
    for group in groups:
        if not group.part_ids:
            raise ValueError(f"Wahlgruppe {group.group_id} ist leer")
        for part_id in group.part_ids:
            if part_id not in parts_by_id:
                raise ValueError(f"Wahlgruppe {group.group_id}: unbekannter Teil {part_id!r}")
            if part_id in membership:
                raise ValueError(f"Teil {part_id} steht mehrfach in Wahlgruppen ({membership[part_id]}, {group.group_id})")
            membership[part_id] = group.group_id
        if not 1 <= group.k < len(group.part_ids):
            raise ValueError(f"Wahlgruppe {group.group_id}: k={group.k} nicht in 1…{len(group.part_ids) - 1}")
        orders = [parts_by_id[part_id].order for part_id in group.part_ids]
        if orders != list(range(orders[0], orders[0] + len(orders))):
            raise ValueError(f"Wahlgruppe {group.group_id}: Teile nicht zusammenhängend ({orders})")
    return membership


def _check_part_group_links(parts, membership: dict[str, str]) -> None:
    """Teil ↔ Gruppe in beiden Richtungen konsistent."""
    for part in parts:
        if part.kind == PART_KIND_AID and (part.group_id is not None or part.part_id in membership):
            raise ValueError(f"Hilfsmittelteil {part.part_id} darf keiner Wahlgruppe angehören")
        if part.kind == PART_KIND_CHOICE and (part.group_id is None or membership.get(part.part_id) != part.group_id):
            raise ValueError(f"Wahlteil {part.part_id}: group_id {part.group_id!r} passt nicht zur Gruppe, die ihn enthält")


def _require_unique(values, name: str) -> None:
    """`ValueError`, wenn ein Wert doppelt vorkommt."""
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        raise ValueError(f"{name} doppelt: {duplicates}")
