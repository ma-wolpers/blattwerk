"""Migration-only Decoder für das historische Frontmatter-Feld `mode` (Invariante I3).

Im aktuellen Blattwerk gibt es kein `mode` mehr. Alte `.md`-Dateien tragen
es aber noch: `mode: presentation` war eine Präsentation, `mode: test` ein
Dokument ohne Sozialform-Symbole (Nutzerentscheidung: wird zur Klausur
`.kbw`). Nur dieses Modul darf den Alt-Key lesen; es wird ausschließlich aus
`app/core/migration/` importiert (Guardrail
`tests/test_guardrail_no_frontmatter_mode.py`). Nach der Migration ist jede
Top-Level-`mode`-Zeile entfernt.
"""

from __future__ import annotations

LEGACY_MODE_KEY = "mode"

# Historische Werte (inkl. Alias `ws`) -> Migrationsziel bzw. kein Ziel.
_LEGACY_MODE_TARGETS = {
    "presentation": "presentation",
    "test": "exam",
    "ws": None,
    "worksheet": None,
    "solution": None,
}


def decode_legacy_target_hint(meta: object) -> str | None:
    """Liefert das aus historischem `mode` ableitbare Ziel (`presentation`/`exam`) oder ``None``."""
    raw = meta.get(LEGACY_MODE_KEY) if isinstance(meta, dict) else None
    if not isinstance(raw, str):
        return None
    return _LEGACY_MODE_TARGETS.get(raw.strip().lower())


def has_weak_legacy_mode(meta: object) -> bool:
    """Ob ein historisches `mode: worksheet|solution|ws` vorliegt (nur schwaches Signal)."""
    raw = meta.get(LEGACY_MODE_KEY) if isinstance(meta, dict) else None
    return isinstance(raw, str) and raw.strip().lower() in {"ws", "worksheet", "solution"}


def legacy_keys_to_strip() -> tuple[str, ...]:
    """Top-Level-Keys, die die Migration unabhängig vom Wert entfernt."""
    return (LEGACY_MODE_KEY,)
