<!--
Automatisch generiert aus app/core/markdown_conventions.py.
NICHT VON HAND BEARBEITEN.
Neu erzeugen: python tools/docs/generate_authoring_guides.py
-->

# Arbeitsblatt & Präsentation erstellen

Diese Anleitung ist die normative Referenz für den Blattwerk-Markdown-Dialekt, den Arbeitsblätter und Präsentationen gemeinsam nutzen (dieselben `:::`-Blöcke, dasselbe Frontmatter). Sie wird automatisch aus dem Code erzeugt (`app/core/markdown_conventions.py`) -- Blocktypen, Optionen und Frontmatter-Felder können hier nicht veralten, weil sie direkt aus den Konstanten stammen, die der Validator selbst zur Prüfung verwendet. Reine Stilpräferenzen (keine Korrektheitsregeln) stehen separat in [`docs/EMPFEHLUNGEN_STIL_ARBEITSBLATT_PRAESENTATION.md`](EMPFEHLUNGEN_STIL_ARBEITSBLATT_PRAESENTATION.md).

## 1. Grundidee

Ein Blattwerk-Dokument besteht aus YAML-Frontmatter (Pflicht) gefolgt von einer Folge semantischer `:::blocktyp ...` ... `:::`-Blöcke. Ob ein Dokument als Arbeitsblatt oder als Präsentation gerendert wird, entscheidet allein das Frontmatter-Feld `mode` -- der Blockdialekt selbst ist identisch. Sichtbarkeit pro Block wird über `mode=worksheet|solution` gesteuert (Standard: in beiden Ausgaben sichtbar).

**Jeder Block braucht sein eigenes `:::`, bevor der nächste Block beginnt -- Verschachtelung ist nicht erlaubt.** Das gilt uneingeschränkt auch für `columns`/`nextcol`/`endcolumns`: das sind ganz normale Blocktypen wie jeder andere, kein syntaktischer Sonderfall. Bei fehlendem Inhalt kann die Kurzform `:::blockname ... :::` (öffnendes und schließendes `:::` auf derselben Zeile) verwendet werden, z. B. `:::nextcol :::`.

## 2. Schnellstart: Arbeitsblatt

```markdown
---
document_type: worksheet
Titel: Neues Arbeitsblatt
Fach: Fach eintragen
Thema: Thema eintragen
---

:::material title="Hinweis"
Arbeite sauber und lies jede Aufgabe genau.
:::

:::task points=2 work=single action=read
Formuliere hier deine erste Aufgabe.
:::
```

## 3. Schnellstart: Präsentation

```markdown
---
document_type: presentation
mode: presentation
presentation_layout: presentation_16_9
Titel: Neue Praesentation
Fach: Fach eintragen
Thema: Thema eintragen
---

--# Einstieg
:::task title="Einstieg"
Starte hier mit der ersten Folie.
:::

--!
:::task title="Weiterfuehrung"
Fuehre hier den naechsten Gedanken aus.
:::
```

`--#` setzt den Abschnittsnamen für die Footer-Navigation, `--!` erzwingt eine neue Folie -- siehe Control-Marker-Referenz unten für alle Marker (inkl. `-+`, das im Gegensatz zu `--!` **keine** neue Folie erzeugt, siehe dortige Warnung).

### Sichtbarkeit in Präsentationen

In Präsentationen (`mode: presentation`) gibt es **keinen Lösungs-Umschalter**: Blöcke mit `mode=solution`/`show=solution` sowie `:::solution ... :::`-Blöcke (nach Blocktyp) werden in Präsentationen **immer** ausgeblendet -- unabhängig davon, ob ein Export explizit "mit Lösung" anfordert. Es gibt keine Möglichkeit, sie in einer Präsentation sichtbar zu machen. `mode=worksheet` (oder keine Angabe, Standard `both`) rendert dagegen normal. Praktisch bedeutet das: `mode=solution`/`:::solution` in einem Präsentationsdokument zu verwenden entspricht "diesen Block dauerhaft verstecken", nicht "Lösungsansicht anbieten".

## 4. Frontmatter-Referenz

| Feld | Pflicht | Art | Erlaubte Werte | Geprüft? |
|---|---|---|---|---|
| `Titel` | ja | Text | -- | ja |
| `Fach` | ja | Text | -- | ja |
| `Thema` | ja | Text | -- | ja |
| `mode` | nein | enum | `presentation`, `solution`, `test`, `worksheet`, `ws` | ja |
| `presentation_layout` | nein | enum | `presentation_16_10`, `presentation_16_9`, `presentation_4_3` | ja |
| `presentation_show_mini_header` | nein | boolean | `0`, `1`, `falsch`, `false`, `ja`, `nein`, `no`, `off`, `on`, `true`, `wahr`, `yes` | ja |
| `presentation_show_section_footer` | nein | boolean | `0`, `1`, `falsch`, `false`, `ja`, `nein`, `no`, `off`, `on`, `true`, `wahr`, `yes` | ja |
| `tag` | nein | scalar_nonempty | -- | ja |
| `show_student_header` | nein | boolean | `0`, `1`, `false`, `j`, `ja`, `n`, `nein`, `no`, `off`, `on`, `true`, `yes` | ja |
| `show_document_header` | nein | boolean | `0`, `1`, `false`, `j`, `ja`, `n`, `nein`, `no`, `off`, `on`, `true`, `yes` | ja |
| `document_type` | nein | enum | `kurzentwurf`, `presentation`, `worksheet` | nein |
| `lochen` | nein | boolean | `0`, `1`, `false`, `j`, `ja`, `n`, `nein`, `no`, `off`, `on`, `true`, `yes` | nein |
| `copyright` | nein | free_text | -- | nein |
| `Stufe` | nein | free_text | -- | nein |
| `worksheet_type` | nein | free_text | -- | nein |
| `font_profile` | nein | free_text | -- | nein |

- **`Titel`** (Pflichtfeld): Der Titel des Dokuments, erscheint im Dokumentkopf und in der Fensterleiste.
- **`Fach`** (Pflichtfeld): Das Unterrichtsfach, erscheint zusammen mit `Thema` in der Metazeile des Dokumentkopfs.
- **`Thema`** (Pflichtfeld): Das konkrete Unterrichtsthema, erscheint zusammen mit `Fach` in der Metazeile des Dokumentkopfs.
- **`mode`** (optional): Steuert das grundlegende Ausgabeverhalten des Dokuments. `worksheet` (Standard, Alias `ws`) zeigt normale Arbeitsblatt-Ausgabe; `solution` rendert global die Lösungsansicht; `presentation` schaltet auf Folienausgabe mit Mini-Header und Folienzähler um; `test` blendet in Aufgaben/Teilaufgaben nur die Arbeitsform-Hinweise (Emoji + Label) aus.
- **`presentation_layout`** (optional): Wählt das Seitenverhältnis der Folien bei `mode: presentation` (`presentation_16_9`, `presentation_16_10` oder `presentation_4_3`). Ohne `mode: presentation` ohne Wirkung.
- **`presentation_show_mini_header`** (optional): Blendet in Präsentationen den kleinen Kopfbereich pro Folie (Phasenübersicht) ein/aus. Standard: an.
- **`presentation_show_section_footer`** (optional): Blendet in Präsentationen den Abschnittsfooter (Folienzähler) pro Folie ein/aus. Standard: an.
- **`tag`** (optional): Freier Kurzbezeichner, der z. B. als Präfix für automatisch generierte Lernhilfe-Label verwendet werden kann (siehe `help`/`hilfe`-Block-Option `tag`). Muss ein einfacher, nicht-leerer Textwert sein -- kein YAML-Mapping oder -Liste.
- **`show_student_header`** (optional): Blendet die Schülerkopfzeile (Name/Lerngruppe/Datum-Felder) am Dokumentanfang ein/aus. Standard: aus. Erwartet einen booleschen Wert im Format `ja`/`nein` (auch `true`/`false`, `1`/`0`, `j`/`n` werden akzeptiert).
- **`show_document_header`** (optional): Blendet den Dokumentkopf (Titel, Fach/Thema-Metazeile) ein/aus. Standard: an. Erwartet denselben booleschen Werttyp wie `show_student_header`.
- **`document_type`** (optional): Markiert den Dokumenttyp explizit (`worksheet`, `presentation` oder `kurzentwurf`) statt ihn aus anderen Feldern zu erraten. Wird von Blattwerk beim Anlegen neuer Dokumente automatisch gesetzt; von Hand meist nicht nötig. Aktuell nicht durch den Markdown-Validator wertgeprüft.
- **`lochen`** (optional): Aktiviert einen vergrößerten linken Rand für Lochung beim Ausdrucken (`ja`/`nein`, Standard: `nein`). Aktuell nicht durch den Markdown-Validator wertgeprüft; ungültige Werte werden beim Rendern stillschweigend als `nein` behandelt.
- **`copyright`** (optional): Ersetzt den Standard-Copyright-Text im Footer durch einen eigenen Text. Ohne dieses Feld wird automatisch ein Standardtext mit aktuellem Jahr eingesetzt.
- **`Stufe`** (optional): Rein informatives Feld für die Jahrgangsstufe. **Hinweis:** wird aktuell an keiner Stelle aus dem Dokument gelesen oder angezeigt -- ohne Wirkung im Build-/Render-Pfad.
- **`worksheet_type`** (optional): Rein informatives Feld für eine Dokumentart-Bezeichnung. **Hinweis:** wird aktuell an keiner Stelle aus dem Dokument gelesen oder angezeigt -- ohne Wirkung im Build-/Render-Pfad.
- **`font_profile`** (optional): **Hinweis:** wird aktuell nicht aus dem Dokument gelesen -- die Schriftart wird ausschließlich über die App-Einstellung gesteuert, nicht über das Frontmatter. Dieses Feld hat aktuell keine Wirkung im Build-/Render-Pfad.

