"""Kurzentwurf-Erkennungssignale für die Klassifikation alter `.md`-Dateien.

Früher bestimmten diese Keys und Muster zur Laufzeit den Dokumenttyp
(`document_types.py`). Seit der Typ allein aus der Dateiendung kommt
(Invariante I1), werden sie nur noch von der Migration verwendet, um für
eine alte `.md`-Datei die Zielendung `.ebw` vorzuschlagen.

`KURZENTWURF_IDENTITY_DETECTION_KEYS`/`KURZENTWURF_LEGACY_DETECTION_SUPPORT_KEYS`
bleiben öffentlich benannt, weil `app/core/markdown_conventions.py` die
Support-Keys als `legacy_detection_only`-Katalogeintrag für die generierte
Anleitung verpackt.
"""

from __future__ import annotations

import re

KURZENTWURF_IDENTITY_DETECTION_KEYS = ("Stundenthema", "Lerngruppe", "start")
"""Frontmatter-Keys, die einen alten Kurzentwurf ausweisen (Migrationssignal)."""

KURZENTWURF_LEGACY_DETECTION_SUPPORT_KEYS = (
    "Stundentyp",
    "Dauer",
    "Oberthema",
    "Stundenziel",
    "Teilziele",
    "Kompetenzen",
    "Material",
    "Unterrichtsbesuch",
)
"""Zusätzliche, rein historische Keys, die die Kurzentwurf-Erkennung stützen.
Nicht von `kurzentwurf_runtime` gelesen oder gerendert."""

KURZENTWURF_PHASE_HEADER_RE = re.compile(
    r"(?im)^\s*#(?:einstieg|erarbeitung|sicherung|vertiefung|hausaufgabe|reserve)\b"
)
KURZENTWURF_MARKER_RE = re.compile(r"(?im)^\s*(?:S>|A>|U>|s<|ant<)\s*")
