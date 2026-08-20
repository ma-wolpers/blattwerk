<!--
Automatisch generiert aus app/core/markdown_conventions.py.
NICHT VON HAND BEARBEITEN.
Neu erzeugen: python tools/docs/generate_authoring_guides.py
-->

# Arbeitsblatt & Präsentation erstellen

Diese Anleitung ist die normative Referenz für den Blattwerk-Markdown-Dialekt, den Arbeitsblätter und Präsentationen gemeinsam nutzen (dieselben `:::`-Blöcke, dasselbe Frontmatter). Sie wird automatisch aus dem Code erzeugt (`app/core/markdown_conventions.py`) -- Blocktypen, Optionen und Frontmatter-Felder können hier nicht veralten, weil sie direkt aus den Konstanten stammen, die der Validator selbst zur Prüfung verwendet.

## 1. Grundidee

Ein Blattwerk-Dokument besteht aus YAML-Frontmatter (Pflicht) gefolgt von einer Folge semantischer `:::blocktyp ...` ... `:::`-Blöcke. Ob ein Dokument als Arbeitsblatt oder als Präsentation gerendert wird, entscheidet allein das Frontmatter-Feld `mode` -- der Blockdialekt selbst ist identisch. Sichtbarkeit pro Block wird über `mode=worksheet|solution` gesteuert (Standard: in beiden Ausgaben sichtbar).

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

-+
:::task title="Weiterfuehrung"
Fuehre hier den naechsten Gedanken aus.
:::
```

`--#` setzt den Abschnittsnamen für die Footer-Navigation, `-+` erzeugt einen neuen Frame, der den bisherigen Folieninhalt beibehält -- siehe Control-Marker-Referenz unten.

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

Optionen: `align`, `gap`, `gap_length`, `layout`, `mode`, `show`, `words`, `words_multi`

### `columns`

Spaltenlayout für nebeneinander angeordnete Inhalte. `cols=2..6` (Standard 2) setzt die Spaltenzahl, `widths`/`ratio` die relativen Breiten, `gap=<css-länge>` den Spaltenabstand. Muss mit `:::nextcol` (Spaltenwechsel) und `:::endcolumns` (Ende) strukturiert werden.

Optionen: `align`, `cols`, `gap`, `ratio`, `widths`

### `dots`

Punktraster-Schreibfeld (z. B. für Übungen zur Feinmotorik/Schrift).

Optionen: `align`, `height`, `mode`, `show`

### `endcolumns`

Schließt einen `:::columns`-Block ab. Keine eigenen Optionen.

Optionen: keine

### `framebreak`

Erzeugt im Präsentationsmodus einen neuen Frame mit dem bisherigen plus neuem Inhalt -- siehe Control-Marker `-+`.

Optionen: keine

### `geometry`

Koordinatensystem für Punkte, Polylinien, Strecken und Funktionsgraphen (siehe Geometry-Abschnitt unten für die YAML-Payload-Struktur). `axis=true` aktiviert echte Achsen mit `origin`/`step_x`/`step_y` zur Umrechnung mathematischer Koordinaten in Rasterzellen; `axis_label_x`/`axis_label_y` beschriften die Achsen (Standard `x`/`y`).

Optionen: `align`, `axis`, `axis_label_x`, `axis_label_y`, `cols`, `line`, `mode`, `origin`, `rows`, `scale`, `show`, `step_x`, `step_y`

### `grid`

Kästchen-/Schreibfeld mit einem Textraster. `rows`/`cols` setzen die Rastergröße (ohne `cols` wird die Spaltenzahl automatisch aus verfügbarer Breite und `scale` berechnet), `scale=<css-länge>` die Zellgröße (Standard `0.5cm`). `line=solid|dashed` steuert den Linienstil des Rasters. Marker-/Inline-Text wird wie bei `lines` nach Arbeitsblatt/Lösung gefiltert.

Optionen: `align`, `cols`, `line`, `mode`, `rows`, `scale`, `show`

### `help`

Separate Hilfekarte (eigene Ausgabe, nicht Teil des normalen Arbeitsblatts). `level` (1-99) gruppiert Hilfen nach Schwierigkeitsstufe, `tag` beeinflusst die automatische Beschriftung (z. B. `1A`, `1B`), `title` überschreibt den Standardtitel "Hilfe". Kanonischer Blockname; `hilfe` ist ein dokumentierter Alias mit identischen Optionen.

Optionen: `level`, `mode`, `show`, `tag`, `title`

### `hilfe`

Dokumentierter Alias für `help` -- identische Optionen und Bedeutung, nur andere Schreibweise.