## 5. Blockreferenz

### `cloze`

Lückentext-Antwortfeld. `gap`/`gap_length` steuert den Lückenmodus/-länge, `words`/`words_multi` die Wortbank-Optionen, `layout` das Layout der Wortbank-Position.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `align` | Enum | `b`, `block`, `blocksatz`, `c`, `center`, `centre`, `j`, `justify`, `l`, `left`, `links`, `linksbuendig`, `linksbundig`, `m`, `middle`, `mitte`, `r`, `rechts`, `rechtsbuendig`, `rechtsbundig`, `right`, `zentriert` | ja | -- | Horizontale Ausrichtung des Blockinhalts: `left`/`links`, `right`/`rechts`, `center`/`mitte`/`zentriert` oder `block`/`blocksatz` (deutsche und englische Schreibweisen gleichwertig). |
| `gap` | Enum | `approx`, `equal`, `fixed`, `gleich`, `same`, `uniform` | nein | `approx` | Lückenlängen-Modus: `fixed`/`equal`/`same`/`uniform`/`gleich` erzwingt gleich lange Lücken, jeder andere Wert (Standard) berechnet die Lückenlänge approximativ aus der Wortlänge. |
| `gap_length` | Ganzzahl | -- | nein | `10` | Feste Lückenlänge in Zeichen bei `gap=fixed` (Standard `10`). |
| `layout` | Text | -- | nein | -- | Steuert ein Layout-Detail des Blocks -- die genaue Bedeutung ist blocktyp-abhängig, siehe Besonderheit unten. |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |
| `words` | Text | -- | nein | -- | Blocktyp-abhängige Bedeutung, siehe Besonderheit unten. *Besonderheit bei `cloze`:* Position der Wortbank relativ zum Lückentext -- nicht die Lückenwörter selbst (die stehen im Blockinhalt). |
| `words_multi` | Bool | -- | nein | `True` | Erlaubt Mehrfachauswahl in der Wortbank (Standard: an). |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::cloze gap=fixed words=below
Text mit {{Lücke}} hier.
:::
```

### `columns`

Spaltenlayout für nebeneinander angeordnete Inhalte. `cols=2..6` (Standard 2) setzt die Spaltenzahl, `widths`/`ratio` die relativen Breiten, `gap=<css-länge>` den Spaltenabstand. Muss mit `:::nextcol` (Spaltenwechsel) und `:::endcolumns` (Ende) strukturiert werden.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `align` | Enum | `b`, `block`, `blocksatz`, `c`, `center`, `centre`, `j`, `justify`, `l`, `left`, `links`, `linksbuendig`, `linksbundig`, `m`, `middle`, `mitte`, `r`, `rechts`, `rechtsbuendig`, `rechtsbundig`, `right`, `zentriert` | ja | -- | Horizontale Ausrichtung des Blockinhalts: `left`/`links`, `right`/`rechts`, `center`/`mitte`/`zentriert` oder `block`/`blocksatz` (deutsche und englische Schreibweisen gleichwertig). |
| `cols` | Ganzzahl | -- | nein | `2` | Anzahl Spalten des Rasters. Der genaue Standardwert und ob eine fehlende Angabe automatisch aus verfügbarer Breite berechnet wird, hängt vom Blocktyp ab (siehe Tabelle: Spalte "Standard"). |
| `gap` | CSS-Länge | -- | nein | -- | Horizontaler Abstand zwischen den Spalten als CSS-Länge (z. B. `1cm`). |
| `ratio` | Text | -- | nein | -- | Alias von `widths` -- relative Spaltengewichte. |
| `widths` | Text | -- | nein | -- | Relative Breiten (Gewichte, z. B. `"2 1"`) oder feste CSS-Breiten für die Spalten/Elemente dieses Blocks. |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::columns cols=2 widths="1 1" :::

:::nextcol :::

:::endcolumns :::
```

### `crossword`

Kreuzworträtsel-Antwortfeld. Der Inhalt ist eine YAML-Liste unter `words:` mit je `word`/`clue` (bzw. `lösung`/`hinweis`) pro Rätselwort; die Wörter werden automatisch so platziert, dass sie sich möglichst oft kreuzen. `maxw`/`maxh` begrenzen die Rastergröße (Standard: aus der Seitenbreite/-höhe abgeleitet), `prefill` gibt die Anzahl zufällig vorausgefüllter Buchstaben an, `position` steuert, ob die Hinweisliste links/rechts/unterhalb des Rasters steht (Standard `auto`). Optional `code` (ein frei gewähltes Lösungswort ohne eigenen Hinweis, das sich aus Buchstaben der platzierten Wörter zusammensetzen lassen muss) und `code_row=true` (das Codewort läuft als eigene Zeile, alle anderen Wörter kreuzen es senkrecht).

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `align` | Enum | `b`, `block`, `blocksatz`, `c`, `center`, `centre`, `j`, `justify`, `l`, `left`, `links`, `linksbuendig`, `linksbundig`, `m`, `middle`, `mitte`, `r`, `rechts`, `rechtsbuendig`, `rechtsbundig`, `right`, `zentriert` | ja | -- | Horizontale Ausrichtung des Blockinhalts: `left`/`links`, `right`/`rechts`, `center`/`mitte`/`zentriert` oder `block`/`blocksatz` (deutsche und englische Schreibweisen gleichwertig). |
| `code` | Text | -- | nein | -- | Frei gewähltes Lösungscodewort ohne eigenen Hinweis in der Liste; muss sich aus Buchstaben der platzierten Rätselwörter zusammensetzen lassen. |
| `code_row` | Bool | -- | nein | `False` | Wenn aktiv, läuft `code` als eigene waagerechte Zeile, die alle anderen Wörter senkrecht kreuzen müssen (Standard: aus). |
| `maxh` | Ganzzahl | -- | nein | -- | Maximale Zeilenzahl des Rätselrasters (Standard: aus der Seitenhöhe abgeleitet). |
| `maxw` | Ganzzahl | -- | nein | -- | Maximale Spaltenzahl des Rätselrasters (Standard: aus der Seitenbreite abgeleitet). |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `position` | Enum | `auto`, `below`, `left`, `right` | ja | `auto` | Position der Hinweisliste relativ zum Raster: `left`/`right`/`below`/`auto` (Standard `auto` -- rechts, wenn genug Platz ist, sonst darunter). |
| `prefill` | Ganzzahl | -- | nein | `0` | Anzahl zufällig vorausgefüllter Buchstaben im Arbeitsblatt-Modus (Standard `0`). |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |

