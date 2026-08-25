"""Generic, block-type-agnostic cache for deterministic block computations.

Not part of any specific block's design -- any block type may use this to
avoid recomputing an expensive, deterministic, JSON-serializable result (e.g.
a crossword layout) across the separate validation and rendering passes of a
single build, or across multiple builds within one editing session. See
`docs/ARCHITEKTUR.md` for the full rationale and cache-key contract.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")

_CACHE_FORMAT_VERSION = 1


@dataclass(frozen=True)
class ComputationKey:
    """Identifies one deterministic block computation for caching purposes.

    `block_type` groups related computations (e.g. "crossword" vs.
    "crossword_code_selection" -- two different keys for two different
    computations on the same block, see `crossword_placement.py`).
    `version` lets a block type invalidate all of its own cached entries when
    its algorithm changes, without touching unrelated block types' entries.
    `payload` must carry every normalized input that influences the result
    (options, content, resolved layout values) and must be JSON-serializable,
    since it is hashed via `json.dumps`.
    """

    block_type: str
    version: int
    payload: dict

    def as_cache_key_string(self) -> str:
        """Builds a stable string key: `block_type:vN:<sha256 of the sorted payload>`."""
        digest = hashlib.sha256(
            json.dumps(self.payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        return f"{self.block_type}:v{self.version}:{digest}"


class BlockComputationCache:
    """In-memory cache with an optional best-effort persistent JSON backing file.

    Every failure mode (missing file, corrupted JSON, wrong format version, a
    write that can't be completed, e.g. a read-only directory) is swallowed
    silently: this cache is a pure performance optimization and must never
    prevent a document from compiling. Callers that don't want persistence at
    all can pass `persistent_path=None`, in which case this behaves as a
    plain per-instance in-memory cache.
    """

    def __init__(self, persistent_path: Path | None = None):
        self._memory: dict[str, object] = {}
        self._persistent_path = persistent_path
        self._persistent_entries: dict[str, object] = self._load_persistent()

    def get_or_compute(self, key: ComputationKey, compute_fn: Callable[[], T]) -> T:
        """Returns the cached result for `key`, computing and storing it on a miss.

        A memory hit is checked first, then a persistent-file hit (which is
        promoted into memory), and only on a full miss is `compute_fn()`
        actually invoked. `compute_fn`'s return value must be JSON-serializable
        when this cache was opened with a `persistent_path`.
        """
        cache_key = key.as_cache_key_string()

        if cache_key in self._memory:
            return self._memory[cache_key]

        if cache_key in self._persistent_entries:
            value = self._persistent_entries[cache_key]
            self._memory[cache_key] = value
            return value

        value = compute_fn()
        self._memory[cache_key] = value
        self._persistent_entries[cache_key] = value
        self._save_persistent()
        return value

    def _load_persistent(self) -> dict[str, object]:
        """Reads the persistent envelope file; any failure yields an empty cache."""
        if self._persistent_path is None:
            return {}
        try:
            raw = self._persistent_path.read_text(encoding="utf-8")
            envelope = json.loads(raw)
            if envelope.get("cache_format_version") != _CACHE_FORMAT_VERSION:
                return {}
            entries = envelope.get("entries")
            return entries if isinstance(entries, dict) else {}
        except Exception:
            return {}

    def _save_persistent(self) -> None:
        """Writes the persistent envelope atomically; any failure is ignored.

        Uses a temp file in the same directory plus `os.replace()` so a
        crash or concurrent read never observes a half-written cache file.
        """
        if self._persistent_path is None:
            return
        try:
            envelope = {
                "cache_format_version": _CACHE_FORMAT_VERSION,
                "entries": self._persistent_entries,
            }
            serialized = json.dumps(envelope, sort_keys=True, ensure_ascii=True)
            directory = self._persistent_path.parent
            directory.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(dir=str(directory), prefix=".blattwerk-cache-tmp-")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                    tmp_file.write(serialized)
                os.replace(tmp_name, self._persistent_path)
            except Exception:
                try:
                    os.unlink(tmp_name)
                except Exception:
                    pass
        except Exception:
            pass


def get_or_compute(cache: BlockComputationCache | None, key: ComputationKey, compute_fn: Callable[[], T]) -> T:
    """Cache-optional entry point: calls `compute_fn()` directly when `cache` is None.

    This is the single "policy" seam every caller should use -- it means a
    block's rendering/validation code never has to branch on whether caching
    is active; `cache=None` (the default everywhere until the application
    layer opts in) reproduces today's uncached behavior exactly.
    """
    if cache is None:
        return compute_fn()
    return cache.get_or_compute(key, compute_fn)


_SESSION_CACHE_PATHS: list[Path] = []


def open_block_computation_cache(md_path: Path, persist: bool) -> BlockComputationCache:
    """Opens the computation cache file next to `md_path` for the application layer.

    Ownership note: this is called by the GUI/application layer (or an
    explicit CLI caller) -- `build_worksheet()`/`build_help_cards()` never
    call this themselves, they only receive an already-open cache. The
    persistent file is always named `.{stem}.blattwerk-cache` regardless of
    `persist`, so multiple build calls within one session (e.g. a worksheet
    export followed by a solution export for the same document) still share
    results; `persist=False` additionally registers the path for best-effort
    deletion via `cleanup_session_caches()` on clean process exit.
    """
    md_path = Path(md_path)
    cache_path = md_path.parent / f".{md_path.stem}.blattwerk-cache"
    if not persist:
        _SESSION_CACHE_PATHS.append(cache_path)
    return BlockComputationCache(persistent_path=cache_path)


def cleanup_session_caches() -> None:
    """Best-effort deletion of all session-scoped cache files opened this run.

    Intended to be registered once via `atexit.register` at application
    startup (see `blattwerk.py`) -- never raises, since a cleanup failure
    must not affect shutdown. A crash that skips this leaves a stale file
    behind, which is harmless: `BlockComputationCache` re-validates the
    format version and key on every read.
    """
    for path in _SESSION_CACHE_PATHS:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
    _SESSION_CACHE_PATHS.clear()
