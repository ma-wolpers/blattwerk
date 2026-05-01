# Blattwerk-Format: Designsprache und Syntax

Diese Datei ist die verbindliche Sprachreferenz für Blattwerk-Markdown.

Die kanonische formale Grammatik steht ergänzend in `docs/GRAMMAR.md`.

## 1. Zweck

Blattwerk ist ein Renderer für Arbeitsblätter mit  eigener semantischer Auszeichnungssprache.
Semantik hat Vorrang, aber Layout-Steuerung ist ausdrücklich Teil der Sprache, wenn sie der Lesbarkeit und Nutzbarkeit dient.

## 2. Grundprinzipien (verbindlich)

1. Semantik vor Layout (mit erlaubter Layout-Steuerung).
2. Dokumentinhalt und Dokumentstruktur ins Frontmatter.
3. Ausgabe-/Druckprofile bleiben in der App/UI, nicht im Frontmatter.
4. Lokale Steuerung in Blockoptionen.
5. Inhalt bleibt Markdown; strukturierte Antwortinhalte sind YAML.
6. Antworttyp bestimmt Inhaltsschema; `answer` ohne `type` ist ungültig.
7. Blocksichtbarkeit erfolgt über `mode=worksheet|solution`; ohne `mode` ist der Block in Arbeitsblatt und Lösung sichtbar. Der alte Key `show` ist deprecated.
8. Teilaufgaben sind Folgeblöcke (`subtask`) nach `task`, nie geschachtelt.

## 3. Dokumentstruktur

Ein Dokument besteht aus:
1. YAML-Frontmatter (Pflicht)
2. einer Folge semantischer Blöcke
3. optionalen Abschnittstrennern (`---`, `--!`, `-+`, `--# ...`, `-=...`)

### 3.1 Frontmatter

```yaml
---
Titel: Titel des Arbeitsblatts
Fach: Fach
Thema: Oberthema
Stufe: Jahrgangsstufe            # optional
worksheet_type: Arbeitsblatt     # optional
show_student_header: true|false
show_document_header: true|false
mode: worksheet|solution|presentation|test  # optional, Standard: worksheet
presentation_layout: presentation_16_9|presentation_16_10|presentation_4_3  # optional (bei mode: presentation)
presentation_show_mini_header: true|false  # optional (default true)
presentation_show_section_footer: true|false  # optional (default true)
lochen: ja|nein                  # optional
copyright: "Text"               # optional
font_profile: segoe              # optional
---
```

Pflichtfelder:
- `Titel`
- `Fach`
- `Thema`

Optionales Dokumentfeld:
- `mode`: `worksheet`, `solution`, `presentation` oder `test` (`ws` bleibt Alias fuer `worksheet`).
- `presentation_layout`: Layout-Preset fuer Folien (`presentation_16_9`, `presentation_16_10`, `presentation_4_3`).
- `presentation_show_mini_header`: blendet Mini-Header pro Folie ein/aus.
- `presentation_show_section_footer`: blendet Abschnittsfooter pro Folie ein/aus.

Wirkung von `mode`:
- `worksheet` (Standard): normales Arbeitsblatt-Verhalten.
- `solution`: globale Loesungsansicht (z. B. fuer direkte Loesungsdokumente).
- `presentation`: Folienausgabe mit Mini-Header, Folienzaehlung und Abschnittsfooter.
- `test`: blendet in `task` und `subtask` die Arbeitsform-Hinweise aus (`work`-Emoji und `work`-Label).
- `action`- und `hint`-Symbole bleiben unverändert sichtbar.

Nicht ins Frontmatter:
- `page_format`
- `print_profile`
- `color_profile`
- `font_size_profile`

Diese vier Werte werden in der App/UI gesetzt.

## 4. Formale Kernsyntax (Kurzreferenz)

```ebnf
document = frontmatter, newline*, block_or_raw* ;
frontmatter = "---", newline, yaml_lines, "---", newline* ;

block_or_raw = block | section_break | raw_markdown ;
section_break = ("--" | "--!" | "-+" | "--#" section_title | "-=" css_length), newline ;

block = open_block, block_content, close_block | self_closing_block ;
open_block = ":::", block_name, (space, options)?, newline ;
close_block = ":::", newline? ;
self_closing_block = ":::", block_name, (space, options)?, space?, ":::", newline? ;

block_name = "material" | "info" | "task" | "subtask"
           | "answer" | "solution" | "columns" | "nextcol" | "endcolumns"
           | "help" | "hilfe" ;

options = option, (space, option)* ;
option = key, "=", value ;
```