### `dots`

Punktraster-Schreibfeld (z. B. für Übungen zur Feinmotorik/Schrift).

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `align` | Enum | `b`, `block`, `blocksatz`, `c`, `center`, `centre`, `j`, `justify`, `l`, `left`, `links`, `linksbuendig`, `linksbundig`, `m`, `middle`, `mitte`, `r`, `rechts`, `rechtsbuendig`, `rechtsbundig`, `right`, `zentriert` | ja | -- | Horizontale Ausrichtung des Blockinhalts: `left`/`links`, `right`/`rechts`, `center`/`mitte`/`zentriert` oder `block`/`blocksatz` (deutsche und englische Schreibweisen gleichwertig). |
| `height` | CSS-Länge | -- | nein | `4cm` | Höhe des Antwortfelds als CSS-Länge (z. B. `4cm`, `120px`). Der genaue Standardwert hängt vom Blocktyp ab (siehe Tabelle: Spalte "Standard"). |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::dots height=4cm

:::
```

### `endcolumns`

Schließt einen `:::columns`-Block ab. Keine eigenen Optionen.

Keine Optionen.

### `framebreak`

Erzeugt im Präsentationsmodus einen neuen Frame mit dem bisherigen plus neuem Inhalt -- siehe Control-Marker `-+`.

Keine Optionen.

### `geometry`

Koordinatensystem für Punkte, Polylinien, Strecken und Funktionsgraphen (siehe Geometry-Abschnitt unten für die YAML-Payload-Struktur). `axis=true` aktiviert echte Achsen mit `origin`/`step_x`/`step_y` zur Umrechnung mathematischer Koordinaten in Rasterzellen; `axis_label_x`/`axis_label_y` beschriften die Achsen (Standard `x`/`y`).

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `align` | Enum | `b`, `block`, `blocksatz`, `c`, `center`, `centre`, `j`, `justify`, `l`, `left`, `links`, `linksbuendig`, `linksbundig`, `m`, `middle`, `mitte`, `r`, `rechts`, `rechtsbuendig`, `rechtsbundig`, `right`, `zentriert` | ja | -- | Horizontale Ausrichtung des Blockinhalts: `left`/`links`, `right`/`rechts`, `center`/`mitte`/`zentriert` oder `block`/`blocksatz` (deutsche und englische Schreibweisen gleichwertig). |
| `axis` | Bool | -- | nein | `False` | Aktiviert ein mathematisches Koordinatensystem mit x-/y-Achse, Tick-Marks und Achsenbeschriftung (Standard: aus, dann gelten reine Rasterkoordinaten `col`/`row`). **Wichtig:** `axis=true` wirkt nur zusammen mit einem gültigen `origin` -- fehlt `origin` oder ist er ungültig, fällt der Block still (ohne Fehler/Warnung) auf den Rasterkoordinaten-Modus zurück. In diesem Fall werden `functions`-Einträge komplett ignoriert, und `points`/`pairs` interpretieren ihre `x`/`y`-Werte als `col`/`row` statt als Mathe-Koordinaten. |
| `axis_label_x` | Text | -- | nein | `x` | Beschriftung der x-Achse (Standard `x`), nur wirksam bei aktivem Achsenmodus (siehe `axis`). |
| `axis_label_y` | Text | -- | nein | `y` | Beschriftung der y-Achse (Standard `y`), nur wirksam bei aktivem Achsenmodus (siehe `axis`). |
| `cols` | Ganzzahl | -- | nein | `20` | Anzahl Spalten des Rasters. Der genaue Standardwert und ob eine fehlende Angabe automatisch aus verfügbarer Breite berechnet wird, hängt vom Blocktyp ab (siehe Tabelle: Spalte "Standard"). |
| `line` | Enum | `dashed`, `solid` | ja | `solid` | Linienstil des Rasterhintergrunds: `solid` (Standard) oder `dashed`. Nur bei `:::grid`/`:::geometry` vorhanden -- nicht zu verwechseln mit dem gleichnamigen `pairs[].line`-Feld in der Geometry-YAML-Payload (dort eigene, unabhängige Einstellung pro Strecke). |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `origin` | Text | -- | nein | -- | Ursprung des Koordinatensystems im Raster, Format `"spalte,zeile"` (z. B. `"10,10"`). **Pflicht, sobald `axis=true` gesetzt ist** -- ohne (oder mit ungültigem) `origin` bleibt der Achsenmodus trotz `axis=true` inaktiv, siehe Besonderheit dort. |
| `rows` | Ganzzahl | -- | nein | `5` | Anzahl Zeilen des Rasters/der Linien. Der genaue Standardwert und ob eine fehlende Angabe automatisch berechnet wird, hängt vom Blocktyp ab (siehe Tabelle: Spalte "Standard"). |
| `scale` | CSS-Länge | -- | nein | `0.5cm` | Zellgröße des Rasters als CSS-Länge (Standard `0.5cm`), z. B. `scale=0.4cm` oder `scale=6mm`. |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |
| `step_x` | Zahl | -- | nein | `1.0` | Skalierung zwischen mathematischer x-Koordinate und Rasterzellen (Standard `1`), nur bei `axis=true`. |
| `step_y` | Zahl | -- | nein | `1.0` | Skalierung zwischen mathematischer y-Koordinate und Rasterzellen (Standard `1`), nur bei `axis=true`. |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::geometry scale=0.5cm axis=true origin="10,10"
points:
  - {x: 0, y: 0, label: "A", show: "&"}
:::
```

### `grid`

Kästchen-/Schreibfeld mit einem Textraster. `rows`/`cols` setzen die Rastergröße (ohne `cols` wird die Spaltenzahl automatisch aus verfügbarer Breite und `scale` berechnet), `scale=<css-länge>` die Zellgröße (Standard `0.5cm`). `line=solid|dashed` steuert den Linienstil des Rasters. Marker-/Inline-Text wird wie bei `lines` nach Arbeitsblatt/Lösung gefiltert.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `align` | Enum | `b`, `block`, `blocksatz`, `c`, `center`, `centre`, `j`, `justify`, `l`, `left`, `links`, `linksbuendig`, `linksbundig`, `m`, `middle`, `mitte`, `r`, `rechts`, `rechtsbuendig`, `rechtsbundig`, `right`, `zentriert` | ja | -- | Horizontale Ausrichtung des Blockinhalts: `left`/`links`, `right`/`rechts`, `center`/`mitte`/`zentriert` oder `block`/`blocksatz` (deutsche und englische Schreibweisen gleichwertig). |
| `cols` | Ganzzahl | -- | nein | -- | Anzahl Spalten des Rasters. Der genaue Standardwert und ob eine fehlende Angabe automatisch aus verfügbarer Breite berechnet wird, hängt vom Blocktyp ab (siehe Tabelle: Spalte "Standard"). |
| `line` | Enum | `dashed`, `solid` | ja | `solid` | Linienstil des Rasterhintergrunds: `solid` (Standard) oder `dashed`. Nur bei `:::grid`/`:::geometry` vorhanden -- nicht zu verwechseln mit dem gleichnamigen `pairs[].line`-Feld in der Geometry-YAML-Payload (dort eigene, unabhängige Einstellung pro Strecke). |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `rows` | Ganzzahl | -- | nein | `5` | Anzahl Zeilen des Rasters/der Linien. Der genaue Standardwert und ob eine fehlende Angabe automatisch berechnet wird, hängt vom Blocktyp ab (siehe Tabelle: Spalte "Standard"). |
| `scale` | CSS-Länge | -- | nein | `0.5cm` | Zellgröße des Rasters als CSS-Länge (Standard `0.5cm`), z. B. `scale=0.4cm` oder `scale=6mm`. |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::grid scale=0.5cm

