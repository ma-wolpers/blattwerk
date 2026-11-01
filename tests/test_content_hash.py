"""Inhalts-Hashes: Die Werte stehen in gespeicherten Daten und dürfen sich nicht ändern."""

from __future__ import annotations

from app.core.blatt_validator_region import compute_block_region_id
from app.core.block_computation_cache import ComputationKey
from app.core.content_hash import sha256_hex, short_identity_hash
from app.core.kurzentwurf_runtime.region import compute_phase_region_id


def test_known_values_stay_stable():
    assert sha256_hex(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert short_identity_hash("abc") == "a9993e364706816a"


def test_region_ids_keep_their_stored_form():
    """Abgehakte Warnungen hängen an diesen IDs; die Werte stammen aus der Fassung vor dem Umzug."""
    assert compute_block_region_id("task", {"points": "2"}) == "worksheet:block:" + short_identity_hash("task|points=2")
    assert compute_phase_region_id("Einstieg", 10, "08:00") == "kurzentwurf:phase:" + short_identity_hash("Einstieg|10|08:00")


def test_computation_key_format_stays_stable():
    key = ComputationKey("crossword", 1, {"a": 1})
    assert key.as_cache_key_string() == "crossword:v1:" + sha256_hex(b'{"a": 1}')
