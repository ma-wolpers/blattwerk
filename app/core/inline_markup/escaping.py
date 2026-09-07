"""Backslash-Escape-Schutz für die eigenen Marker-Zeichen (`\\*`, `\\_`, `\\=`, `\\~`, `\\^`, `\\|`, `` \\` ``, `\\%`, `\\!`).

`protect_escapes()` läuft in `emphasis.py::parse_emphasis` als allererster
Schritt, VOR jedem Marker-Durchlauf: jedes Escape wird durch ein eigenes
Private-Use-Zeichen ersetzt, auf das keiner der Marker-Regexe reagiert.
Damit kann z. B. `\\*text\\*` garantiert NICHT als `*text*` (kursiv)
fehlinterpretiert werden, unabhängig davon, welcher Marker-Durchlauf
zuerst drankommt. Ein reines "ersetze `\\X` durch `X` NACH dem Parsen"-
Ansatz böte diese Garantie nicht -- der Stern in `\\*text\\*` würde sonst
schon während des `*`-Durchlaufs als echtes Trennzeichen erkannt, bevor
die Escape-Auflösung überhaupt läuft (realer Bug in einer früheren Fassung).

Auflösung der Platzhalter ist danach bewusst KONSUMENTENABHÄNGIG (siehe
`resolve_escape_placeholders`/`restore_escape_backslashes`), weil
`markdown_bridge.py`s unformatierte ("plain") Textabschnitte anders
behandelt werden müssen als direkt gerenderte: sie gehen roh zurück an
python-markdown, das seine eigene, native Escape-Behandlung besitzt.
"""

from __future__ import annotations

import re

ESCAPABLE_CHARS = "*_=~^|`%!"
_ESCAPE_PLACEHOLDER_BASE = 0xF020
_ESCAPE_PLACEHOLDERS = {ch: chr(_ESCAPE_PLACEHOLDER_BASE + i) for i, ch in enumerate(ESCAPABLE_CHARS)}
_ESCAPE_PLACEHOLDERS_REVERSE = {placeholder: ch for ch, placeholder in _ESCAPE_PLACEHOLDERS.items()}
_ESCAPE_PROTECT_PATTERN = re.compile(r"\\([" + re.escape(ESCAPABLE_CHARS) + r"])")
_ESCAPE_PLACEHOLDER_PATTERN = re.compile("[" + "".join(_ESCAPE_PLACEHOLDERS.values()) + "]")


def protect_escapes(text: str) -> str:
    """Ersetzt jedes `\\X` (X in `ESCAPABLE_CHARS`) durch sein Platzhalter-Zeichen."""
    return _ESCAPE_PROTECT_PATTERN.sub(lambda m: _ESCAPE_PLACEHOLDERS[m.group(1)], text)


def contains_escape_placeholder(text: str) -> bool:
    """True, wenn `text` noch ungelöste Escape-Platzhalter enthält."""
    return bool(_ESCAPE_PLACEHOLDER_PATTERN.search(text))


def resolve_escape_placeholders(text: str) -> str:
    """Löst Escape-Platzhalter zum literalen Zeichen auf (`\\*` -> `*`).

    Für Konsumenten, die das Ergebnis DIREKT als finalen Text/HTML
    ausgeben (Kurzentwurf; und `markdown_bridge.py` für nicht-plain Runs,
    die es selbst über `html_renderer.py` rendert) -- hier endet die
    Verarbeitung, es gibt keine nachgelagerte Engine mehr, die den
    Rückschluss selbst vornehmen könnte.
    """
    if not _ESCAPE_PLACEHOLDER_PATTERN.search(text):
        return text
    return _ESCAPE_PLACEHOLDER_PATTERN.sub(lambda m: _ESCAPE_PLACEHOLDERS_REVERSE[m.group(0)], text)


def restore_escape_backslashes(text: str) -> str:
    """Löst Escape-Platzhalter zurück zur ORIGINALEN Backslash-Form auf (`\\*` bleibt `\\*`).

    Nur für `markdown_bridge.py`s `is_plain`-Runs: dieser Text wird roh an
    python-markdown zur WEITEREN Verarbeitung zurückgegeben, das seine
    eigene, native Escape-Behandlung für `\\*` etc. besitzt. Würden wir
    hier stattdessen den literalen Stern zurückgeben (siehe
    `resolve_escape_placeholders`), würde python-markdowns eigener,
    weiterhin aktiver Emphasis-Prozessor den nun unbewachten Stern
    fälschlich erneut als Kursiv-Markup interpretieren -- ein realer Bug
    in einer früheren Fassung dieses Moduls.
    """
    if not _ESCAPE_PLACEHOLDER_PATTERN.search(text):
        return text
    return _ESCAPE_PLACEHOLDER_PATTERN.sub(lambda m: "\\" + _ESCAPE_PLACEHOLDERS_REVERSE[m.group(0)], text)