:::
```

### `help`

Separate Hilfekarte (eigene Ausgabe, nicht Teil des normalen Arbeitsblatts). `level` (1-99) gruppiert Hilfen nach Schwierigkeitsstufe, `tag` beeinflusst die automatische Beschriftung (z. B. `1A`, `1B`), `title` überschreibt den Standardtitel "Hilfe". Kanonischer Blockname; `hilfe` ist ein dokumentierter Alias mit identischen Optionen.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `level` | Ganzzahl | -- | nein | -- | Schwierigkeitsstufe der Hilfekarte (1-99) -- rein organisatorisch, ohne Einfluss auf Sichtbarkeit oder Reihenfolge. |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |
| `tag` | Text | -- | nein | -- | Beeinflusst die automatische Beschriftung mehrerer Hilfekarten zum selben Bezugspunkt (z. B. `tag=1` erzeugt `1A`, `1B`, ...; ein einzelner Buchstabe erzeugt `1<tag>`, `2<tag>`, ...). |
| `title` | Text | -- | nein | -- | Überschreibt die automatisch erzeugte Standardbeschriftung des Blocks mit einem eigenen Text. |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::help title="Hilfe" level=1
Hilfetext hier…
:::
```

### `hilfe`

Dokumentierter Alias für `help` -- identische Optionen und Bedeutung, nur andere Schreibweise.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `level` | Ganzzahl | -- | nein | -- | Schwierigkeitsstufe der Hilfekarte (1-99) -- rein organisatorisch, ohne Einfluss auf Sichtbarkeit oder Reihenfolge. |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |
| `tag` | Text | -- | nein | -- | Beeinflusst die automatische Beschriftung mehrerer Hilfekarten zum selben Bezugspunkt (z. B. `tag=1` erzeugt `1A`, `1B`, ...; ein einzelner Buchstabe erzeugt `1<tag>`, `2<tag>`, ...). |
| `title` | Text | -- | nein | -- | Überschreibt die automatisch erzeugte Standardbeschriftung des Blocks mit einem eigenen Text. |

### `info`

Hinweisbox mit `type=default|warning|note` für unterschiedliche Hervorhebungsstile.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `align` | Enum | `b`, `block`, `blocksatz`, `c`, `center`, `centre`, `j`, `justify`, `l`, `left`, `links`, `linksbuendig`, `linksbundig`, `m`, `middle`, `mitte`, `r`, `rechts`, `rechtsbuendig`, `rechtsbundig`, `right`, `zentriert` | ja | -- | Horizontale Ausrichtung des Blockinhalts: `left`/`links`, `right`/`rechts`, `center`/`mitte`/`zentriert` oder `block`/`blocksatz` (deutsche und englische Schreibweisen gleichwertig). |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |
| `type` | Enum | `default`, `note`, `warning` | ja | `default` | Hervorhebungsstil der Hinweisbox: `default` (Standard), `warning` oder `note`. |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::info type=tip
Hinweis hier…
:::
```

### `lines`

Textbasiertes Antwortfeld mit Linien zum Beschriften. `rows=<n>` setzt die Mindestanzahl sichtbarer Linien (Standard 3); die tatsächliche Anzahl ist `max(rows, sichtbare Inhaltszeilen)`. `height=<css-länge>` steuert die Linienhöhe. Markdown ist im Inhalt erlaubt; `§`/`%`/`&`-Zeilenmarker (bzw. `§{...}`/`%{...}`/`&{...}` inline) steuern, ob eine Zeile nur im Arbeitsblatt, nur in der Lösung oder in beiden erscheint.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `align` | Enum | `b`, `block`, `blocksatz`, `c`, `center`, `centre`, `j`, `justify`, `l`, `left`, `links`, `linksbuendig`, `linksbundig`, `m`, `middle`, `mitte`, `r`, `rechts`, `rechtsbuendig`, `rechtsbundig`, `right`, `zentriert` | ja | -- | Horizontale Ausrichtung des Blockinhalts: `left`/`links`, `right`/`rechts`, `center`/`mitte`/`zentriert` oder `block`/`blocksatz` (deutsche und englische Schreibweisen gleichwertig). |
| `height` | CSS-Länge | -- | nein | -- | Höhe des Antwortfelds als CSS-Länge (z. B. `4cm`, `120px`). Der genaue Standardwert hängt vom Blocktyp ab (siehe Tabelle: Spalte "Standard"). |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `rows` | Ganzzahl | -- | nein | `3` | Anzahl Zeilen des Rasters/der Linien. Der genaue Standardwert und ob eine fehlende Angabe automatisch berechnet wird, hängt vom Blocktyp ab (siehe Tabelle: Spalte "Standard"). |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::lines rows=3

:::
```

### `matching`

Zuordnungs-Antwortfeld (YAML-only) mit zwei Seiten (`left`/`right` oder `top`/`bottom`, je nach `layout`/`orientation`) und den Verbindungen in `matches`. `worksheet_matches` zeigt optional Beispielverbindungen bereits im Arbeitsblatt. `height_mode=content|uniform`, `lane_align` und `show_guides` steuern das Layout; ein Seiten-Verhältnis von genau einem Element (1↔N) löst die Warnung `MA001` aus.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `align` | Enum | `center` | nein | `center` | Bei `matching` deutlich enger als die generische `align`-Option: einziger unterstützter Wert ist `center` (Standard) -- zentriert Inhalte in den Zuordnungs-Blöcken horizontal und vertikal. Andere Werte werden aktuell nicht geprüft. |
| `bottom` | Text | -- | nein | -- | Untere-Seite-Einträge bei vertikalem Layout, `|`-getrennt. |
| `height_mode` | Enum | `content`, `uniform` | nein | `content` | `content` (Standard) richtet jeden Block nach eigenem Inhalt aus; `uniform` macht alle Blöcke gleich hoch. |
| `lane_align` | Enum | `center`, `end`, `start` | nein | `center` | Richtet beide Seiten entlang ihrer gemeinsamen Mittelachse aus: `start`, `center` (Standard) oder `end`. |
| `layout` | Text | -- | nein | -- | Steuert ein Layout-Detail des Blocks -- die genaue Bedeutung ist blocktyp-abhängig, siehe Besonderheit unten. *Besonderheit bei `matching`:* Legt fest, ob die beiden Seiten horizontal (`left`/`right`) oder vertikal (`top`/`bottom`) angeordnet werden. |
| `left` | Text | -- | nein | -- | Linke-Seite-Einträge bei horizontalem Layout, `|`-getrennt. |
| `links` | Text | -- | nein | -- | Alias von `left`. |
| `matches` | Text | -- | nein | -- | Definiert die korrekten Verbindungen zwischen beiden Seiten. |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `orientation` | Text | -- | nein | -- | Alias von `layout`. |
| `right` | Text | -- | nein | -- | Rechte-Seite-Einträge bei horizontalem Layout, `|`-getrennt. |
| `scale` | CSS-Länge | -- | nein | `0.5cm` | Zellgröße des Rasters als CSS-Länge (Standard `0.5cm`), z. B. `scale=0.4cm` oder `scale=6mm`. |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |
| `show_guides` | Bool | -- | nein | `False` | Blendet gestrichelte Platzhalterblöcke und Canvas-Rand ein (Standard: aus). |
| `top` | Text | -- | nein | -- | Obere-Seite-Einträge bei vertikalem Layout, `|`-getrennt. |
| `worksheet_matches` | Text | -- | nein | -- | Zeigt zusätzlich Beispielverbindungen bereits im Arbeitsblatt (nicht nur in der Lösung). |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::matching layout=horizontal height_mode=uniform lane_align=center show_guides=false
left:
  - "Begriff A"
  - "Begriff B"
right:
  - "Erklärung A"
  - "Erklärung B"
matches:
  - "1-1"
  - "2-2"
