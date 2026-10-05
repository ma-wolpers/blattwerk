"""Frontmatter-Rewrite für sicher klassifizierte Altbestände (über die eine Edit-Engine).

Für `sicher` (und nur dann) wird:

* jede Top-Level-`mode`-Zeile entfernt (Nutzerentscheidung: auch
  `worksheet`/`solution`, weil `mode` nicht mehr existiert),
* `document_type` auf den kanonischen Wert des Ziels gesetzt bzw. eingefügt,
* bei einer Datei ganz ohne Frontmatter (nur `.kwe.md` möglich) ein
  Frontmatter angelegt.

Sonst ändert sich nichts. Byte-Genauigkeit (BOM, Zeilenenden, fehlende
Schluss-Newline, Kommentare) garantiert `frontmatter_edit.FrontmatterEditor`
samt Verifikation; ist der Edit nicht sicher, wird die Datei nicht migriert
(`rewrite_unsicher`).
"""

from __future__ import annotations

from ..document_semantics import DOCUMENT_TYPE_KEY
from ..frontmatter_edit import EditUnsafe, FrontmatterEditor
from .legacy_decode import legacy_keys_to_strip

REWRITE_VERSION = 1


def rewrite_for_target(text: str, target_type: str) -> str:
    """Liefert den migrierten Text oder wirft `EditUnsafe`."""
    editor = FrontmatterEditor(text)
    editor.ensure_frontmatter()
    for key in legacy_keys_to_strip():
        editor.remove_key(key)
    editor.set_scalar(DOCUMENT_TYPE_KEY, target_type)
    return editor.result()


def decode_utf8(data: bytes) -> str:
    """Dekodiert verlustfrei (BOM bleibt als Zeichen erhalten, Zeilenenden unverändert).

    Raises:
        UnicodeDecodeError: bei Nicht-UTF-8.
    """
    return data.decode("utf-8")


def encode_utf8(text: str) -> bytes:
    """Kodiert zurück; zusammen mit `decode_utf8` ein exakter Roundtrip."""
    return text.encode("utf-8")


__all__ = ["EditUnsafe", "REWRITE_VERSION", "decode_utf8", "encode_utf8", "rewrite_for_target"]