Optionen: `level`, `mode`, `show`, `tag`, `title`

### `info`

Hinweisbox mit `type=default|warning|note` für unterschiedliche Hervorhebungsstile.

Optionen: `align`, `mode`, `show`, `type`

### `lines`

Textbasiertes Antwortfeld mit Linien zum Beschriften. `rows=<n>` setzt die Mindestanzahl sichtbarer Linien (Standard 3); die tatsächliche Anzahl ist `max(rows, sichtbare Inhaltszeilen)`. `height=<css-länge>` steuert die Linienhöhe. Markdown ist im Inhalt erlaubt; `§`/`%`/`&`-Zeilenmarker (bzw. `§{...}`/`%{...}`/`&{...}` inline) steuern, ob eine Zeile nur im Arbeitsblatt, nur in der Lösung oder in beiden erscheint.

Optionen: `align`, `height`, `mode`, `rows`, `show`

### `matching`

Zuordnungs-Antwortfeld (YAML-only) mit zwei Seiten (`left`/`right` oder `top`/`bottom`, je nach `layout`/`orientation`) und den Verbindungen in `matches`. `worksheet_matches` zeigt optional Beispielverbindungen bereits im Arbeitsblatt. `height_mode=content|uniform`, `lane_align` und `show_guides` steuern das Layout; ein Seiten-Verhältnis von genau einem Element (1↔N) löst die Warnung `MA001` aus.

Optionen: `align`, `bottom`, `height_mode`, `lane_align`, `layout`, `left`, `links`, `matches`, `mode`, `orientation`, `right`, `scale`, `show`, `show_guides`, `top`, `worksheet_matches`

### `material`

Kontext- und Erklärmaterial, das vor einer Aufgabe eingeblendet wird. Optionale `title` beschriftet die Box.

Optionen: `align`, `mode`, `show`, `title`

### `mc`

Multiple-Choice-/Wahr-Falsch-Antwortfeld. `options` listet die Antwortmöglichkeiten, `correct` die richtige(n), `tf`/`true_false` schaltet auf Wahr-Falsch-Layout, `inline` und `widths` steuern das Layout.

Optionen: `align`, `correct`, `inline`, `mode`, `options`, `show`, `tf`, `true_false`, `widths`

### `nextcol`

Spaltenwechsel innerhalb eines `:::columns`-Blocks. Keine eigenen Optionen.

Optionen: keine

### `numberline`

Zahlenstrahl-Antwortfeld mit YAML-Payload (`labels`/`answers`/`arcs`/... je Element mit `show: "§"|"%"|"&"` für Sichtbarkeit). Optionen wie `min`/`max`, `tick_step`, `major_every` und `positive_sign` steuern Wertebereich und Beschriftung.

Optionen: `align`, `full_width`, `height`, `major_every`, `max`, `max_width_cm`, `max_width_mm`, `maximum`, `min`, `minimum`, `mode`, `positive_sign`, `show`, `signed_positive`, `tick_spacing`, `tick_spacing_cm`, `tick_spacing_mm`, `tick_step`, `ticks`

### `pagebreak`

Erzwingt einen harten Seiten-/Folienumbruch -- siehe Control-Marker `--!`.

Optionen: keine

### `qrcode`

Klickbarer QR-Code-Link. `url` ist Pflicht (http/https-Link oder relativer Pfad ohne Leerzeichen). Größenoptionen `w`/`h`/`maxw` (auch `width`/`height`/`max-width`) folgen derselben CSS-Größen-Logik wie Markdown-Bilder (z. B. `3cm`, `120px`, `60%`, `auto`).

Optionen: `align`, `alignment`, `h`, `height`, `max-width`, `maxw`, `mode`, `show`, `url`, `w`, `width`

### `sectionmark`

Setzt den aktuellen Abschnittsnamen für die Präsentations-Footer-Navigation -- siehe Control-Marker `--#`.

Optionen: `title`

### `slidechromeoff`

Blendet Mini-Header/Footer auf der aktuellen Folie aus -- siehe Control-Marker `--hf`.

Optionen: keine

### `solution`

Musterlösungstext. `label=true|false` (Standard `true`) blendet das Label "Lösung" ein/aus.

Optionen: `align`, `label`, `mode`, `show`

### `space`

Freier Leerraum ohne Linien/Raster, z. B. für Zeichnungen.

Optionen: `align`, `height`, `mode`, `show`

### `subtask`