:::
```

### `material`

Kontext- und Erklärmaterial, das vor einer Aufgabe eingeblendet wird. Optionale `title` beschriftet die Box.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `align` | Enum | `b`, `block`, `blocksatz`, `c`, `center`, `centre`, `j`, `justify`, `l`, `left`, `links`, `linksbuendig`, `linksbundig`, `m`, `middle`, `mitte`, `r`, `rechts`, `rechtsbuendig`, `rechtsbundig`, `right`, `zentriert` | ja | -- | Horizontale Ausrichtung des Blockinhalts: `left`/`links`, `right`/`rechts`, `center`/`mitte`/`zentriert` oder `block`/`blocksatz` (deutsche und englische Schreibweisen gleichwertig). |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |
| `title` | Text | -- | nein | -- | Überschreibt die automatisch erzeugte Standardbeschriftung des Blocks mit einem eigenen Text. |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::material title="Titel"
Inhalt hier…
:::
```

### `mc`

Multiple-Choice-/Wahr-Falsch-Antwortfeld. **Primärer Weg:** die Antwortmöglichkeiten stehen als Markdown-Checkbox-Liste im Blockinhalt (`- [x] Richtige Antwort`, `- [ ] Falsche Antwort`) -- siehe Beispiel unten. `tf`/`true_false` schaltet auf Wahr-Falsch-Layout um, `inline` und `widths` steuern das Layout. Die Header-Optionen `options=`/`correct=` sind ein **Fallback**, der nur greift, wenn der Blockinhalt keine Checkbox-Liste enthält (siehe deren Erklärungen unten) -- für neue Dokumente die Checkbox-Liste bevorzugen.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `align` | Enum | `b`, `block`, `blocksatz`, `c`, `center`, `centre`, `j`, `justify`, `l`, `left`, `links`, `linksbuendig`, `linksbundig`, `m`, `middle`, `mitte`, `r`, `rechts`, `rechtsbuendig`, `rechtsbundig`, `right`, `zentriert` | ja | -- | Horizontale Ausrichtung des Blockinhalts: `left`/`links`, `right`/`rechts`, `center`/`mitte`/`zentriert` oder `block`/`blocksatz` (deutsche und englische Schreibweisen gleichwertig). |
| `correct` | Text | -- | nein | -- | **Nur relevant im Fallback-Modus** (kein `- [x]`/`- [ ]` im Blockinhalt): 1-basierter Index bzw. `|`-getrennte Indexliste der richtigen Antwortoption(en) aus `options=`. Im Wahr-Falsch-Modus (`tf`) stattdessen einfach `true`/`false` (welche Seite richtig ist). |
| `inline` | Bool | -- | nein | `False` | Schaltet auf ein kompaktes, horizontal fließendes Layout der Antwortoptionen um (Standard: aus). |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `options` | Text | -- | nein | -- | **Nur relevant im Fallback-Modus** (kein `- [x]`/`- [ ]` im Blockinhalt): `|`-getrennte Liste der Antwortmöglichkeiten als Header-Option, Alternative zur primären Checkbox-Liste im Blockinhalt. |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |
| `tf` | Bool | -- | nein | `False` | Schaltet auf Wahr-Falsch-Layout um (akzeptiert u. a. `1`/`true`/`yes`/`on`/`tf`/`richtigfalsch`/`richtig_false` als "an"; Standard: aus). |
| `true_false` | Bool | -- | nein | `False` | Alias von `tf`. |
| `widths` | Text | -- | nein | -- | Relative Breiten (Gewichte, z. B. `"2 1"`) oder feste CSS-Breiten für die Spalten/Elemente dieses Blocks. |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::mc inline=true
Frage oder Einleitung…
- [x] Richtige Antwort
- [ ] Falsche Antwort A
- [ ] Falsche Antwort B
:::
```

### `nextcol`

Spaltenwechsel innerhalb eines `:::columns`-Blocks. Keine eigenen Optionen.

Keine Optionen.

### `numberline`

Zahlenstrahl-Antwortfeld mit YAML-Payload (`labels`/`answers`/`arcs`/... je Element mit `show: "§"|"%"|"&"` für Sichtbarkeit). Optionen wie `min`/`max`, `tick_step`, `major_every` und `positive_sign` steuern Wertebereich und Beschriftung.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `align` | Enum | `b`, `block`, `blocksatz`, `c`, `center`, `centre`, `j`, `justify`, `l`, `left`, `links`, `linksbuendig`, `linksbundig`, `m`, `middle`, `mitte`, `r`, `rechts`, `rechtsbuendig`, `rechtsbundig`, `right`, `zentriert` | ja | -- | Horizontale Ausrichtung des Blockinhalts: `left`/`links`, `right`/`rechts`, `center`/`mitte`/`zentriert` oder `block`/`blocksatz` (deutsche und englische Schreibweisen gleichwertig). |
| `full_width` | Bool | -- | nein | -- | Erzwingt volle verfügbare Breite für den Zahlenstrahl. |
| `height` | CSS-Länge | -- | nein | `2.7cm` | Höhe des Antwortfelds als CSS-Länge (z. B. `4cm`, `120px`). Der genaue Standardwert hängt vom Blocktyp ab (siehe Tabelle: Spalte "Standard"). |
| `major_every` | Ganzzahl | -- | nein | `0` | Jede n-te Tick-Marke wird als Hauptmarkierung hervorgehoben. |
| `max` | Zahl | -- | nein | -- | Obere Grenze des dargestellten Zahlenbereichs. |
| `max_width_cm` | Zahl | -- | nein | -- | Maximale Darstellungsbreite des Zahlenstrahls in Zentimetern. |
| `max_width_mm` | Zahl | -- | nein | -- | Maximale Darstellungsbreite des Zahlenstrahls in Millimetern. |
| `maximum` | Zahl | -- | nein | -- | Alias von `max`. |
| `min` | Zahl | -- | nein | -- | Untere Grenze des dargestellten Zahlenbereichs. |
| `minimum` | Zahl | -- | nein | -- | Alias von `min`. |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `positive_sign` | Bool | -- | nein | -- | Zeigt bei positiven Zahlen explizit ein `+`-Vorzeichen an (Standard: aus). |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |
| `signed_positive` | Bool | -- | nein | -- | Alias von `positive_sign`. |
| `tick_spacing` | Zahl | -- | nein | -- | Physischer Abstand zwischen Tick-Marken (Einheit im Wert enthalten). |
| `tick_spacing_cm` | Zahl | -- | nein | -- | Physischer Abstand zwischen Tick-Marken in Zentimetern. |
| `tick_spacing_mm` | Zahl | -- | nein | -- | Physischer Abstand zwischen Tick-Marken in Millimetern. |
| `tick_step` | Zahl | -- | nein | -- | Abstand zwischen zwei Tick-Marken in Zahlenraum-Einheiten. |
| `ticks` | Text | -- | nein | -- | Explizite Liste anzuzeigender Tick-Werte. |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::numberline min=0 max=10 tick_step=1 major_every=5 height=2cm
labels:
  - {value: 0, show: "&"}
  - {value: 10, show: "&"}
answers:
  - {value: 5}
:::
```

### `pagebreak`

Erzwingt einen harten Seiten-/Folienumbruch -- siehe Control-Marker `--!`.

Keine Optionen.

### `qrcode`