Zusatzregeln:
- `subtask` darf nur nach einem `task` stehen (bis zum nächsten `task`).
- Geschachtelte `subtask`-Blöcke in `task`-Inhalten sind nicht Teil der Sprache.
- `--!` erzwingt einen harten Seiten-/Folienumbruch.
- `-+` erzeugt im Praesentationsmodus einen neuen Frame mit dem bisherigen Inhalt plus folgendem Inhalt.
- `--# Abschnitt` setzt den aktuellen Abschnittsnamen fuer Footer-Navigation in Praesentationen.
- `-=<css-laenge>` erzeugt vertikalen Abstand mit voller Seiten-/Spaltenbreite.
- `---` ist wieder normale Markdown-Linie und dient nicht mehr als Spacer.

Die ausführliche formale Definition (inklusive Lexer-Hinweisen und Stabilitätsregeln für Diagnosecodes) steht in `docs/GRAMMAR.md`.

## 5. Blocktypen

### 5.1 material
Zweck: Kontext und Erklärmaterial.
Optionen: `title` (optional), `show` (optional)

### 5.2 info
Zweck: Hinweisbox.
Optionen: `type=default|warning|note`, `show` (optional)

### 5.3 task
Zweck: Hauptaufgabe.
Optionen:
- `points` (optional)
- `work` (optional)
- `action` (optional)
- `hint` (optional)
- `show` (optional)

#### work
Kanonisch (EN):
- `single`
- `partner`
- `group`

Dokumentierte Aliase:
- `ea`, `einzel`, `einzelarbeit` -> `single`
- `pa`, `partnerarbeit` -> `partner`
- `ga`, `gruppe`, `gruppenarbeit` -> `group`

#### action
Kanonisch (EN):
- `exchange` -> 💬 austauschen
- `decide` -> ⚖️ entscheiden
- `experiment` -> 🧪 experimentieren
- `reflect` -> 🤔 reflektieren
- `read` -> 📖 lesen
- `calculate` -> 🔢 rechnen
- `match` -> ↔️ zuordnen
- `write` -> ✍️ schreiben
- `draw` -> 📐 zeichnen

Dokumentierte DE-Aliase:
- `austauschen`, `entscheiden`, `experimentieren`, `reflektieren`, `lesen`, `rechnen`, `zuordnen`, `schreiben`, `zeichnen`

#### hint
Kanonisch (EN):
- `tip` -> 💡 Tipp
- `definition` -> 📘 Definition
- `remember` -> 💭 Erinnerung
- `term` -> 📖 Fachwort
- `expert` -> 🚀 Expertenaufgabe

Dokumentierte DE-Aliase:
- `tipp`, `erinnerung`, `fachwort`, `expertenaufgabe`

### 5.4 subtask
Zweck: Teilaufgabe zu vorherigem `task`.
Optionen: `work`, `action`, `show` (alle optional)
Regel: Nur als Folgeblock auf Top-Level.

### 5.5 Antwort-Blocktypen
Zweck: Antwortbereich oder interaktiver Antworttyp.

Unterstützte dedizierte Blocktypen:
- `lines`
- `grid`
- `geometry`
- `dots`
- `space`
- `table`
- `numberline`
- `mc`
- `cloze`
- `matching`
- `wordsearch`

Regeln:
- Legacy-Syntax `:::answer type=...` ist nicht erlaubt.
- `grid` ist textbasiert und dient als Kaestchen-/Schreibfeld mit Marker-Text.
- Strukturierte Inhalte sind YAML fuer `geometry`, `numberline`, `table` und `matching`.
- `matching` ist YAML-only (kein alternatives [section]-Format).

#### Lines-Optionen und Renderingverhalten

Fuer `lines` gilt zusaetzlich:

- `rows=<n>`
    - Standard: `3`
    - Definiert die Mindestanzahl sichtbarer Linien.
- `height=<css-laenge>`
    - Optional, z. B. `2.1em` oder `8mm`.
    - Steuert die konkrete Linienhoehe (Zeilenraster/Pitch) pro Antwortzeile.

Linienanzahl-Regel (Arbeitsblatt und Loesung):
- Effektive Linienanzahl = `max(rows, sichtbare Inhaltszeilen)`.
- `sichtbare Inhaltszeilen` zaehlt die expliziten Textzeilen nach Marker-Filterung.
- Weiche Umbrueche durch volle Zeilenbreite (Soft-Wrap) erhoehen die Linienanzahl **nicht** automatisch.

