"""Gemeinsamer Kontext der Migrations-Zustandsmaschine: Pfade, Zustände, Journal-Abfragen.

Zustände pro Datei (vorwärts), jeder erst nach einem verbindlichen
Journal-Eintrag erreicht:

    PLANNED → BACKED_UP → TARGET_WRITTEN → TARGET_VERIFIED → TARGET_ATTRS_APPLIED
    → SOURCE_QUARANTINED → SOURCE_RO_CLEARED → SOURCE_REMOVED → COMMITTED
    → SIDE_STATE_APPLIED

Rückwärts: ROLLED_BACK (Datei) und SIDE_STATE_REVERTED (Begleitzustand).
Sonderzustände: SKIPPED (z. B. `changed_since_plan`) und CONFLICT (nichts
angefasst, Rückfrage nötig).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .fs_ops import FileIdentity
from .journal import Journal

PLANNED = "PLANNED"
BACKED_UP = "BACKED_UP"
TARGET_WRITTEN = "TARGET_WRITTEN"
TARGET_VERIFIED = "TARGET_VERIFIED"
TARGET_ATTRS_APPLIED = "TARGET_ATTRS_APPLIED"
SOURCE_QUARANTINED = "SOURCE_QUARANTINED"
SOURCE_RO_CLEARED = "SOURCE_RO_CLEARED"
SOURCE_REMOVED = "SOURCE_REMOVED"
COMMITTED = "COMMITTED"
SIDE_STATE_APPLIED = "SIDE_STATE_APPLIED"
ROLLED_BACK = "ROLLED_BACK"
SIDE_STATE_REVERTED = "SIDE_STATE_REVERTED"
SKIPPED = "SKIPPED"
CONFLICT = "CONFLICT"

FORWARD_ORDER = (
    PLANNED,
    BACKED_UP,
    TARGET_WRITTEN,
    TARGET_VERIFIED,
    TARGET_ATTRS_APPLIED,
    SOURCE_QUARANTINED,
    SOURCE_RO_CLEARED,
    SOURCE_REMOVED,
    COMMITTED,
    SIDE_STATE_APPLIED,
)
TERMINAL_STATES = (SIDE_STATE_APPLIED, ROLLED_BACK, SIDE_STATE_REVERTED, SKIPPED)


class ConflictError(Exception):
    """Ein Ist-Zustand passt zu keinem erwarteten Zustand; nichts wird angefasst."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


class SkipItem(Exception):
    """Der Eintrag wird übersprungen (z. B. Quelle seit dem Plan verändert)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ConflictResolver(Protocol):
    """Rückfragen bei Konflikten (CLI interaktiv/nicht-interaktiv, GUI-Dialog)."""

    def resolve(self, kind: str, item_label: str, choices: tuple[str, ...]) -> str:
        """Liefert eine der `choices`."""


class SideStateStore(Protocol):
    """Port für den Begleitzustand (Recent-Files, Keys quittierter Warnungen).

    Implementierungen ersetzen nur Einträge, die (kanonisch verglichen) genau
    `old` entsprechen -- dadurch sind Anwenden und Zurücknehmen idempotent und
    berühren nie Einträge anderer Dateien.
    """

    def apply_rename(self, old: str, new: str) -> None: ...


@dataclass
class ItemContext:
    """Alle Pfade und Journal-Informationen zu einem Planeintrag."""

    entry: object
    root: Path
    run_dir: Path
    run_id: str
    journal: Journal
    records: list[dict]
    warnings: list[str] = field(default_factory=list)

    @property
    def src(self) -> Path:
        return self.root / self.entry.source

    @property
    def dst(self) -> Path:
        return self.root / self.entry.target

    @property
    def tmp(self) -> Path:
        return self.dst.with_name(f".{self.dst.name}.bw-tmp-{self.run_id}")

    @property
    def quarantine(self) -> Path:
        return self.src.with_name(f"{self.src.name}.bw-migrating-{self.run_id}")

    @property
    def backup(self) -> Path:
        return self.run_dir / "backup" / self.entry.source

    @property
    def plan_identity(self) -> FileIdentity:
        return FileIdentity.from_dict(self.entry.identity)

    def item_records(self) -> list[dict]:
        return [record for record in self.records if record.get("item") == self.entry.item_id]

    def last_state(self) -> str | None:
        states = [record["state"] for record in self.item_records() if "state" in record]
        return states[-1] if states else None

    def reached(self, state: str) -> bool:
        """Ob `state` (vorwärts) bereits verbindlich erreicht wurde."""
        reached = {record["state"] for record in self.item_records() if "state" in record}
        return state in reached

    def recorded(self, key: str):
        """Letzter journalierter Wert eines Felds dieses Eintrags (z. B. `target_identity`)."""
        for record in reversed(self.item_records()):
            if key in record:
                return record[key]
        return None

    def mark(self, state: str, **extra) -> None:
        """Schreibt einen Zustandswechsel verbindlich ins Journal."""
        record = self.journal.append({"item": self.entry.item_id, "state": state, **extra})
        self.records.append(record)

    def intent(self, step: str, **extra) -> None:
        """Schreibt eine Absicht verbindlich ins Journal (vor der Aktion)."""
        record = self.journal.append({"item": self.entry.item_id, "intent": step, **extra})
        self.records.append(record)

    def label(self) -> str:
        return self.entry.source