Klickbarer QR-Code-Link. `url` ist Pflicht (http/https-Link oder relativer Pfad ohne Leerzeichen). Größenoptionen `w`/`h`/`maxw` (auch `width`/`height`/`max-width`) folgen derselben CSS-Größen-Logik wie Markdown-Bilder (z. B. `3cm`, `120px`, `60%`, `auto`).

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `align` | Enum | `b`, `block`, `blocksatz`, `c`, `center`, `centre`, `j`, `justify`, `l`, `left`, `links`, `linksbuendig`, `linksbundig`, `m`, `middle`, `mitte`, `r`, `rechts`, `rechtsbuendig`, `rechtsbundig`, `right`, `zentriert` | ja | -- | Horizontale Ausrichtung des Blockinhalts: `left`/`links`, `right`/`rechts`, `center`/`mitte`/`zentriert` oder `block`/`blocksatz` (deutsche und englische Schreibweisen gleichwertig). |
| `alignment` | Enum | `b`, `block`, `blocksatz`, `c`, `center`, `centre`, `j`, `justify`, `l`, `left`, `links`, `linksbuendig`, `linksbundig`, `m`, `middle`, `mitte`, `r`, `rechts`, `rechtsbuendig`, `rechtsbundig`, `right`, `zentriert` | ja | -- | Alias von `align` bei `qrcode` -- identische generische Objekt-Ausrichtung (`left|right|center|block`), nur andere Schreibweise. |
| `h` | CSS-Länge | -- | ja | -- | Höhe des QR-Codes als CSS-Größe, gleiche Regeln wie `w`. |
| `height` | CSS-Länge | -- | ja | -- | Alias von `h` -- Höhe des QR-Codes, folgt derselben CSS-Größen-Logik wie Bildgrößen in Markdown (z. B. `3cm`, `120px`, `60%`, `auto`); ungültige Werte werden als `OP002` gemeldet. |
| `max-width` | CSS-Länge | -- | ja | -- | Alias von `maxw`. |
| `maxw` | CSS-Länge | -- | ja | -- | Maximale Breite des QR-Codes als CSS-Größe, gleiche Regeln wie `w`. |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |
| `url` | URL | -- | ja | -- | Pflichtoption: Ziel-Link des QR-Codes (http/https-URL oder relativer Pfad ohne Leerzeichen). Ungültige Werte werden als `QR002` gemeldet, ein fehlender Wert als `QR001`. |
| `w` | CSS-Länge | -- | ja | -- | Breite des QR-Codes als CSS-Größe (z. B. `3cm`, `120px`, `60%`, `auto`); ungültige Werte werden als `OP002` gemeldet. |
| `width` | CSS-Länge | -- | ja | -- | Alias von `w` -- Breite des QR-Codes, siehe `height`/`w`/`h`/`maxw`. |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::qrcode url=https://example.org w=3cm h=3cm maxw=45% :::
```

### `sectionmark`

Setzt den aktuellen Abschnittsnamen für die Präsentations-Footer-Navigation -- siehe Control-Marker `--#`.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `title` | Text | -- | nein | -- | Überschreibt die automatisch erzeugte Standardbeschriftung des Blocks mit einem eigenen Text. |

### `slidechromeoff`

Blendet Mini-Header/Footer auf der aktuellen Folie aus -- siehe Control-Marker `--hf`.

Keine Optionen.

### `solution`

Musterlösungstext. `label=true|false` (Standard `true`) blendet das Label "Lösung" ein/aus.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `align` | Enum | `b`, `block`, `blocksatz`, `c`, `center`, `centre`, `j`, `justify`, `l`, `left`, `links`, `linksbuendig`, `linksbundig`, `m`, `middle`, `mitte`, `r`, `rechts`, `rechtsbuendig`, `rechtsbundig`, `right`, `zentriert` | ja | -- | Horizontale Ausrichtung des Blockinhalts: `left`/`links`, `right`/`rechts`, `center`/`mitte`/`zentriert` oder `block`/`blocksatz` (deutsche und englische Schreibweisen gleichwertig). |
| `label` | Bool | -- | nein | `True` | Blendet das Label "Lösung" vor dem Text ein/aus (Standard: an). |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::solution
Musterlösung hier…
:::
```

### `space`

Freier Leerraum ohne Linien/Raster, z. B. für Zeichnungen.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `align` | Enum | `b`, `block`, `blocksatz`, `c`, `center`, `centre`, `j`, `justify`, `l`, `left`, `links`, `linksbuendig`, `linksbundig`, `m`, `middle`, `mitte`, `r`, `rechts`, `rechtsbuendig`, `rechtsbundig`, `right`, `zentriert` | ja | -- | Horizontale Ausrichtung des Blockinhalts: `left`/`links`, `right`/`rechts`, `center`/`mitte`/`zentriert` oder `block`/`blocksatz` (deutsche und englische Schreibweisen gleichwertig). |
| `height` | CSS-Länge | -- | nein | `3cm` | Höhe des Antwortfelds als CSS-Länge (z. B. `4cm`, `120px`). Der genaue Standardwert hängt vom Blocktyp ab (siehe Tabelle: Spalte "Standard"). |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::space height=3cm

:::
```

### `subtask`

Teilaufgabe zu einem vorangehenden `task`. Muss unmittelbar nach dem zugehörigen `task` als eigener Top-Level-Block folgen (nicht verschachtelt); mehrere `subtask`-Blöcke werden automatisch a), b), c) ... nummeriert. Unterstützt `time`/`work`/`action` wie `task`.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `action` | Enum | `aus`, `austauschen`, `calc`, `calculate`, `dec`, `decide`, `draw`, `drw`, `ent`, `entscheiden`, `exc`, `exchange`, `exp`, `experiment`, `experimentieren`, `les`, `lesen`, `mat`, `match`, `rd`, `read`, `rech`, `rechnen`, `ref`, `reflect`, `reflektieren`, `schr`, `schreiben`, `write`, `wrt`, `zei`, `zeichnen`, `zuo`, `zuordnen` | ja | *(keiner)* | Tätigkeits-Hinweis, wird als Emoji + Label gerendert (`read`/`lesen` 📖, `write`/`schreiben` ✍️, `calculate`/`rechnen` 🔢, `draw`/`zeichnen` 📐, `match`/`zuordnen` ↔️, `exchange`/`austauschen` 💬, `decide`/`entscheiden` ⚖️, `experiment`/`experimentieren` 🧪, `reflect`/`reflektieren` 🤔). Ohne Angabe wird kein Aktions-Symbol angezeigt. |
| `align` | Enum | `b`, `block`, `blocksatz`, `c`, `center`, `centre`, `j`, `justify`, `l`, `left`, `links`, `linksbuendig`, `linksbundig`, `m`, `middle`, `mitte`, `r`, `rechts`, `rechtsbuendig`, `rechtsbundig`, `right`, `zentriert` | ja | -- | Horizontale Ausrichtung des Blockinhalts: `left`/`links`, `right`/`rechts`, `center`/`mitte`/`zentriert` oder `block`/`blocksatz` (deutsche und englische Schreibweisen gleichwertig). |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |
| `time` | Text | -- | nein | -- | Geschätzte Bearbeitungszeit, wird als `X min` ausgegeben. Freier Textwert -- üblich, aber nicht erzwungen, ist eine reine Zahl (Minuten). |
| `work` | Enum | `ea`, `einzel`, `ga`, `group`, `grp`, `gruppe`, `pa`, `partner`, `sgl`, `single` | ja | `single` | Empfohlene Arbeitsform, wird als Emoji + Label gerendert: `single`/`einzel` (👤), `partner` (👥) oder `group`/`gruppe` (👪). Deutsche und englische Schreibweisen sind gleichwertig. Ohne Angabe gilt `single`. |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::subtask work=single
Teilaufgabe hier…
:::
```

### `table`

Tabellen-Antwortfeld. **Zellinhalte müssen als `cells:`-YAML-Liste-von-Listen im Blockinhalt stehen** (siehe Beispiel unten) -- eine native Markdown-Tabelle (`| A | B |`) im Blockinhalt wird **nicht** geparst und bleibt unwirksam. `headers="A|B|C"` setzt Spaltenüberschriften, `header_columns=<n>` (Alias `header_cols`) macht die ersten `n` Spalten zu Header-Spalten, `row_labels="..."` beschriftet Zeilen, `widths=...` steuert Spaltenbreiten, `alignment=left|center|right|justify` (auch Kurzformen `l`/`r`/`c`/`j`, auch pro Spalte) die Ausrichtung, `row_height=<css-länge>` die Zeilenhöhe.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `alignment` | Enum | `c`, `center`, `j`, `justify`, `l`, `left`, `r`, `right` | nein | -- | Eigene, von der generischen `align`-Option unabhängige Semantik: steuert die Textausrichtung je Tabellenspalte, auch als Kurzform pro Spalte (z. B. `alignment="l r c c"` mit `l`/`r`/`c`/`j` für links/rechts/zentriert/Blocksatz). Aktuell nicht vom Validator geprüft. |
| `cols` | Ganzzahl | -- | nein | -- | Anzahl Spalten des Rasters. Der genaue Standardwert und ob eine fehlende Angabe automatisch aus verfügbarer Breite berechnet wird, hängt vom Blocktyp ab (siehe Tabelle: Spalte "Standard"). |
| `header_cols` | Ganzzahl | -- | nein | -- | Alias von `header_columns`. |
| `header_columns` | Ganzzahl | -- | nein | -- | Rendert die ersten `n` Spalten im Tabellenkörper als Header-Spalten. |
| `headers` | Text | -- | nein | -- | Spaltenüberschriften, `|`-getrennt (z. B. `headers="A|B|C"`). |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `row_height` | CSS-Länge | -- | nein | -- | Zeilenhöhe als CSS-Länge. |
| `row_labels` | Text | -- | nein | -- | Zeilenbeschriftungen, `|`-getrennt (z. B. `row_labels="Zeile 1|Zeile 2"`). |
| `rows` | Ganzzahl | -- | nein | -- | Anzahl Zeilen des Rasters/der Linien. Der genaue Standardwert und ob eine fehlende Angabe automatisch berechnet wird, hängt vom Blocktyp ab (siehe Tabelle: Spalte "Standard"). |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |
| `width` | CSS-Länge | -- | nein | -- | Gesamtbreite der Tabelle als CSS-Länge. |
| `widths` | Text | -- | nein | -- | Relative Breiten (Gewichte, z. B. `"2 1"`) oder feste CSS-Breiten für die Spalten/Elemente dieses Blocks. |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::table rows=3 cols=3 headers="A|B|C"
cells:
  - ["", "", ""]
  - ["", "", ""]
  - ["", "", ""]
:::
```