Markdown auf Linien:
- Markdown (z. B. `**fett**`, Listen) ist in `lines` erlaubt.
- Zeilenabstaende und Linienraster sind auf denselben vertikalen Takt gekoppelt, damit explizite Newlines und Soft-Wraps geometrisch konsistent bleiben.
- Escaped-Leerzeichen (`\ `) bleiben als sichtbare Platzhalter erhalten (z. B. `(\ \ \ \ )` fuer Klammer-Luecken).

#### Grid-Optionen

Fuer `grid` gilt zusaetzlich:

- `scale=<css-laenge>`
    - Standard: `0.5cm`
    - Steuert die Zellgroesse des Rasters (Massstab).
    - Beispiel: `scale=0.4cm`, `scale=6mm`.

Automatische Spaltenzahl in `grid` ohne `cols`:
- Ohne explizites `cols` wird `cols` deterministisch aus aktiver Druck-Inhaltsbreite (Seitenformat + aktive Seitenraender) und `scale` berechnet.
- Regel: `cols = floor(verfuegbare_breite / cell_size)` mit Mindestwert `1`.
- Das beruecksichtigt auch den Frontmatter-Schalter `lochen` fuer vergroesserten linken Rand.
- Ziel: Zellen werden nicht schmaler als `scale`.

Textinhalt in `grid`:
- Marker-/Inline-Text wird wie bei `lines` nach Arbeitsblatt/Loesung gefiltert und als Overlay im Kaestchenfeld gerendert.
- Unmarkierter Text ist in beiden Modi sichtbar.

#### Geometry-Optionen

Fuer `geometry` gilt zusaetzlich:

- `scale=<css-laenge>`
    - Standard: `0.5cm`
    - Steuert die Zellgroesse des Rasters (Massstab).
    - Beispiel: `scale=0.4cm`, `scale=6mm`.
- `axis=true|false`
    - Aktiviert ein mathematisches Koordinatensystem mit x-/y-Achse.
    - Bei `axis=true` werden Achsen, Tick-Marks und Achsenlabels standardmäßig gerendert.
- `origin="col,row"`
    - Ursprung im Raster (z. B. `"10,10"`).
- `step_x=<zahl>`, `step_y=<zahl>`
    - Skalierung zwischen mathematischen Koordinaten und Grid-Zellen.
- `axis_label_x=<text>`, `axis_label_y=<text>`
    - Optionale Achsenbezeichnungen am positiven Achsenende.
    - Standard: `x` und `y`.

Geometry-YAML-Sichtbarkeit auf Elementebene (`points`, `sequence`, `pairs`, `functions`):
- `show: "§"` = nur Arbeitsblatt
- `show: "%"` = nur Lösung
- `show: "&"` = Arbeitsblatt und Lösung
- Ohne `show` gilt standardmäßig `"&"`.
- Werte wie `show: worksheet|solution|both` sind für Grid-Elemente ungültig.

`sequence`-Einträge (`x`, `y`, optional `label`): alle sichtbaren Punkte werden nach x-Wert sortiert als Polylinie verbunden.

`pairs`-Einträge (`x1`, `y1`, `x2`, `y2`): jeder Eintrag wird als unabhängige Strecke von Endpunkt 1 nach Endpunkt 2 gerendert.
- Optionaler Key `line`: `solid` | `dashed` (Standard: `dashed`)

Numberline-YAML-Sichtbarkeit auf Elementebene (`labels`, `answers`, `arcs`):
- `show: "§"` = nur Arbeitsblatt
- `show: "%"` = nur Lösung
- `show: "&"` = Arbeitsblatt und Lösung
- Ohne `show` gilt standardmäßig `"&"`.
- Werte wie `show: worksheet|solution|both` sind für Numberline-Elemente ungültig.

#### Matching-Optionen

Für `matching` gelten zusätzlich folgende Optionen:

- `height_mode=content|uniform`
    - Standard: `content`
    - `content`: Jeder Block richtet seine Höhe nach dem eigenen Inhalt.
    - `uniform`: Alle Blöcke sind gleich hoch; die Höhe wird automatisch aus dem längsten Inhalt bestimmt.
- `align=center`
    - Standard: `center`
    - Zentriert Inhalte in Matching-Blöcken horizontal und vertikal.
- `lane_align=start|center|end`
    - Standard: `center`
    - Richtet beide Seiten (links/rechts bzw. oben/unten) entlang ihrer gemeinsamen Mittelachse aus.
- `show_guides=true|false`
    - Standard: `false`
    - `false`: Keine gestrichelten Platzhalterblöcke und kein gestrichelter Canvas-Rand.
    - `true`: Guide-Elemente werden sichtbar gerendert.
