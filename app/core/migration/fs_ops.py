"""Dateisystem-Primitiven der Migration: Identität, No-Replace-Umbenennen, Attribute, Zeiten.

Sicherheitsregeln (Plan, Abschnitt 2.4):

* **Nie überschreiben.** `rename_no_replace` ist die einzige Umbenennung:
  unter Windows `os.rename` (wirft `FileExistsError`, wenn das Ziel existiert),
  auf POSIX `os.link` + `os.unlink` (nicht atomar; der Zwischenzustand mit
  zwei Namen auf denselben Inode wird von der Recovery erkannt). `os.replace`
  und `atomic_write_text` werden in der Migration nicht verwendet.
* **Identität = Hash + Inode.** `FileIdentity` kombiniert Inhalt (SHA-256,
  Größe, `mtime_ns`) mit `st_dev`/`st_ino` (Windows: File-ID). `atime`
  gehört bewusst nicht dazu, weil Lesen sie verändern darf.
* **Metadaten** werden explizit gesetzt (keine Abhängigkeit vom Verhalten
  einzelner Kopier-APIs); Fehlschläge melden die Aufrufer als Warnung.
"""

from __future__ import annotations

import ctypes
import hashlib
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"

FILE_ATTRIBUTE_READONLY = 0x1
FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_SYSTEM = 0x4
FILE_ATTRIBUTE_ARCHIVE = 0x20
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
FILE_ATTRIBUTE_OFFLINE = 0x1000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x40000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x400000
PLACEHOLDER_ATTRIBUTES = FILE_ATTRIBUTE_OFFLINE | FILE_ATTRIBUTE_RECALL_ON_OPEN | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
TRANSFERRED_ATTRIBUTES = FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_ARCHIVE


@dataclass(frozen=True)
class FileIdentity:
    """Inhalt plus Dateisystem-Identität einer Datei (ohne `atime`)."""

    size: int
    mtime_ns: int
    sha256: str
    dev: int
    ino: int

    def has_inode(self) -> bool:
        """Ob eine verlässliche Inode/File-ID verfügbar ist (``st_ino == 0``: nein)."""
        return self.ino != 0

    def as_dict(self) -> dict:
        return {"size": self.size, "mtime_ns": self.mtime_ns, "sha256": self.sha256, "dev": self.dev, "ino": self.ino}

    @classmethod
    def from_dict(cls, data: dict) -> "FileIdentity":
        return cls(int(data["size"]), int(data["mtime_ns"]), str(data["sha256"]), int(data["dev"]), int(data["ino"]))


def sha256_hex(data: bytes) -> str:
    """SHA-256 als Hex-String."""
    return hashlib.sha256(data).hexdigest()


def read_with_identity(path: Path) -> tuple[bytes, FileIdentity]:
    """Liest eine Datei und liefert Bytes samt Identität.

    `stat` vor und nach dem Lesen muss übereinstimmen (Größe, `mtime_ns`,
    Inode); sonst wurde die Datei während des Lesens verändert
    (`ChangedDuringRead`).
    """
    before = os.stat(path)
    data = Path(path).read_bytes()
    after = os.stat(path)
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ChangedDuringRead(str(path))
    return data, FileIdentity(after.st_size, after.st_mtime_ns, sha256_hex(data), after.st_dev, after.st_ino)


def identity_of(path: Path) -> FileIdentity:
    """Identität einer Datei (liest den Inhalt)."""
    return read_with_identity(path)[1]


class ChangedDuringRead(Exception):
    """Die Datei hat sich während des Lesens verändert."""


def same_inode(path_a: Path, path_b: Path) -> bool:
    """Ob zwei Pfade auf dieselbe Datei zeigen (nur mit verfügbarer Inode/File-ID)."""
    stat_a, stat_b = os.stat(path_a), os.stat(path_b)
    return stat_a.st_ino != 0 and (stat_a.st_dev, stat_a.st_ino) == (stat_b.st_dev, stat_b.st_ino)


def rename_no_replace(src: Path, dst: Path) -> None:
    """Benennt `src` in `dst` um, ohne ein bestehendes `dst` je zu überschreiben.

    Raises:
        FileExistsError: wenn `dst` bereits existiert (`src` bleibt unverändert).
    """
    if IS_WINDOWS:
        os.rename(src, dst)  # wirft unter Windows FileExistsError statt zu ersetzen
        return
    os.link(src, dst)  # wirft FileExistsError, wenn dst existiert
    os.unlink(src)