### `task`

Die Hauptaufgabe -- der zentrale Blocktyp eines Arbeitsblatts. `points` vergibt eine Punktzahl, `time` eine Bearbeitungszeit in Minuten (Ausgabe als `X min`). `work` zeigt die empfohlene Arbeitsform (`single`/`partner`/`group`, auch deutsche Aliase wie `einzel`), `action` einen Tätigkeits-Hinweis (`read`/`write`/`calculate`/...) und `hint` einen Lernhinweis (`tip`/`definition`/`remember`/...) -- jeweils mit passendem Emoji gerendert. `title` beschriftet die Aufgabe zusätzlich zur automatischen Nummerierung.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `action` | Enum | `aus`, `austauschen`, `calc`, `calculate`, `dec`, `decide`, `draw`, `drw`, `ent`, `entscheiden`, `exc`, `exchange`, `exp`, `experiment`, `experimentieren`, `les`, `lesen`, `mat`, `match`, `rd`, `read`, `rech`, `rechnen`, `ref`, `reflect`, `reflektieren`, `schr`, `schreiben`, `write`, `wrt`, `zei`, `zeichnen`, `zuo`, `zuordnen` | ja | *(keiner)* | Tätigkeits-Hinweis, wird als Emoji + Label gerendert (`read`/`lesen` 📖, `write`/`schreiben` ✍️, `calculate`/`rechnen` 🔢, `draw`/`zeichnen` 📐, `match`/`zuordnen` ↔️, `exchange`/`austauschen` 💬, `decide`/`entscheiden` ⚖️, `experiment`/`experimentieren` 🧪, `reflect`/`reflektieren` 🤔). Ohne Angabe wird kein Aktions-Symbol angezeigt. |
| `align` | Enum | `b`, `block`, `blocksatz`, `c`, `center`, `centre`, `j`, `justify`, `l`, `left`, `links`, `linksbuendig`, `linksbundig`, `m`, `middle`, `mitte`, `r`, `rechts`, `rechtsbuendig`, `rechtsbundig`, `right`, `zentriert` | ja | -- | Horizontale Ausrichtung des Blockinhalts: `left`/`links`, `right`/`rechts`, `center`/`mitte`/`zentriert` oder `block`/`blocksatz` (deutsche und englische Schreibweisen gleichwertig). |
| `hint` | Enum | `def`, `definition`, `eri`, `erinnerung`, `exp`, `expert`, `experte`, `fachwort`, `fw`, `hint`, `rem`, `remember`, `reminder`, `term`, `tip`, `tipp`, `tm`, `tp` | ja | *(keiner)* | Siehe `option:hint` -- bei `task` zusätzlich mit passendem Emoji direkt neben der Aufgabe gerendert. |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `points` | Text | -- | nein | -- | Vergibt eine Punktzahl für die Aufgabe, wird neben der Aufgabe angezeigt. |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |
| `time` | Text | -- | nein | -- | Geschätzte Bearbeitungszeit, wird als `X min` ausgegeben. Freier Textwert -- üblich, aber nicht erzwungen, ist eine reine Zahl (Minuten). |
| `title` | Text | -- | nein | -- | Überschreibt die automatisch erzeugte Standardbeschriftung des Blocks mit einem eigenen Text. |
| `work` | Enum | `ea`, `einzel`, `ga`, `group`, `grp`, `gruppe`, `pa`, `partner`, `sgl`, `single` | ja | `single` | Empfohlene Arbeitsform, wird als Emoji + Label gerendert: `single`/`einzel` (👤), `partner` (👥) oder `group`/`gruppe` (👪). Deutsche und englische Schreibweisen sind gleichwertig. Ohne Angabe gilt `single`. |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::task work=single action=write
Aufgabentext hier…
:::
```

### `vspacer`

Erzeugt vertikalen Abstand in voller Breite -- siehe Control-Marker `-=`.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `height` | CSS-Länge | -- | nein | -- | Höhe des Antwortfelds als CSS-Länge (z. B. `4cm`, `120px`). Der genaue Standardwert hängt vom Blocktyp ab (siehe Tabelle: Spalte "Standard"). |

### `wordsearch`

Wortsuchrätsel-Antwortfeld. `words` listet die zu versteckenden Wörter, `diagonal`/`horizontal`/`vertical` steuern erlaubte Richtungen, `min_size`/`min_rows`/`min_cols` die Mindestrastergröße.

| Option | Art | Erlaubte Werte | Geprüft? | Standard | Erklärung |
|---|---|---|---|---|---|
| `align` | Enum | `b`, `block`, `blocksatz`, `c`, `center`, `centre`, `j`, `justify`, `l`, `left`, `links`, `linksbuendig`, `linksbundig`, `m`, `middle`, `mitte`, `r`, `rechts`, `rechtsbuendig`, `rechtsbundig`, `right`, `zentriert` | ja | -- | Horizontale Ausrichtung des Blockinhalts: `left`/`links`, `right`/`rechts`, `center`/`mitte`/`zentriert` oder `block`/`blocksatz` (deutsche und englische Schreibweisen gleichwertig). |
| `diagonal` | Bool | -- | nein | `False` | Erlaubt diagonale Wortplatzierung im Rätsel (Standard: aus). Akzeptiert auch eine Richtungsliste statt eines einfachen Ein/Aus-Werts. |
| `horizontal` | Bool | -- | nein | `False` | Erlaubt horizontale Wortplatzierung (Standard: aus). Akzeptiert auch eine Richtungsliste. |
| `min_cols` | Ganzzahl | -- | nein | -- | Mindestanzahl Spalten des Rätselrasters. |
| `min_rows` | Ganzzahl | -- | nein | -- | Mindestanzahl Zeilen des Rätselrasters. |
| `min_size` | Ganzzahl | -- | nein | -- | Mindestrastergröße (Zeilen und Spalten gemeinsam). |
| `mode` | Enum | `solution`, `worksheet` | ja | -- | Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der Block in beiden Ausgaben sichtbar. |
| `show` | Enum | `both`, `solution`, `worksheet` | ja | `both` | Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung `OP003` aus, bleibt aber weiterhin funktionsfähig). |
| `vertical` | Bool | -- | nein | `False` | Erlaubt vertikale Wortplatzierung (Standard: aus). Akzeptiert auch eine Richtungsliste. |
| `words` | Text | -- | nein | -- | Blocktyp-abhängige Bedeutung, siehe Besonderheit unten. |

**Beispiel** (identisch mit dem Ctrl+B-Einfügemenü im Editor):

```markdown
:::wordsearch min_size=10x12 diagonal=false
- Wort1
- Wort2
- Wort3
:::
```

## 6. Wertlisten für `work`/`action`/`hint`

**work (Arbeitsform bei task/subtask):** `ea`, `einzel`, `ga`, `group`, `grp`, `gruppe`, `pa`, `partner`, `sgl`, `single`

**action (Tätigkeits-Hinweis bei task):** `aus`, `austauschen`, `calc`, `calculate`, `dec`, `decide`, `draw`, `drw`, `ent`, `entscheiden`, `exc`, `exchange`, `exp`, `experiment`, `experimentieren`, `les`, `lesen`, `mat`, `match`, `rd`, `read`, `rech`, `rechnen`, `ref`, `reflect`, `reflektieren`, `schr`, `schreiben`, `write`, `wrt`, `zei`, `zeichnen`, `zuo`, `zuordnen`

**hint (Lernhinweis bei task):** `def`, `definition`, `eri`, `erinnerung`, `exp`, `expert`, `experte`, `fachwort`, `fw`, `hint`, `rem`, `remember`, `reminder`, `term`, `tip`, `tipp`, `tm`, `tp`

## 7. Control-Marker-Referenz

- **framebreak**: `-+` auf einer eigenen Zeile erzeugt im Präsentationsmodus einen neuen Frame, der den bisherigen Folieninhalt beibehält und um den folgenden Inhalt ergänzt -- für das schrittweise Aufbauen **desselben** Gedankens auf **derselben** Folie (z. B. Punkt für Punkt aufdecken). Der Präsentations-Exportdialog bietet eine Option, diese schrittweisen Folien beim Export zu einer einzigen finalen Folie zusammenzufassen. **`-+` ist kein Folientrenner:** wird er anstelle von `--!` verwendet, um inhaltlich neue/andere Folien einzuleiten, sammelt sich der gesamte bisherige Inhalt auf einer einzigen, zunehmend überfüllten Folie an, statt eine neue zu beginnen -- für einen echten Folienwechsel immer `--!` verwenden.
- **pagebreak**: `--!` auf einer eigenen Zeile erzwingt einen harten Seiten-/Folienumbruch an dieser Stelle -- der Marker, um in einer Präsentation gezielt eine **neue** Folie zu beginnen.
- **sectionmark**: `--# Abschnittsname` setzt den aktuellen Abschnittsnamen für die Footer-Navigation in Präsentationen. Alles nach `--# ` bis Zeilenende wird als Abschnittstitel übernommen.
- **slidechromeoff**: `--hf` auf einer eigenen Zeile blendet auf der aktuellen Folie Mini-Header und Footer (Phasenübersicht + Folienzähler) aus, ohne das globale Präsentationslayout zu verändern -- nützlich für Folien mit wenig Platz.
- **soft_section_break**: `--` auf einer eigenen Zeile markiert einen weichen Abschnittswechsel (Solltrennstelle) ohne zusätzlichen vertikalen Abstand. Die normale Markdown-Trennlinie `---` ist demgegenüber **kein** Blattwerk-Kontrollmarker, sondern gewöhnliches Markdown: sie erzeugt ebenfalls einen Abschnittswechsel, aber zusätzlich mit `1cm` Abstand (per CSS in `assets/worksheet.css`), weil der Parser sie gar nicht als eigenes Token erkennt.
- **vspacer**: `-=<css-länge>` (z. B. `-=0.5cm`, `-=20px`) erzeugt vertikalen Abstand in voller Seiten-/Spaltenbreite -- nützlich zum manuellen Feintuning des Layouts.