- `worksheet_matches`
    - Optionaler YAML-Key mit Paaren im gleichen Format wie `matches`.
    - Diese Verbindungen erscheinen im Arbeitsblatt als Beispielpfade.
    - In der Lösung werden weiterhin die regulären `matches` gerendert.
- Validierung:
    - Wenn eine Seite nur ein Element enthält (`1↔N`), erzeugt der Validator eine Warnung (`MA001`).

#### Marker in textbasierten Antwort-Blockinhalten

Für textbasierte Antwort-Blocktypen sind zwei Varianten verfügbar:

Legacy-Zeilenmarker (gesamte Zeile):
- `§` = Zeile nur im Arbeitsblatt
- `%` = Zeile nur in der Lösung
- `&` = Zeile in Arbeitsblatt und Lösung
- Erkennung nur als eigenes Token am Zeilenanfang oder Zeilenende.

Inline-Token (Teil einer Zeile):
- `§{...}` = nur im Arbeitsblatt sichtbar
- `%{...}` = nur in der Lösung sichtbar
- `&{...}` = in Arbeitsblatt und Lösung sichtbar

Default-Regel:
- Text ohne Token ist in beiden Modi sichtbar.

Beispiele:
- `§ Starte mit einem Satz.`
- `Beispielaufgabe im AB &`
- `§{Impuls im AB} %{Musterantwort in der Loesung} Gemeinsamer Text`
- `Text mit Escape \%\{ bleibt als Literal sichtbar.`
- `$x^2 + 1$` bleibt normales Mathe-/Textfragment (kein Token ohne `{...}`).

Konflikt-/Syntaxregel:
- Legacy-Marker am Anfang und Ende derselben Zeile gelten als Konflikt.
- Inline-Token muessen geschlossen werden (`}`); ungeschlossene Token erzeugen ebenfalls `AN006`.

Option-Namenskonvention (kanonisch):
- MC Inline-Breiten: nur `widths`
- Table Spaltenbreiten: nur `widths`
- Table Ausrichtung: nur `alignment`
- Cloze Lückenmodus: nur `gap`
- Cloze Wortbank-Position: nur `words`

Table-Optionen (zusaetzlich zu `rows`/`cols`):
- `row_height=<css-laenge>`
- `headers="A|B|C"`
- `header_columns=<n>` (Alias: `header_cols=<n>`)
    - Rendert die ersten `n` Spalten im Tabellen-Body als Header-Spalten (`<th scope="row">`).
- `row_labels="Zeile 1|Zeile 2|..."`
- `widths=<gewichte|fr|css-breiten>`
- `alignment=left|center|right|justify`
    - Auch als Kurzform pro Spalte moeglich, z. B. `alignment="l r c c"`.
    - Unterstuetzte Kurzformen: `l`, `r`, `c`, `j`.

### 5.6 solution
Zweck: Musterlösungstext.
Optionen: `label=true|false` (optional, Standard `true`), `show` (optional)

### 5.7 columns / nextcol / endcolumns
Zweck: Spaltenlayout.
`columns` Optionen: `cols=2..6` (optional, Standard `2`), `widths` oder `ratio` (optional), `gap` (optional)

`gap`:
- CSS-Laenge fuer den horizontalen Spaltenabstand.
- Unterstuetzte Einheiten: `px`, `pt`, `cm`, `mm`, `em`, `rem`, `%`.
- Beispiel: `:::columns cols=2 widths="2 1" gap=1cm :::`

### 5.8 help / hilfe
Zweck: Hilfekartenblock (separate Hilfekarten-Ausgabe).
Kanonischer Name: `help`
Dokumentierter Alias: `hilfe`

Optionen:
- `title` (optional, Standard `Hilfe`)
- `level` (optional, 1..99)
- `show` (optional)

## 6. Sichtbarkeit

Für alle Blocktypen gilt optional:
- `show=worksheet|solution|both` (Standard: `both`)

Legacy-Optionen wie `hide_in_solution` oder `hide_in_worksheet` sind nicht Teil der Sprache.

## 7. Abschnittstrenner

- `---` markiert einen Abschnittswechsel (Solltrennstelle) und fuegt zusaetzlich einen vertikalen Abstand von `1cm` zwischen den beiden Abschnitten ein.
- `--` fungiert ebenfalls als Solltrennstelle, jedoch ohne den zusaetzlichen `1cm`-Abstand.

## 8. Konfliktregel

Wenn Beispiele oder alte Notizen dieser Referenz widersprechen, gilt diese Datei als Norm.
Abweichungen werden durch Bereinigung entfernt, nicht durch Sonderlogik kaschiert.
