# CSS-Anleitung für Blattwerk (ohne Vorkenntnisse)

Diese Anleitung ist für Menschen, die **kein CSS können** und trotzdem das Aussehen ihrer Arbeitsblätter anpassen wollen.

Ziel: Du sollst nach 10–20 Minuten sicher kleine Änderungen in `assets/worksheet.css` machen können.

---

## 1) Was ist CSS überhaupt?

- CSS bestimmt, **wie etwas aussieht** (Farben, Abstände, Rahmen, Schriftgrößen).
- Die Inhalte kommen aus Markdown/HTML – CSS macht daraus ein gestaltetes Arbeitsblatt.

Merksatz:
- **Markdown/HTML = Inhalt**
- **CSS = Design**

---

## 2) Welche Datei ist für dich wichtig?

Für Design-Änderungen arbeitest du fast immer nur hier:

- `assets/worksheet.css`

Diese Datei ist jetzt bewusst **normales, gültiges CSS**. Du kannst sie in VS Code direkt bearbeiten.

---

## 3) So ist eine CSS-Regel aufgebaut

Beispiel:

```css
.task {
    margin: 2em 0 0.5em 0;
}
```

Bedeutung:
- `.task` = „alle Elemente mit Klasse task"
- `margin` = Außenabstand
- `2em 0 0.5em 0` = oben 2em, rechts 0, unten 0.5em, links 0

Grundform:

```css
.selector {
    eigenschaft: wert;
}
```

---

## 4) Die wichtigsten Bereiche in deiner Datei

### 4.1 Globale Farben und Linien (`:root`)

Ganz oben steht ein Block mit Variablen, z. B.:

- `--text-color`
- `--header-color`
- `--field-border-width`

Damit steuerst du zentrale Designwerte.

### 4.2 Seitenformat (`@page`)

Im CSS gibt es ein Default für Papiergröße und Ränder:

```css
@page {
    size: A4 portrait;
    margin: 2.0cm 1.5cm 1.5cm 1.5cm;
}
```

### 4.3 Inhalte (z. B. Aufgaben, Material, Antwortfelder)

Typische Blöcke:
- `.material` (Materialkasten)
- `.task` (Aufgabenblock)
- `.answer.lines .line` (Linien zum Schreiben)
- `.answer.grid` (Kästchenraster)
- `.answer.dots` (Punktfläche)
- `.answer.numberline` (horizontale Zahlengerade / Zahlenstrahl)

---

## 5) Wichtig: Was gewinnt bei Konflikten?

Blattwerk arbeitet mit **Defaults + Laufzeit-Overrides**:

1. Zuerst wird `assets/worksheet.css` geladen (deine Defaults).
2. Beim Export setzt Blattwerk danach dynamische Werte für:
   - Seitenformat (`@page`)
   - Druckprofil (`:root` Variablen)

Das heißt:
- Wenn du in `worksheet.css` z. B. `--text-color` änderst,
- aber im Programm ein anderes Druckprofil gewählt ist,
- dann gewinnt meist der spätere Laufzeitwert.

Praxisregel:
- **Struktur und Feindesign** → in `worksheet.css`
- **Profile/Formatlogik** → in `app/styles/blatt_styles.py`

---

## 6) Sichere Änderungen für den Anfang

Diese Dinge kannst du fast immer gefahrlos testen:

1. Textfarbe ändern
2. Rahmen dicker/dünner machen
3. Abstände bei Aufgaben anpassen
4. Höhe der Schreiblinien verändern

### Beispiel A: Text etwas dunkler

Suche in `:root`:

```css
--text-color: #111;
```

Ändere zu:

```css
--text-color: #000;
```

### Beispiel B: Mehr Platz zwischen Aufgaben

Suche:

```css
.task {
    margin: 2em 0 0.5em 0;
}
```

Ändere zu:

```css
.task {
    margin: 2.5em 0 0.7em 0;
}
```

### Beispiel C: Schreiblinien höher

Suche:

```css
.answer.lines .line {
    height: 1.2em;
}
```

Ändere zu:

```css
.answer.lines .line {
    height: 1.4em;
}
```

---

## 7) Einheit kurz erklärt

- `px` = feste Pixel (gut für Linienbreiten)
- `em` = relativ zur Schriftgröße (gut für Abstände)
- `cm` = Zentimeter (gut für Druck, z. B. `@page`)
- `%` = relativ zum verfügbaren Platz

Für Blattwerk meist sinnvoll:
- Linien/Rahmen: `px`
- Abstände: `em`
- Seitenränder/Druckgrößen: `cm`

---

## 8) Typische Fehler und schnelle Hilfe

### Fehler: „at-rule or selector expected"

Ursache häufig:
- Tippfehler in Klammern `{}`
- Semikolon `;` vergessen
- ungültige Zeile mitten im CSS

Checkliste:
1. Hat jede Regel eine öffnende und schließende Klammer?
2. Endet jede Eigenschaft mit `;`?
3. Ist vor einer neuen Regel kein Textmüll?

### Fehler: Änderung ist nicht sichtbar

Mögliche Gründe:
- Du bearbeitest nicht die richtige Datei
- Ein Druckprofil überschreibt deinen Wert
- Du siehst noch eine alte Vorschau

Dann:
1. Datei speichern
2. Export/Vorschau neu auslösen
3. Prüfen, ob der geänderte Wert aus `:root` evtl. vom Profil überschrieben wird

---

## 9) Empfohlener Workflow (für Einsteiger)

1. Nur **eine** kleine CSS-Änderung machen
2. Speichern
3. Vorschau/Export prüfen
4. Wenn gut: nächste Änderung
5. Wenn schlecht: sofort rückgängig (`Strg+Z`)

So weißt du immer genau, welche Zeile welche Wirkung hatte.

---

## 10) Mini-Cheat-Sheet (Copy/Paste)

### Kasten-Rand ändern

```css
.material {
    border: 2px solid #999;
}
```

### Überschrift größer

```css
h1 {
    font-size: 1.8em;
}
```

### Punktefeld dichter machen

```css
:root {
    --dot-spacing: 0.4cm;
}
```

### Rasterlinie kräftiger

```css
:root {
    --grid-line-stroke: 1.3px;
}
```

---

## 11) Wenn du unsicher bist: diese Bereiche besser nicht anfassen

Als Anfänger lieber zuerst nicht ändern:
- `break-inside` / `page-break-inside`
- komplexe `background-image`-Definitionen im Rasterbereich
- `position: fixed` im Footer

Die beeinflussen Druckseiten und Layoutfluss stark.

---

## 12) Wo steht was im Code?

- Basis-Design: `assets/worksheet.css`
- Profil-/Format-Logik: `app/styles/blatt_styles.py`
- Architekturüberblick: `docs/ARCHITEKTUR.md`

---

Wenn du möchtest, kann ich dir als Nächstes eine **"Anfänger-Version" deiner aktuellen `worksheet.css` mit Abschnittskommentaren** erstellen (gleiche Funktion, nur besser lesbar).