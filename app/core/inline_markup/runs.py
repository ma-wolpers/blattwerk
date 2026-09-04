"""Semantische Zwischenrepräsentation für Inline-Markup: `Run` und `ParseDiagnostic`.

`Run` ist bewusst ein flaches Modell (keine verschachtelte Baumstruktur):
eine Liste von Textläufen mit unabhängigen Stil-Flags deckt jede geforderte
Kombination (`**so*etwas***`, `***das** hier*`) über Flag-Kombination pro
Lauf ab, ohne eine Baum-Traversierung im Ausgabeformat zu benötigen. Vorbild
ist `TextRun` in `bw-gui/src/bw_gui/widgets/doc_text_events.py` (sibling-
Repo) -- der einzige bereits vorhandene Präzedenzfall für "Text in
typisierte Knoten parsen" in diesem Ökosystem.

`kind` unterscheidet drei grundsätzlich verschiedene Laufarten:
- "text": normaler Text, trägt die Stil-Flags.
- "code": Inline-Code oder Fenced-Code-Block-Inhalt, roh, keine Stil-Flags
  (verschachteltes Fett um Inline-Code wird bewusst NICHT unterstützt).
- "math": eine geschützte `$...$`/`$$...$$`-Formel, roh (inkl. `$`-
  Begrenzer), keine Stil-Flags.

Kommentare (`%%...%%`) erzeugen bewusst KEINEN `Run` -- sie werden in
`spans.py` vollständig verworfen, bevor überhaupt ein Run entstehen könnte.
Nur ein nicht geschlossener Kommentar hinterlässt Spuren, als
`ParseDiagnostic`, nicht als Run.

Alle Stil-Flags sind unabhängige, frei kombinierbare Dimensionen (bold,
italic, underline, highlight, strike, subscript, superscript, spoiler) --
kein exklusiver Zustand wie z. B. eine Textausrichtung. Ein Run mit
`subscript=True, superscript=True` ist ein seltener, aber wohldefinierter
Fall (z. B. `~^x^~` handgeschrieben verschachtelt), kein ungültiger
Zustand. Die einzige echte Exklusivität liegt in `kind`, das als Enum statt
als Flag modelliert ist -- Stil-Flags existieren nur bei `kind="text"`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RunKind = Literal["text", "code", "math"]


@dataclass(frozen=True)
class Run:
    """Ein einzelner Textlauf mit unabhängigen, frei kombinierbaren Stil-Flags.

    Für `kind != "text"` bleiben alle Stil-Flags auf `False` -- Code- und
    Mathe-Läufe tragen ausschließlich ihren rohen `text`.
    """

    kind: RunKind
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    highlight: bool = False
    strike: bool = False
    subscript: bool = False
    superscript: bool = False
    spoiler: bool = False
    is_block: bool = False
    """Nur bedeutsam für `kind="code"`: unterscheidet einen mehrzeiligen
    Fenced-Code-Block (rendert als `<pre><code>`) von einem einzeiligen
    Inline-Code-Span (rendert als `<code>`)."""

    @property
    def is_plain(self) -> bool:
        """True für einen unformatierten Textlauf (kind='text', keine Stil-Flags gesetzt).

        Für `markdown_bridge.py`: ein "plain" Run muss roh/unverändert im
        Markdown-Quelltext verbleiben, damit python-markdowns eigene,
        unveränderte Zuständigkeit (Links, Entities, `nl2br`, Blockstruktur)
        für genau diesen Text erhalten bleibt -- nur nicht-plain Runs
        (formatiert, Code, Mathe) werden gerendert und gestasht.
        """
        return self.kind == "text" and not any(
            (self.bold, self.italic, self.underline, self.highlight, self.strike, self.subscript, self.superscript, self.spoiler)
        )

    def with_flags(self, **extra_flags: bool) -> "Run":
        """Liefert eine Kopie mit zusätzlich gesetzten Stil-Flags (bestehende bleiben erhalten, ODER-verknüpft)."""
        if self.kind != "text":
            return self
        merged = {
            "bold": self.bold,
            "italic": self.italic,
            "underline": self.underline,
            "highlight": self.highlight,
            "strike": self.strike,
            "subscript": self.subscript,
            "superscript": self.superscript,
            "spoiler": self.spoiler,
        }
        for key, value in extra_flags.items():
            merged[key] = merged[key] or value
        return Run(kind=self.kind, text=self.text, **merged)


@dataclass(frozen=True)
class ParseDiagnostic:
    """Ein einzelner Parser-Befund (z. B. ein nicht geschlossenes `%%`).

    `code` folgt der Projektkonvention aus `blatt_validator_constants.py`
    (Präfix + dreistellige Nummer). Präfix `IM` (Inline-Markup) ist neu,
    weil dieses Paket dokumenttyp-übergreifend ist (Arbeitsblatt UND
    Kurzentwurf) und keinem bestehenden Präfix (`BL`/`AN`/`KZF`/...)
    eindeutig zuzuordnen wäre. `position` ist ein 0-basierter
    Zeichen-Offset in den Eingabetext, den der jeweilige Aufrufer bei
    Bedarf selbst in eine Zeilennummer umrechnet.
    """

    code: str
    severity: Literal["error", "warning"]
    message: str
    position: int | None = None


IM001_UNCLOSED_COMMENT = "IM001"

STYLE_FLAG_NAMES = (
    "bold",
    "italic",
    "underline",
    "highlight",
    "strike",
    "subscript",
    "superscript",
    "spoiler",
)


def style_flags(run: Run) -> dict:
    """Liefert die acht Stil-Flags eines Runs als Dict -- gemeinsamer Helfer für `emphasis.py`/`placeholders.py`."""
    return {name: getattr(run, name) for name in STYLE_FLAG_NAMES}
