import json

from app.core.block_computation_cache import (
    BlockComputationCache,
    ComputationKey,
    get_or_compute,
    open_block_computation_cache,
)


def _make_key(payload):
    return ComputationKey(block_type="dummy", version=1, payload=payload)


def test_get_or_compute_returns_memory_hit_without_recomputing():
    cache = BlockComputationCache()
    calls = []

    def compute():
        calls.append(1)
        return {"result": 42}

    key = _make_key({"a": 1})
    first = cache.get_or_compute(key, compute)
    second = cache.get_or_compute(key, compute)

    assert first == {"result": 42}
    assert second == {"result": 42}
    assert len(calls) == 1


def test_persistent_hit_survives_across_separate_cache_instances(tmp_path):
    cache_path = tmp_path / ".doc.blattwerk-cache"
    calls = []

    def compute():
        calls.append(1)
        return {"layout": [1, 2, 3]}

    key = _make_key({"words": ["A", "B"]})

    first_instance = BlockComputationCache(persistent_path=cache_path)
    first_instance.get_or_compute(key, compute)

    second_instance = BlockComputationCache(persistent_path=cache_path)
    result = second_instance.get_or_compute(key, compute)

    assert result == {"layout": [1, 2, 3]}
    assert len(calls) == 1


def test_module_level_get_or_compute_calls_compute_fn_directly_when_cache_is_none():
    calls = []

    def compute():
        calls.append(1)
        return "value"

    result = get_or_compute(None, _make_key({}), compute)

    assert result == "value"
    assert len(calls) == 1


def test_corrupted_cache_file_is_ignored_instead_of_raising(tmp_path):
    cache_path = tmp_path / ".doc.blattwerk-cache"
    cache_path.write_text("not valid json {{{", encoding="utf-8")

    cache = BlockComputationCache(persistent_path=cache_path)
    result = cache.get_or_compute(_make_key({}), lambda: "computed")

    assert result == "computed"


def test_wrong_format_version_is_ignored():
    cache_path_content = json.dumps({"cache_format_version": 999, "entries": {"x": "stale"}})

    def load_from(tmp_path):
        cache_path = tmp_path / ".doc.blattwerk-cache"
        cache_path.write_text(cache_path_content, encoding="utf-8")
        return cache_path

    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        cache_path = load_from(Path(tmp))
        cache = BlockComputationCache(persistent_path=cache_path)
        result = cache.get_or_compute(_make_key({}), lambda: "recomputed")

        assert result == "recomputed"


def test_write_failure_does_not_prevent_computation(tmp_path):
    unwritable_dir = tmp_path / "does-not-exist" / "still-does-not-exist"
    cache_path = unwritable_dir / ".doc.blattwerk-cache"

    # Simulate an unwritable target by pointing the persistent path at a file
    # that collides with a required parent directory name.
    blocking_file = tmp_path / "does-not-exist"
    blocking_file.write_text("blocking", encoding="utf-8")

    cache = BlockComputationCache(persistent_path=cache_path)
    result = cache.get_or_compute(_make_key({}), lambda: "value-despite-write-failure")

    assert result == "value-despite-write-failure"


def test_version_mismatch_recomputes_instead_of_reusing_stale_entry(tmp_path):
    cache_path = tmp_path / ".doc.blattwerk-cache"

    key_v1 = ComputationKey(block_type="dummy", version=1, payload={"a": 1})
    cache_v1 = BlockComputationCache(persistent_path=cache_path)
    cache_v1.get_or_compute(key_v1, lambda: "v1-result")

    key_v2 = ComputationKey(block_type="dummy", version=2, payload={"a": 1})
    cache_v2 = BlockComputationCache(persistent_path=cache_path)
    calls = []

    def compute_v2():
        calls.append(1)
        return "v2-result"

    result = cache_v2.get_or_compute(key_v2, compute_v2)

    assert result == "v2-result"
    assert len(calls) == 1


def test_open_block_computation_cache_derives_path_from_md_stem(tmp_path):
    md_path = tmp_path / "arbeitsblatt.md"
    md_path.write_text("---\n---\n", encoding="utf-8")

    cache = open_block_computation_cache(md_path, persist=True)
    cache.get_or_compute(_make_key({}), lambda: "value")

    assert (tmp_path / ".arbeitsblatt.blattwerk-cache").exists()


def test_result_and_payload_must_be_json_serializable_round_trip(tmp_path):
    """Cache results are only useful across process/instance boundaries if
    both the ComputationKey payload and compute_fn's return value survive a
    JSON round-trip -- this pins that contract down explicitly."""
    cache_path = tmp_path / ".doc.blattwerk-cache"
    key = _make_key({"nested": {"list": [1, 2, "three"]}, "flag": True})

    cache = BlockComputationCache(persistent_path=cache_path)
    cache.get_or_compute(key, lambda: {"cells": [[1, 2], [3, 4]], "ok": True})

    raw = json.loads(cache_path.read_text(encoding="utf-8"))
    assert raw["cache_format_version"] == 1
    stored_value = next(iter(raw["entries"].values()))
    assert stored_value == {"cells": [[1, 2], [3, 4]], "ok": True}