Teilaufgabe zu einem vorangehenden `task`. Muss unmittelbar nach dem zugehörigen `task` als eigener Top-Level-Block folgen (nicht verschachtelt); mehrere `subtask`-Blöcke werden automatisch a), b), c) ... nummeriert. Unterstützt `time`/`work`/`action` wie `task`.

Optionen: `action`, `align`, `mode`, `show`, `time`, `work`

### `table`

Tabellen-Antwortfeld mit YAML-Payload. `headers="A|B|C"` setzt Spaltenüberschriften, `header_columns=<n>` (Alias `header_cols`) macht die ersten `n` Spalten zu Header-Spalten, `row_labels="..."` beschriftet Zeilen, `widths=...` steuert Spaltenbreiten, `alignment=left|center|right|justify` (auch Kurzformen `l`/`r`/`c`/`j`, auch pro Spalte) die Ausrichtung, `row_height=<css-länge>` die Zeilenhöhe.

Optionen: `alignment`, `cols`, `header_cols`, `header_columns`, `headers`, `mode`, `row_height`, `row_labels`, `rows`, `show`, `width`, `widths`

### `task`

Die Hauptaufgabe -- der zentrale Blocktyp eines Arbeitsblatts. `points` vergibt eine Punktzahl, `time` eine Bearbeitungszeit in Minuten (Ausgabe als `X min`). `work` zeigt die empfohlene Arbeitsform (`single`/`partner`/`group`, auch deutsche Aliase wie `einzel`), `action` einen Tätigkeits-Hinweis (`read`/`write`/`calculate`/...) und `hint` einen Lernhinweis (`tip`/`definition`/`remember`/...) -- jeweils mit passendem Emoji gerendert. `title` beschriftet die Aufgabe zusätzlich zur automatischen Nummerierung.

Optionen: `action`, `align`, `hint`, `mode`, `points`, `show`, `time`, `title`, `work`

### `vspacer`

Erzeugt vertikalen Abstand in voller Breite -- siehe Control-Marker `-=`.

Optionen: `height`

### `wordsearch`

Wortsuchrätsel-Antwortfeld. `words` listet die zu versteckenden Wörter, `diagonal`/`horizontal`/`vertical` steuern erlaubte Richtungen, `min_size`/`min_rows`/`min_cols` die Mindestrastergröße.

Optionen: `align`, `diagonal`, `horizontal`, `min_cols`, `min_rows`, `min_size`, `mode`, `show`, `vertical`, `words`

## 6. Wertlisten für `work`/`action`/`hint`

**work (Arbeitsform bei task/subtask):** `ea`, `einzel`, `einzelarbeit`, `ga`, `group`, `gruppe`, `gruppenarbeit`, `pa`, `partner`, `partnerarbeit`, `single`

**action (Tätigkeits-Hinweis bei task):** `austauschen`, `calculate`, `decide`, `draw`, `entscheiden`, `exchange`, `experiment`, `experimentieren`, `lesen`, `match`, `read`, `rechnen`, `reflect`, `reflektieren`, `schreiben`, `write`, `zeichnen`, `zuordnen`

**hint (Lernhinweis bei task):** `def`, `definition`, `erinnerung`, `expert`, `expertenaufgabe`, `fachwort`, `hint`, `remember`, `reminder`, `term`, `tip`, `tipp`

## 7. Control-Marker-Referenz

- **framebreak**: `-+` auf einer eigenen Zeile erzeugt im Präsentationsmodus einen neuen Frame (neue Folie), der den bisherigen Folieninhalt beibehält und um den folgenden Inhalt ergänzt -- nützlich, um einen Gedanken schrittweise aufzubauen.
- **pagebreak**: `--!` auf einer eigenen Zeile erzwingt einen harten Seiten-/Folienumbruch an dieser Stelle.
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

```yaml
points:
  - x: 2
    y: 3
    label: A
    color: "#2563eb"
    thickness: 2
pairs:
  - x1: 0
    y1: 0
    x2: 4
    y2: 4
    line: dashed
    label: Strecke g
functions:
  - expr: "x**2"
    domain: "-3:3"
    label: f(x) = x²
    color: "#dc2626"
    thickness: 1.5
```

## 9. Sichtbarkeitsmarker in Antwortinhalten

Für textbasierte Antwort-Blocktypen (`lines`, `grid`, ...) steuern Zeilenmarker `§`/`%`/`&` (am Zeilenanfang) bzw. Inline-Token `§{...}`/`%{...}`/`&{...}` (mitten in der Zeile), ob ein Textteil nur im Arbeitsblatt, nur in der Lösung oder in beiden erscheint. Text ohne Marker ist standardmäßig in beiden Modi sichtbar.
