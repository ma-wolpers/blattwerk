"""Inhalts-Hashes an einer Stelle."""

from __future__ import annotations

import hashlib


def sha256_hex(data: bytes) -> str:
    """SHA-256 als Hex-String.

    Example:
        >>> sha256_hex(b"")[:8]
        'e3b0c442'
    """
    return hashlib.sha256(data).hexdigest()


def short_identity_hash(text: str) -> str:
    """Kurzer, stabiler Hash eines Textes für Regionen und Diagnose-Identitäten.

    Keine Sicherheitsfunktion. Das Ergebnis steht in gespeicherten Bestätigungen abgehakter
    Warnungen: Ändert sich Verfahren oder Länge, gelten alle Haken als verloren.

    Args:
        text: Kanonische Textform, UTF-8-kodiert gehasht.

    Returns:
        Die ersten 16 Hex-Zeichen des SHA-1.

    Example:
        >>> short_identity_hash("")
        'da39a3ee5e6b4b0d'
    """
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
