"""Write-Ahead-Journal der Migration (`journal.jsonl`).

Garantien (Plan 2.4):

* Jeder Eintrag ist eine JSON-Zeile mit `seq` und `crc32` über den
  restlichen Inhalt. Geschrieben wird per Append, dann `flush` und
  `os.fsync`; **verbindlich ist ein Eintrag, sobald `fsync` zurückkehrt.**
* Eine abgerissene bzw. CRC-ungültige **letzte** Zeile gilt als nie
  geschrieben (Absturz mitten im Schreiben). Eine kaputte Zeile davor ist ein
  echter Schaden → `JournalCorrupt` (dann wird nichts automatisch getan).
* Regel der Aufrufer: "Absicht X" verbindlich vor X, "X erledigt" nach der
  Verifikation. Verzeichnis-fsync ist unter Windows nicht möglich; die
  Recovery prüft deshalb immer zusätzlich den tatsächlichen Plattenzustand.
"""

from __future__ import annotations

import json
import os
import zlib
from pathlib import Path


class JournalCorrupt(Exception):
    """Eine Journalzeile vor der letzten ist unlesbar oder CRC-ungültig."""


def _crc(payload: dict) -> int:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return zlib.crc32(canonical.encode("utf-8"))


class Journal:
    """Append-only-Journal mit fsync pro Eintrag."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._seq = len(read_journal(self.path)) if self.path.exists() else 0

    def append(self, record: dict) -> dict:
        """Schreibt einen Eintrag verbindlich (kehrt erst nach `fsync` zurück)."""
        self._seq += 1
        payload = {"seq": self._seq, **record}
        line = json.dumps({**payload, "crc32": _crc(payload)}, ensure_ascii=False) + "\n"
        with open(self.path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        return payload


def read_journal(path: Path) -> list[dict]:
    """Liest alle verbindlichen Einträge.

    Raises:
        JournalCorrupt: bei einer kaputten Zeile, die nicht die letzte ist.
    """
    if not Path(path).exists():
        return []
    raw_lines = Path(path).read_text(encoding="utf-8").split("\n")
    if raw_lines and raw_lines[-1] == "":
        raw_lines.pop()
    records = []
    for index, raw in enumerate(raw_lines):
        record = _parse_line(raw)
        if record is None:
            if index == len(raw_lines) - 1:
                break  # abgerissene letzte Zeile: gilt als nie geschrieben
            raise JournalCorrupt(f"Journalzeile {index + 1} ist beschaedigt.")
        records.append(record)
    return records


def _parse_line(raw: str) -> dict | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "crc32" not in data:
        return None
    crc = data.pop("crc32")
    return data if crc == _crc(data) else None
