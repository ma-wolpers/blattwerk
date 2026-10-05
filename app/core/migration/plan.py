"""Scan eines Ordnerbaums und planstabiler Migrationsplan (`plan.json`).

Ablauf (Plan 2.1): `lstat` vor jedem Lesen (sichert `atime` und Creation
Time) → Ausschlüsse und technische Schutzgrenzen (Skip-Gründe, keine
Klassifikation) → `classify` → nur bei `sicher` Rewrite mit Verifikation →
Planeintrag mit Identitäts-Fingerprint und Rewrite-Hash.

Ausschlüsse: `.git`, versteckte Einträge (Name mit `.` oder Windows
HIDDEN/SYSTEM), Symlinks/Junctions/Reparse Points (nie betreten),
Pfadteile passend zu `*Lerngruppen*` (ohne Groß/Klein) und `--exclude`.
Cloud-Platzhalter werden nicht gelesen (`nicht_lokal`).
"""

from __future__ import annotations

import fnmatch
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..document_type_registry import spec_for_type
from .classify import CLASSIFIER_VERSION, STATUS_SAFE, classify
from .fs_ops import (
    PLACEHOLDER_ATTRIBUTES,
    FileIdentity,
    birthtime_ns,
    file_attributes,
    is_hidden,
    is_link_or_reparse,
    sha256_hex,
)
from .rewrite import REWRITE_VERSION, EditUnsafe, decode_utf8, encode_utf8, rewrite_for_target

PLAN_SCHEMA_VERSION = 1
DEFAULT_MAX_SIZE_BYTES = 20 * 1024 * 1024
DEFAULT_EXCLUDES = ("*Lerngruppen*",)

SKIP_TOO_LARGE = "uebersprungen_groesse"
SKIP_NOT_UTF8 = "nicht_utf8"
SKIP_NOT_LOCAL = "nicht_lokal"
SKIP_REPARSE = "reparse_point"
SKIP_REWRITE_UNSAFE = "rewrite_unsicher"


@dataclass(frozen=True)
class PlanEntry:
    """Ein geplanter Migrationsschritt (alle Pfade relativ zum Root, POSIX-Schreibweise)."""

    item_id: int
    source: str
    target: str
    target_type: str
    identity: dict
    attributes: int
    readonly: bool
    atime_ns: int
    mtime_ns: int
    birthtime_ns: int | None
    rewrite_sha256: str
    signals: tuple[str, ...]


@dataclass(frozen=True)
class ReportItem:
    """Eine gescannte Datei, die nicht (automatisch) migriert wird."""

    path: str
    status: str
    signals: tuple[str, ...] = ()


@dataclass
class MigrationPlan:
    """Planstabiler Migrationsplan; `--write` führt genau diesen Plan aus."""

    root: str
    entries: list[PlanEntry] = field(default_factory=list)
    report: list[ReportItem] = field(default_factory=list)
    plan_schema_version: int = PLAN_SCHEMA_VERSION
    classifier_version: int = CLASSIFIER_VERSION
    rewrite_version: int = REWRITE_VERSION

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, text: str) -> "MigrationPlan":
        """Lädt und validiert einen Plan (Versionen müssen exakt passen).

        Raises:
            PlanInvalid: bei falschem Format oder anderer Migrationslogik-Version.
        """
        try:
            data = json.loads(text)
            versions = (data["plan_schema_version"], data["classifier_version"], data["rewrite_version"])
            if versions != (PLAN_SCHEMA_VERSION, CLASSIFIER_VERSION, REWRITE_VERSION):
                raise PlanInvalid(f"Migrationslogik-Version passt nicht: {versions}")
            entries = [PlanEntry(**{**raw, "signals": tuple(raw["signals"])}) for raw in data["entries"]]
            report = [ReportItem(raw["path"], raw["status"], tuple(raw.get("signals", ()))) for raw in data["report"]]
            return cls(root=str(data["root"]), entries=entries, report=report)
        except PlanInvalid:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise PlanInvalid(f"plan.json ungueltig: {error}") from error


class PlanInvalid(Exception):
    """Plan ungültig oder mit anderer Migrationslogik erstellt."""


