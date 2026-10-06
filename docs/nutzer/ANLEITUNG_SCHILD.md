<!--
Automatisch generiert aus app/core/markdown_conventions.py.
NICHT VON HAND BEARBEITEN.
Neu erzeugen: python tools/docs/generate_authoring_guides.py
-->



# Schilder erstellen

Ein Schilder-Dokument (`.sbw`) macht aus jedem Schild eine eigene A4-Seite, auf der nur der Text steht – mittig und so groß wie möglich. Typisch: Begriffe für eine Sortier- oder Zuordnungsaufgabe, Stationsschilder, Tafelüberschriften.

## 1. Schnellstart

```markdown
---
document_type: schild
Titel: Neue Schilder
ausrichtung: hoch          # hoch | quer
fett: ja                   # ja | nein
rand: 15                   # Seitenrand in mm
schriftgroesse: einheitlich  # einheitlich | maximal
---

Erstes Schild

---

Zweites Schild
```

## 2. Schilder trennen

Schilder werden durch eine Zeile getrennt, die nur `---` enthält. Leerzeilen um den Trenner sind egal. Ein Zeilenumbruch *innerhalb* eines Schilds bleibt als Umbruch erhalten; sonst bricht Blattwerk nur zwischen Wörtern um – Wörter werden nie getrennt. Der Text wird nicht als Markdown gelesen: `**`, `#` usw. erscheinen wörtlich.

## 3. Optionen im Frontmatter

| Option | Werte | Standard | Wirkung |
| --- | --- | --- | --- |
| `ausrichtung` | `hoch` / `quer` | `hoch` | A4 hochkant oder quer. |
| `fett` | `ja` / `nein` | `ja` | Schrift fett oder normal. |
| `rand` | Zahl in mm (0–80) | `15` | Abstand zum Blattrand auf allen Seiten. |
| `schriftgroesse` | `einheitlich` / `maximal` | `einheitlich` | `einheitlich`: alle Schilder gleich groß – so groß, dass auch das längste passt. `maximal`: jedes Schild für sich so groß wie möglich. |

Ungültige Werte gelten als Standardwert und werden gemeldet (`SBW003`).

## 4. Wie die Schriftgröße bestimmt wird

Blattwerk probiert für jedes Schild aus, wie groß der Text werden kann, ohne über den Rand zu laufen. Begrenzt wird das meist vom längsten einzelnen Wort (es muss in eine Zeile passen) oder bei langen Texten von der Seitenhöhe. Vorschau und PDF sind dabei identisch.

## 5. Warnungen

- `SBW001`: Das Dokument enthält kein Schild.
- `SBW002`: Leeres Schild – meist ein doppeltes oder abschließendes `---`.
- `SBW003`: Ungültige Option im Frontmatter.