## 8. Geometry im Detail (`:::geometry`)

### Blockoptionen

`:::grid` und `:::geometry` unterstützen die Option `line=solid|dashed` (Standard: `solid`), die den Linienstil des Rasterhintergrunds selbst steuert -- unabhängig vom gleichnamigen `pairs[].line`-Feld auf Objektebene (siehe unten), das nur die einzelne Strecke betrifft.

Erlaubte `line`-Werte: `dashed`, `solid`.

### `functions`

Funktionsgraphen (nur im Achsenmodus). `expr` ist der auszuwertende Funktionsterm, `domain` der Definitionsbereich als `min:max` (Standard `-10:10`, auch `min..max` erlaubt). `label` beschriftet den Graphen am rechten (letzten sichtbaren) Kurvenende. `color`/`thickness` wie bei `points`.

Erlaubte Keys: `color`, `domain`, `expr`, `label`, `show`, `thickness`.

### `pairs`

Einzelne Strecken zwischen zwei Punkten (`x1,y1` nach `x2,y2`). `label` beschriftet die Strecke am Streckenmittelpunkt. `line=solid|dashed` (Standard bei fehlendem/ungültigem Wert: `dashed`) steuert den Linienstil dieser einzelnen Strecke -- eine eigene, von der Block-Option `line` unabhängige Ebene; ein ungültiger Wert wird als `AN012` gemeldet. `color`/`thickness` wie bei `points`.

Erlaubte Keys: `color`, `label`, `line`, `show`, `thickness`, `x1`, `x2`, `y1`, `y2`.

### `points`

Einzelne markierte Punkte im Raster. Im Achsenmodus (`axis=true`) werden `x`/`y` als mathematische Koordinaten interpretiert, sonst `col`/`row` (bzw. `x`/`y` als Alias) als direkte Rasterkoordinaten. `label` beschriftet den Punkt. `color` (beliebiger CSS-Farbwert) und `thickness` (positive Zahl) sind optional -- fehlt einer der beiden oder ist er ungültig, fällt der Punkt auf den bisherigen Theme-Standard zurück, ohne den Build zu blockieren (Warnung `AN013`/`AN014`).

Erlaubte Keys: `col`, `color`, `label`, `row`, `show`, `thickness`, `x`, `y`.

### `sequence`

Eine Liste aus `x`/`y`-Punkten (nur im Achsenmodus sinnvoll), die als sortierte Polylinie verbunden werden. `color`/`thickness` gelten für die Verbindungslinie selbst, nicht für einzelne Punktmarkierungen.

Erlaubte Keys: `color`, `label`, `show`, `thickness`, `x`, `y`.

### Repräsentatives Beispiel

```markdown
:::geometry rows=20 cols=20 axis=true origin="10,10"
points:
  - {x: 2, y: 3, label: "A", color: "#2563eb", thickness: 2}
pairs:
  - {x1: 0, y1: 0, x2: 4, y2: 4, line: dashed, label: "Strecke g"}
functions:
  - {expr: "x^2", domain: "-3:3", label: "f(x) = x^2", color: "#dc2626", thickness: 1.5}
:::
```

Flow-Style-YAML (`{key: value, ...}` auf einer Zeile) ist die in den Blattwerk-Beispielen übliche Schreibweise für Geometry-Einträge -- Block-Style (`key:` mit eingerückten Folgezeilen) ist gleichwertig und wird identisch geparst. `axis=true` **und** ein gültiges `origin` sind zusammen nötig, damit `functions` überhaupt gerendert wird und `points`/`pairs` als Mathe-Koordinaten statt Rasterkoordinaten interpretiert werden (siehe Besonderheit bei `axis`/`origin` oben).

## 9. Sichtbarkeitsmarker in Antwortinhalten

Für textbasierte Antwort-Blocktypen (`lines`, `grid`, ...) steuern Zeilenmarker `§`/`%`/`&` (am Zeilenanfang) bzw. Inline-Token `§{...}`/`%{...}`/`&{...}` (mitten in der Zeile), ob ein Textteil nur im Arbeitsblatt, nur in der Lösung oder in beiden erscheint. Text ohne Marker ist standardmäßig in beiden Modi sichtbar.