def target_name(source_name: str, target_type: str) -> str:
    """Zielname: Quellname ohne `.kwe.md` bzw. `.md` (ganzer Name, ohne Groß/Klein) plus Typ-Endung."""
    lowered = source_name.lower()
    stem = source_name[: -len(".kwe.md")] if lowered.endswith(".kwe.md") else source_name[: -len(".md")]
    return stem + spec_for_type(target_type).extension


def _excluded(relative: str, patterns: tuple[str, ...]) -> bool:
    parts = relative.split("/")
    lowered_patterns = [pattern.lower() for pattern in patterns]
    for pattern in lowered_patterns:
        if fnmatch.fnmatch(relative.lower(), pattern) or any(fnmatch.fnmatch(part.lower(), pattern) for part in parts):
            return True
    return False


def iter_candidates(root: Path, excludes: tuple[str, ...]):
    """Liefert `(pfad, relativ, lstat)` aller `.md`-Kandidaten bzw. Skip-Gründe als `(pfad, relativ, grund)`."""
    stack = [root]
    while stack:
        directory = stack.pop()
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            if entry.name == ".git" or _excluded(relative, excludes):
                continue
            lstat_result = os.lstat(path)
            if is_link_or_reparse(path):
                if entry.name.lower().endswith(".md"):
                    yield path, relative, SKIP_REPARSE
                continue
            if is_hidden(path, lstat_result):
                continue
            if entry.is_dir(follow_symlinks=False):
                stack.append(path)
            elif entry.name.lower().endswith(".md"):
                yield path, relative, lstat_result


def scan(root: Path, *, excludes: tuple[str, ...] = (), max_size: int = DEFAULT_MAX_SIZE_BYTES) -> MigrationPlan:
    """Scannt `root` und erzeugt den Plan (liest nur Kandidaten, schreibt nichts)."""
    resolved_root = Path(root).resolve()
    plan = MigrationPlan(root=str(resolved_root))
    all_excludes = tuple(DEFAULT_EXCLUDES) + tuple(excludes)
    for path, relative, info in iter_candidates(resolved_root, all_excludes):
        if isinstance(info, str):
            plan.report.append(ReportItem(relative, info))
            continue
        report_or_entry = _plan_file(path, relative, info, len(plan.entries) + 1, max_size)
        if isinstance(report_or_entry, ReportItem):
            plan.report.append(report_or_entry)
        else:
            plan.entries.append(report_or_entry)
    return plan


def _plan_file(path: Path, relative: str, lstat_result, item_id: int, max_size: int):
    attributes = file_attributes(lstat_result)
    if attributes & PLACEHOLDER_ATTRIBUTES:
        return ReportItem(relative, SKIP_NOT_LOCAL)
    if lstat_result.st_size > max_size:
        return ReportItem(relative, SKIP_TOO_LARGE)
    atime_ns, mtime_ns = lstat_result.st_atime_ns, lstat_result.st_mtime_ns
    creation_ns = birthtime_ns(lstat_result)
    data = path.read_bytes()
    try:
        text = decode_utf8(data)
    except UnicodeDecodeError:
        return ReportItem(relative, SKIP_NOT_UTF8)
    result = classify(path.name, text)
    if result.status != STATUS_SAFE:
        return ReportItem(relative, result.status, result.signals)
    try:
        rewritten = rewrite_for_target(text, result.target_type)
    except EditUnsafe:
        return ReportItem(relative, SKIP_REWRITE_UNSAFE, result.signals)
    identity = FileIdentity(len(data), mtime_ns, sha256_hex(data), lstat_result.st_dev, lstat_result.st_ino)
    return PlanEntry(
        item_id=item_id,
        source=relative,
        target=str(Path(relative).with_name(target_name(path.name, result.target_type)).as_posix()),
        target_type=result.target_type,
        identity=identity.as_dict(),
        attributes=attributes,
        readonly=not (lstat_result.st_mode & 0o200),
        atime_ns=atime_ns,
        mtime_ns=mtime_ns,
        birthtime_ns=creation_ns,
        rewrite_sha256=sha256_hex(encode_utf8(rewritten)),
        signals=result.signals,
    )