def write_new_file(path: Path, data: bytes) -> FileIdentity:
    """Legt eine Datei exklusiv an (`xb`), schreibt, fsync-t und liefert ihre Identität."""
    with open(path, "xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    result = os.stat(path)
    return FileIdentity(result.st_size, result.st_mtime_ns, sha256_hex(data), result.st_dev, result.st_ino)


def file_attributes(stat_result: os.stat_result) -> int:
    """Windows-Dateiattribute aus einem `stat`-Ergebnis (POSIX: 0)."""
    return int(getattr(stat_result, "st_file_attributes", 0) or 0)


def is_link_or_reparse(path: Path) -> bool:
    """Symlink, Junction oder anderer Reparse Point (wird nie betreten/migriert)."""
    result = os.lstat(path)
    return stat.S_ISLNK(result.st_mode) or bool(file_attributes(result) & FILE_ATTRIBUTE_REPARSE_POINT)


def is_hidden(path: Path, stat_result: os.stat_result) -> bool:
    """Versteckt = Name mit `.` oder Windows-Attribut HIDDEN/SYSTEM."""
    return Path(path).name.startswith(".") or bool(
        file_attributes(stat_result) & (FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)
    )


def is_readonly(path: Path) -> bool:
    """Ob die Datei schreibgeschützt ist (Windows-Read-only-Attribut bzw. kein Schreibbit)."""
    return not (os.stat(path).st_mode & stat.S_IWRITE)


def set_readonly(path: Path, readonly: bool) -> None:
    """Setzt bzw. entfernt den Schreibschutz explizit."""
    mode = os.stat(path).st_mode
    os.chmod(path, (mode & ~stat.S_IWRITE) if readonly else (mode | stat.S_IWRITE))


def set_windows_attributes(path: Path, attributes: int) -> bool:
    """Überträgt Hidden/System/Archive auf `path` (ohne Read-only zu berühren).

    Returns:
        ``True`` bei Erfolg oder wenn nichts zu tun ist (POSIX).
    """
    if not IS_WINDOWS:
        return True
    current = file_attributes(os.stat(path))
    wanted = (current & ~TRANSFERRED_ATTRIBUTES) | (attributes & TRANSFERRED_ATTRIBUTES)
    wanted &= ~FILE_ATTRIBUTE_REPARSE_POINT
    if wanted == current:
        return True
    return bool(ctypes.windll.kernel32.SetFileAttributesW(str(path), wanted or 0x80))


def set_times(path: Path, atime_ns: int, mtime_ns: int) -> None:
    """Setzt `atime`/`mtime` explizit."""
    os.utime(path, ns=(int(atime_ns), int(mtime_ns)))


def birthtime_ns(stat_result: os.stat_result) -> int | None:
    """Erstellungszeit, falls verfügbar (Windows: `st_birthtime_ns` bzw. `st_ctime_ns`)."""
    value = getattr(stat_result, "st_birthtime_ns", None)
    if value is not None:
        return int(value)
    return int(stat_result.st_ctime_ns) if IS_WINDOWS else None


def set_creation_time(path: Path, creation_ns: int | None) -> bool:
    """Setzt die Erstellungszeit (best effort, nur Windows). ``False`` bei Fehlschlag."""
    if creation_ns is None or not IS_WINDOWS:
        return creation_ns is None
    from ctypes import wintypes

    filetime_value = int(creation_ns) // 100 + 116444736000000000
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateFileW.restype = wintypes.HANDLE
    handle = kernel32.CreateFileW(str(path), 0x100, 0x7, None, 3, 0x02000000, None)
    if handle in (None, wintypes.HANDLE(-1).value):
        return False
    try:
        filetime = wintypes.FILETIME(filetime_value & 0xFFFFFFFF, filetime_value >> 32)
        return bool(kernel32.SetFileTime(handle, ctypes.byref(filetime), None, None))
    finally:
        kernel32.CloseHandle(handle)


def fsync_file(path: Path) -> None:
    """Erzwingt das Schreiben einer bestehenden Datei auf den Datenträger."""
    with open(path, "rb+") as handle:
        os.fsync(handle.fileno())
