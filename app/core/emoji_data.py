"""Unicode-Datentabellen für die Emoji-Erkennung (reine Daten, ohne Logik).

Vom 300-Zeilen-Limit ausgenommen wie `blatt_kern_shared_data.py`. Die Python-
Standardbibliothek kennt die Unicode-Eigenschaft `Emoji_Presentation` nicht
(`unicodedata` liefert nur Kategorie/Name), deshalb steht der benötigte Ausschnitt
hier als Tabelle. Logik dazu: `emoji_markup.py`.

Quelle: Unicode `emoji-data.txt` (Eigenschaft `Emoji_Presentation`), BMP-Teil.
Die Zeichen aus der Ebene 1 (SMP) deckt `SMP_PICTOGRAPHIC_RANGE` pauschal ab.
"""

from __future__ import annotations

CLUSTER_EXTENDERS = frozenset({"Mn", "Me", "Cf", "Sk"})
"""Unicode-Kategorien, die an ein vorangehendes Basiszeichen gebunden sind.

Kombinationszeichen (Mn, darunter der Variation Selector U+FE0F), umschließende
Zeichen (Me, z. B. Keycap U+20E3), Formatzeichen (Cf, z. B. ZWJ U+200D und die
Tag-Zeichen von Flaggen-Sequenzen) und Modifikatoren (Sk, z. B. Hauttöne
U+1F3FB–U+1F3FF). Genutzt von `emoji_markup.py` (Emoji-Cluster) und
`pdf_text_stamp_adapter.py` (Glyphen-Cluster beim Stempeln)."""

EMOJI_PRESENTATION_SELECTOR = "️"
"""VS16: erzwingt die bunte Emoji-Darstellung eines sonst textartigen Zeichens (↔️, ⚖️)."""

TEXT_PRESENTATION_SELECTOR = "︎"
"""VS15: erzwingt die Textdarstellung, auch bei Zeichen mit `Emoji_Presentation`."""

ZERO_WIDTH_JOINER = "‍"
"""Verbindet Emojis zu einer Sequenz (👨‍👩‍👧); das Zeichen danach gehört zum Cluster."""

SMP_PICTOGRAPHIC_RANGE = (0x1F000, 0x1FAFF)
"""Ebene-1-Block mit allen Bildzeichen (Spielsteine bis Symbols and Pictographs Extended-A).

Pauschal statt einzeln: Auch die wenigen textartigen Zeichen darin rendert der
Browser über die Emoji-Schrift; der Filter schadet ihnen nicht."""

REGIONAL_INDICATOR_RANGE = (0x1F1E6, 0x1F1FF)
"""Regionalindikatoren: zwei hintereinander bilden eine Flagge (🇩🇪) und ein Cluster."""

BMP_EMOJI_PRESENTATION_RANGES = (
    (0x231A, 0x231B),
    (0x23E9, 0x23EC),
    (0x23F0, 0x23F0),
    (0x23F3, 0x23F3),
    (0x25FD, 0x25FE),
    (0x2614, 0x2615),
    (0x2648, 0x2653),
    (0x267F, 0x267F),
    (0x2693, 0x2693),
    (0x26A1, 0x26A1),
    (0x26AA, 0x26AB),
    (0x26BD, 0x26BE),
    (0x26C4, 0x26C5),
    (0x26CE, 0x26CE),
    (0x26D4, 0x26D4),
    (0x26EA, 0x26EA),
    (0x26F2, 0x26F3),
    (0x26F5, 0x26F5),
    (0x26FA, 0x26FA),
    (0x26FD, 0x26FD),
    (0x2705, 0x2705),
    (0x270A, 0x270B),
    (0x2728, 0x2728),
    (0x274C, 0x274C),
    (0x274E, 0x274E),
    (0x2753, 0x2755),
    (0x2757, 0x2757),
    (0x2795, 0x2797),
    (0x27B0, 0x27B0),
    (0x27BF, 0x27BF),
    (0x2B1B, 0x2B1C),
    (0x2B50, 0x2B50),
    (0x2B55, 0x2B55),
)
"""BMP-Zeichen, die ohne Variation Selector bunt (als Emoji) erscheinen, z. B. ✅ ⭐ ⚡.

Textartige Zeichen wie ☐ ☑ ☆ fehlen bewusst: Sie bleiben Text, solange kein
U+FE0F folgt (mc-Kästchen, Sterne-Skala im Selfcheck)."""
