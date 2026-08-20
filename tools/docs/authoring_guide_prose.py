"""Redaktionelle Prosa-Bausteine für die generierten Blattwerk-Autoren-Anleitungen.

Reine Datendatei (ein Dict aus Textkonstanten, keine Logik) -- vom
300-Zeilen-Limit ausgenommen, analog zu `blatt_validator_constants.py`.

Diese Texte sind **redaktionell**, nicht aus Code abgeleitet: sie erklären
Autor:innen, wozu ein Blocktyp/Feld/Marker gedacht ist und wie man ihn
sinnvoll einsetzt. Die **normativen Fakten** (welche Optionen/Werte
tatsächlich erlaubt sind) kommen ausschließlich aus
`app/core/markdown_conventions.py`; diese Datei darf ihnen nicht
widersprechen, sie nur erklären.

`assert_prose_coverage()` in `generate_authoring_guides.py` erzwingt, dass
jeder Katalogeintrag (Blocktyp, Frontmatter-Feld, Control-Marker, Geometry-
Sektion, Kurzentwurf-Aspekt) hier einen Eintrag hat -- neue DSL-Elemente im
Code zwingen dadurch zu einem manuellen Doku-Update, bevor CI grün wird.
Geprüft wird nur *Existenz*, nicht inhaltliche Korrektheit (keine
Automatisierung natürlicher Sprache).
"""

from __future__ import annotations

PROSE_SECTIONS: dict[str, str] = {
    # -- Frontmatter: Pflichtfelder --------------------------------------
    "frontmatter:Titel": "Der Titel des Dokuments, erscheint im Dokumentkopf und in der Fensterleiste.",
    "frontmatter:Fach": "Das Unterrichtsfach, erscheint zusammen mit `Thema` in der Metazeile des Dokumentkopfs.",
    "frontmatter:Thema": "Das konkrete Unterrichtsthema, erscheint zusammen mit `Fach` in der Metazeile des Dokumentkopfs.",
    # -- Frontmatter: optionale Felder ------------------------------------
    "frontmatter:mode": (
        "Steuert das grundlegende Ausgabeverhalten des Dokuments. `worksheet` (Standard, Alias `ws`) "
        "zeigt normale Arbeitsblatt-Ausgabe; `solution` rendert global die Lösungsansicht; "
        "`presentation` schaltet auf Folienausgabe mit Mini-Header und Folienzähler um; `test` blendet "
        "in Aufgaben/Teilaufgaben nur die Arbeitsform-Hinweise (Emoji + Label) aus."
    ),
    "frontmatter:presentation_layout": (
        "Wählt das Seitenverhältnis der Folien bei `mode: presentation` (`presentation_16_9`, "
        "`presentation_16_10` oder `presentation_4_3`). Ohne `mode: presentation` ohne Wirkung."
    ),
    "frontmatter:presentation_show_mini_header": (
        "Blendet in Präsentationen den kleinen Kopfbereich pro Folie (Phasenübersicht) ein/aus. "
        "Standard: an."
    ),
    "frontmatter:presentation_show_section_footer": (
        "Blendet in Präsentationen den Abschnittsfooter (Folienzähler) pro Folie ein/aus. Standard: an."
    ),
    "frontmatter:tag": (
        "Freier Kurzbezeichner, der z. B. als Präfix für automatisch generierte Lernhilfe-Label "
        "verwendet werden kann (siehe `help`/`hilfe`-Block-Option `tag`). Muss ein einfacher, "
        "nicht-leerer Textwert sein -- kein YAML-Mapping oder -Liste."
    ),
    "frontmatter:show_student_header": (
        "Blendet die Schülerkopfzeile (Name/Lerngruppe/Datum-Felder) am Dokumentanfang ein/aus. "
        "Standard: aus. Erwartet einen booleschen Wert im Format `ja`/`nein` (auch `true`/`false`, "
        "`1`/`0`, `j`/`n` werden akzeptiert)."
    ),
    "frontmatter:show_document_header": (
        "Blendet den Dokumentkopf (Titel, Fach/Thema-Metazeile) ein/aus. Standard: an. Erwartet "
        "denselben booleschen Werttyp wie `show_student_header`."
    ),
    "frontmatter:document_type": (
        "Markiert den Dokumenttyp explizit (`worksheet`, `presentation` oder `kurzentwurf`) statt ihn "
        "aus anderen Feldern zu erraten. Wird von Blattwerk beim Anlegen neuer Dokumente automatisch "
        "gesetzt; von Hand meist nicht nötig. Aktuell nicht durch den Markdown-Validator wertgeprüft."
    ),
    "frontmatter:lochen": (
        "Aktiviert einen vergrößerten linken Rand für Lochung beim Ausdrucken (`ja`/`nein`, Standard: "
        "`nein`). Aktuell nicht durch den Markdown-Validator wertgeprüft; ungültige Werte werden beim "
        "Rendern stillschweigend als `nein` behandelt."
    ),
    "frontmatter:copyright": (
        "Ersetzt den Standard-Copyright-Text im Footer durch einen eigenen Text. Ohne dieses Feld wird "
        "automatisch ein Standardtext mit aktuellem Jahr eingesetzt."
    ),
    "frontmatter:Stufe": (
        "Rein informatives Feld für die Jahrgangsstufe. **Hinweis:** wird aktuell an keiner Stelle aus "
        "dem Dokument gelesen oder angezeigt -- ohne Wirkung im Build-/Render-Pfad."
    ),
    "frontmatter:worksheet_type": (
        "Rein informatives Feld für eine Dokumentart-Bezeichnung. **Hinweis:** wird aktuell an keiner "
        "Stelle aus dem Dokument gelesen oder angezeigt -- ohne Wirkung im Build-/Render-Pfad."
    ),
    "frontmatter:font_profile": (
        "**Hinweis:** wird aktuell nicht aus dem Dokument gelesen -- die Schriftart wird ausschließlich "
        "über die App-Einstellung gesteuert, nicht über das Frontmatter. Dieses Feld hat aktuell keine "
        "Wirkung im Build-/Render-Pfad."
    ),
    # -- Control-Marker ----------------------------------------------------
    "marker:pagebreak": (
        "`--!` auf einer eigenen Zeile erzwingt einen harten Seiten-/Folienumbruch an dieser Stelle."
    ),
    "marker:framebreak": (
        "`-+` auf einer eigenen Zeile erzeugt im Präsentationsmodus einen neuen Frame (neue Folie), "
        "der den bisherigen Folieninhalt beibehält und um den folgenden Inhalt ergänzt -- nützlich, um "
        "einen Gedanken schrittweise aufzubauen."
    ),
    "marker:slidechromeoff": (
        "`--hf` auf einer eigenen Zeile blendet auf der aktuellen Folie Mini-Header und Footer "
        "(Phasenübersicht + Folienzähler) aus, ohne das globale Präsentationslayout zu verändern -- "
        "nützlich für Folien mit wenig Platz."
    ),
    "marker:sectionmark": (
        "`--# Abschnittsname` setzt den aktuellen Abschnittsnamen für die Footer-Navigation in "
        "Präsentationen. Alles nach `--# ` bis Zeilenende wird als Abschnittstitel übernommen."
    ),
    "marker:vspacer": (
        "`-=<css-länge>` (z. B. `-=0.5cm`, `-=20px`) erzeugt vertikalen Abstand in voller Seiten-/"
        "Spaltenbreite -- nützlich zum manuellen Feintuning des Layouts."
    ),
    "marker:soft_section_break": (
        "`--` auf einer eigenen Zeile markiert einen weichen Abschnittswechsel (Solltrennstelle) ohne "
        "zusätzlichen vertikalen Abstand. Die normale Markdown-Trennlinie `---` ist demgegenüber "
        "**kein** Blattwerk-Kontrollmarker, sondern gewöhnliches Markdown: sie erzeugt ebenfalls einen "
        "Abschnittswechsel, aber zusätzlich mit `1cm` Abstand (per CSS in `assets/worksheet.css`), weil "
        "der Parser sie gar nicht als eigenes Token erkennt."
    ),
    # -- Kurzentwurf ---------------------------------------------------------
    "kurzentwurf:phases": (
        "Ein Kurzentwurf gliedert sich in `#phase`-Abschnitte, deren Name einer der sechs festen "
        "Unterrichtsphasen entsprechen muss (siehe Liste unten), z. B. `#einstieg t=10` für eine "
        "10-minütige Einstiegsphase. `t=<minuten>` ist optional; ohne Zeitangaben wird die Phase ohne "
        "Zeitlabel gerendert. `Hausaufgabe` und `Didaktische Reserve` benötigen nie ein `t=...`."
    ),
    "kurzentwurf:identity_meta": (
        "Titel, Untertitel und globale Startzeit können sowohl im YAML-Frontmatter (`---`-Block) als "
        "auch als einzelne `@title:`/`@subtitle:`/`@start:`-Metazeilen im Dokument gesetzt werden -- "
        "beide Varianten verstehen dieselben deutschen/englischen Alias-Schreibweisen (z. B. "
        "`Stundenthema` für den Titel, `Lerngruppe` für den Untertitel)."
    ),
    "kurzentwurf:legacy_detection_only": (
        "Diese Felder werden derzeit ausschließlich zur Erkennung älterer Kurzentwurf-Dokumente "
        "berücksichtigt (falls kein explizites `document_type: kurzentwurf` gesetzt ist). Sie steuern "
        "weder Inhalt noch Darstellung des gerenderten Kurzentwurfs und sollten für neue Dokumente "
        "nicht als funktionale DSL-Felder verwendet, sondern höchstens als rein organisatorische "
        "Notiz betrachtet werden."
    ),
    "kurzentwurf:markers": (
        "Innerhalb einer Phase gliedern Zeilenmarker den Inhalt in drei Spalten: `S>` (Lernschritte), "
        "`A>` gefolgt von `s<` (Lernaktivität der Lernenden) und `U>` (Lernumgebung/Sozialform). "
        "`ant<` markiert eine antizipierte Schülerreaktion/Fehlvorstellung zum jeweiligen Lernschritt "
        "und sollte nach jedem `s<` gesetzt werden. `---` trennt zwei Segmente innerhalb derselben "
        "Phase; `|` allein auf einer Zeile springt zur nächsten Spalte."
    ),
    # -- Geometry --------------------------------------------------------
    "geometry:block_options": (
        "`:::grid` und `:::geometry` unterstützen die Option `line=solid|dashed` (Standard: `solid`), "
        "die den Linienstil des Rasterhintergrunds selbst steuert -- unabhängig vom gleichnamigen "
        "`pairs[].line`-Feld auf Objektebene (siehe unten), das nur die einzelne Strecke betrifft."
    ),
    "geometry:points": (
        "Einzelne markierte Punkte im Raster. Im Achsenmodus (`axis=true`) werden `x`/`y` als "
        "mathematische Koordinaten interpretiert, sonst `col`/`row` (bzw. `x`/`y` als Alias) als "
        "direkte Rasterkoordinaten. `label` beschriftet den Punkt. `color` (beliebiger CSS-Farbwert) "
        "und `thickness` (positive Zahl) sind optional -- fehlt einer der beiden oder ist er ungültig, "
        "fällt der Punkt auf den bisherigen Theme-Standard zurück, ohne den Build zu blockieren "
        "(Warnung `AN013`/`AN014`)."
    ),
    "geometry:sequence": (
        "Eine Liste aus `x`/`y`-Punkten (nur im Achsenmodus sinnvoll), die als sortierte Polylinie "
        "verbunden werden. `color`/`thickness` gelten für die Verbindungslinie selbst, nicht für "
        "einzelne Punktmarkierungen."
    ),
    "geometry:pairs": (
        "Einzelne Strecken zwischen zwei Punkten (`x1,y1` nach `x2,y2`). `label` beschriftet die "
        "Strecke am Streckenmittelpunkt. `line=solid|dashed` (Standard bei fehlendem/ungültigem Wert: "
        "`dashed`) steuert den Linienstil dieser einzelnen Strecke -- eine eigene, von der "
        "Block-Option `line` unabhängige Ebene; ein ungültiger Wert wird als `AN012` gemeldet. "
        "`color`/`thickness` wie bei `points`."
    ),
    "geometry:functions": (
        "Funktionsgraphen (nur im Achsenmodus). `expr` ist der auszuwertende Funktionsterm, `domain` "
        "der Definitionsbereich als `min:max` (Standard `-10:10`, auch `min..max` erlaubt). `label` "
        "beschriftet den Graphen am rechten (letzten sichtbaren) Kurvenende. `color`/`thickness` wie "
        "bei `points`."
    ),
    # -- Blocktypen ----------------------------------------------------
    "block:material": (
        "Kontext- und Erklärmaterial, das vor einer Aufgabe eingeblendet wird. Optionale `title` "
        "beschriftet die Box."
    ),
    "block:info": (
        "Hinweisbox mit `type=default|warning|note` für unterschiedliche Hervorhebungsstile."
    ),
    "block:task": (
        "Die Hauptaufgabe -- der zentrale Blocktyp eines Arbeitsblatts. `points` vergibt eine "
        "Punktzahl, `time` eine Bearbeitungszeit in Minuten (Ausgabe als `X min`). `work` zeigt die "
        "empfohlene Arbeitsform (`single`/`partner`/`group`, auch deutsche Aliase wie `einzel`), "
        "`action` einen Tätigkeits-Hinweis (`read`/`write`/`calculate`/...) und `hint` einen "
        "Lernhinweis (`tip`/`definition`/`remember`/...) -- jeweils mit passendem Emoji gerendert. "
        "`title` beschriftet die Aufgabe zusätzlich zur automatischen Nummerierung."
    ),
    "block:subtask": (
        "Teilaufgabe zu einem vorangehenden `task`. Muss unmittelbar nach dem zugehörigen `task` als "
        "eigener Top-Level-Block folgen (nicht verschachtelt); mehrere `subtask`-Blöcke werden "
        "automatisch a), b), c) ... nummeriert. Unterstützt `time`/`work`/`action` wie `task`."
    ),
    "block:lines": (
        "Textbasiertes Antwortfeld mit Linien zum Beschriften. `rows=<n>` setzt die Mindestanzahl "
        "sichtbarer Linien (Standard 3); die tatsächliche Anzahl ist `max(rows, sichtbare "
        "Inhaltszeilen)`. `height=<css-länge>` steuert die Linienhöhe. Markdown ist im Inhalt erlaubt; "
        "`§`/`%`/`&`-Zeilenmarker (bzw. `§{...}`/`%{...}`/`&{...}` inline) steuern, ob eine Zeile nur "
        "im Arbeitsblatt, nur in der Lösung oder in beiden erscheint."
    ),
    "block:grid": (
        "Kästchen-/Schreibfeld mit einem Textraster. `rows`/`cols` setzen die Rastergröße (ohne "
        "`cols` wird die Spaltenzahl automatisch aus verfügbarer Breite und `scale` berechnet), "
        "`scale=<css-länge>` die Zellgröße (Standard `0.5cm`). `line=solid|dashed` steuert den "
        "Linienstil des Rasters. Marker-/Inline-Text wird wie bei `lines` nach Arbeitsblatt/Lösung "
        "gefiltert."
    ),
    "block:geometry": (
        "Koordinatensystem für Punkte, Polylinien, Strecken und Funktionsgraphen (siehe Geometry-"
        "Abschnitt unten für die YAML-Payload-Struktur). `axis=true` aktiviert echte Achsen mit "
        "`origin`/`step_x`/`step_y` zur Umrechnung mathematischer Koordinaten in Rasterzellen; "
        "`axis_label_x`/`axis_label_y` beschriften die Achsen (Standard `x`/`y`)."
    ),
    "block:dots": ("Punktraster-Schreibfeld (z. B. für Übungen zur Feinmotorik/Schrift)."),
    "block:space": ("Freier Leerraum ohne Linien/Raster, z. B. für Zeichnungen."),
    "block:table": (
        "Tabellen-Antwortfeld mit YAML-Payload. `headers=\"A|B|C\"` setzt Spaltenüberschriften, "
        "`header_columns=<n>` (Alias `header_cols`) macht die ersten `n` Spalten zu Header-Spalten, "
        "`row_labels=\"...\"` beschriftet Zeilen, `widths=...` steuert Spaltenbreiten, "
        "`alignment=left|center|right|justify` (auch Kurzformen `l`/`r`/`c`/`j`, auch pro Spalte) die "
        "Ausrichtung, `row_height=<css-länge>` die Zeilenhöhe."
    ),
    "block:numberline": (
        "Zahlenstrahl-Antwortfeld mit YAML-Payload (`labels`/`answers`/`arcs`/... je Element mit "
        "`show: \"§\"|\"%\"|\"&\"` für Sichtbarkeit). Optionen wie `min`/`max`, `tick_step`, "
        "`major_every` und `positive_sign` steuern Wertebereich und Beschriftung."
    ),
    "block:mc": (
        "Multiple-Choice-/Wahr-Falsch-Antwortfeld. `options` listet die Antwortmöglichkeiten, "
        "`correct` die richtige(n), `tf`/`true_false` schaltet auf Wahr-Falsch-Layout, `inline` und "
        "`widths` steuern das Layout."
    ),
    "block:cloze": (
        "Lückentext-Antwortfeld. `gap`/`gap_length` steuert den Lückenmodus/-länge, `words`/"
        "`words_multi` die Wortbank-Optionen, `layout` das Layout der Wortbank-Position."
    ),
    "block:matching": (
        "Zuordnungs-Antwortfeld (YAML-only) mit zwei Seiten (`left`/`right` oder `top`/`bottom`, je "
        "nach `layout`/`orientation`) und den Verbindungen in `matches`. `worksheet_matches` zeigt "
        "optional Beispielverbindungen bereits im Arbeitsblatt. `height_mode=content|uniform`, "
        "`lane_align` und `show_guides` steuern das Layout; ein Seiten-Verhältnis von genau einem "
        "Element (1↔N) löst die Warnung `MA001` aus."
    ),
    "block:wordsearch": (
        "Wortsuchrätsel-Antwortfeld. `words` listet die zu versteckenden Wörter, "
        "`diagonal`/`horizontal`/`vertical` steuern erlaubte Richtungen, `min_size`/`min_rows`/"
        "`min_cols` die Mindestrastergröße."
    ),
    "block:solution": (
        "Musterlösungstext. `label=true|false` (Standard `true`) blendet das Label \"Lösung\" ein/aus."
    ),
    "block:columns": (
        "Spaltenlayout für nebeneinander angeordnete Inhalte. `cols=2..6` (Standard 2) setzt die "
        "Spaltenzahl, `widths`/`ratio` die relativen Breiten, `gap=<css-länge>` den Spaltenabstand. "
        "Muss mit `:::nextcol` (Spaltenwechsel) und `:::endcolumns` (Ende) strukturiert werden."
    ),
    "block:nextcol": ("Spaltenwechsel innerhalb eines `:::columns`-Blocks. Keine eigenen Optionen."),
    "block:endcolumns": ("Schließt einen `:::columns`-Block ab. Keine eigenen Optionen."),
    "block:help": (
        "Separate Hilfekarte (eigene Ausgabe, nicht Teil des normalen Arbeitsblatts). `level` (1-99) "
        "gruppiert Hilfen nach Schwierigkeitsstufe, `tag` beeinflusst die automatische Beschriftung "
        "(z. B. `1A`, `1B`), `title` überschreibt den Standardtitel \"Hilfe\". Kanonischer Blockname; "
        "`hilfe` ist ein dokumentierter Alias mit identischen Optionen."
    ),
    "block:hilfe": (
        "Dokumentierter Alias für `help` -- identische Optionen und Bedeutung, nur andere Schreibweise."
    ),
    "block:qrcode": (
        "Klickbarer QR-Code-Link. `url` ist Pflicht (http/https-Link oder relativer Pfad ohne "
        "Leerzeichen). Größenoptionen `w`/`h`/`maxw` (auch `width`/`height`/`max-width`) folgen "
        "derselben CSS-Größen-Logik wie Markdown-Bilder (z. B. `3cm`, `120px`, `60%`, `auto`)."
    ),
    "block:pagebreak": ("Erzwingt einen harten Seiten-/Folienumbruch -- siehe Control-Marker `--!`."),
    "block:framebreak": (
        "Erzeugt im Präsentationsmodus einen neuen Frame mit dem bisherigen plus neuem Inhalt -- "
        "siehe Control-Marker `-+`."
    ),
    "block:slidechromeoff": (
        "Blendet Mini-Header/Footer auf der aktuellen Folie aus -- siehe Control-Marker `--hf`."
    ),
    "block:sectionmark": (
        "Setzt den aktuellen Abschnittsnamen für die Präsentations-Footer-Navigation -- siehe "
        "Control-Marker `--#`."
    ),
    "block:vspacer": ("Erzeugt vertikalen Abstand in voller Breite -- siehe Control-Marker `-=`."),
    # -- Geteilte Optionskonzepte (option:<name>) -- gelten identisch über mehrere Blöcke --
    "option:show": (
        "Steuert die Sichtbarkeit des Blocks: `worksheet` (nur Arbeitsblatt), `solution` (nur "
        "Lösung) oder `both` (Standard, in beiden Ausgaben sichtbar). **Veraltet:** Neue Dokumente "
        "sollten stattdessen `mode=worksheet|solution` verwenden (`show` löst dafür die Warnung "
        "`OP003` aus, bleibt aber weiterhin funktionsfähig)."
    ),
    "option:mode": (
        "Blockweite Sichtbarkeitssteuerung, Nachfolger von `show`: `worksheet` blendet den Block nur "
        "im Arbeitsblatt ein, `solution` nur in der Lösung. Ohne `mode` **und** ohne `show` ist der "
        "Block in beiden Ausgaben sichtbar."
    ),
    "option:align": (
        "Horizontale Ausrichtung des Blockinhalts: `left`/`links`, `right`/`rechts`, "
        "`center`/`mitte`/`zentriert` oder `block`/`blocksatz` (deutsche und englische "
        "Schreibweisen gleichwertig)."
    ),
    "option:work": (
        "Empfohlene Arbeitsform, wird als Emoji + Label gerendert: `single`/`einzel` (👤), "
        "`partner` (👥) oder `group`/`gruppe` (👪). Deutsche und englische Schreibweisen sind "
        "gleichwertig. Ohne Angabe gilt `single`."
    ),
    "option:action": (
        "Tätigkeits-Hinweis, wird als Emoji + Label gerendert (`read`/`lesen` 📖, `write`/"
        "`schreiben` ✍️, `calculate`/`rechnen` 🔢, `draw`/`zeichnen` 📐, `match`/`zuordnen` ↔️, "
        "`exchange`/`austauschen` 💬, `decide`/`entscheiden` ⚖️, `experiment`/`experimentieren` 🧪, "
        "`reflect`/`reflektieren` 🤔). Ohne Angabe wird kein Aktions-Symbol angezeigt."
    ),
    "option:hint": (
        "Lernhinweis, wird als Emoji + Label gerendert (`tip`/`tipp` 💡, `definition` 📘, "
        "`remember`/`erinnerung` 💭, `term`/`fachwort` 📖, `expert`/`expertenaufgabe` 🚀). Ohne "
        "Angabe wird kein Hinweis-Symbol angezeigt."
    ),
    "option:line": (
        "Linienstil des Rasterhintergrunds: `solid` (Standard) oder `dashed`. Nur bei `:::grid`/"
        "`:::geometry` vorhanden -- nicht zu verwechseln mit dem gleichnamigen `pairs[].line`-Feld "
        "in der Geometry-YAML-Payload (dort eigene, unabhängige Einstellung pro Strecke)."
    ),
    "option:title": (
        "Überschreibt die automatisch erzeugte Standardbeschriftung des Blocks mit einem eigenen Text."
    ),
    "option:widths": (
        "Relative Breiten (Gewichte, z. B. `\"2 1\"`) oder feste CSS-Breiten für die Spalten/Elemente "
        "dieses Blocks."
    ),
    "option:scale": (
        "Zellgröße des Rasters als CSS-Länge (Standard `0.5cm`), z. B. `scale=0.4cm` oder `scale=6mm`."
    ),
    "option:rows": (
        "Anzahl Zeilen des Rasters/der Linien. Der genaue Standardwert und ob eine fehlende Angabe "
        "automatisch berechnet wird, hängt vom Blocktyp ab (siehe Tabelle: Spalte \"Standard\")."
    ),
    "option:cols": (
        "Anzahl Spalten des Rasters. Der genaue Standardwert und ob eine fehlende Angabe automatisch "
        "aus verfügbarer Breite berechnet wird, hängt vom Blocktyp ab (siehe Tabelle: Spalte "
        "\"Standard\")."
    ),
    "option:height": (
        "Höhe des Antwortfelds als CSS-Länge (z. B. `4cm`, `120px`). Der genaue Standardwert hängt "
        "vom Blocktyp ab (siehe Tabelle: Spalte \"Standard\")."
    ),
    "option:time": (
        "Geschätzte Bearbeitungszeit, wird als `X min` ausgegeben. Freier Textwert -- üblich, aber "
        "nicht erzwungen, ist eine reine Zahl (Minuten)."
    ),
    "option:tag": (
        "Beeinflusst die automatische Beschriftung mehrerer Hilfekarten zum selben Bezugspunkt (z. B. "
        "`tag=1` erzeugt `1A`, `1B`, ...; ein einzelner Buchstabe erzeugt `1<tag>`, `2<tag>`, ...)."
    ),
    "option:level": (
        "Schwierigkeitsstufe der Hilfekarte (1-99) -- rein organisatorisch, ohne Einfluss auf "
        "Sichtbarkeit oder Reihenfolge."
    ),
    "option:layout": (
        "Steuert ein Layout-Detail des Blocks -- die genaue Bedeutung ist blocktyp-abhängig, siehe "
        "Besonderheit unten."
    ),
    "option:words": (
        "Blocktyp-abhängige Bedeutung, siehe Besonderheit unten."
    ),
    # -- Divergente Optionen: block-eigene Erklärungen (block:<block>.<name>) --
    "block:matching.align": (
        "Bei `matching` deutlich enger als die generische `align`-Option: einziger unterstützter "
        "Wert ist `center` (Standard) -- zentriert Inhalte in den Zuordnungs-Blöcken horizontal und "
        "vertikal. Andere Werte werden aktuell nicht geprüft."
    ),
    "block:qrcode.alignment": (
        "Alias von `align` bei `qrcode` -- identische generische Objekt-Ausrichtung "
        "(`left|right|center|block`), nur andere Schreibweise."
    ),
    "block:table.alignment": (
        "Eigene, von der generischen `align`-Option unabhängige Semantik: steuert die Textausrichtung "
        "je Tabellenspalte, auch als Kurzform pro Spalte (z. B. `alignment=\"l r c c\"` mit `l`/`r`/"
        "`c`/`j` für links/rechts/zentriert/Blocksatz). Aktuell nicht vom Validator geprüft."
    ),
    "block:cloze.gap": (
        "Lückenlängen-Modus: `fixed`/`equal`/`same`/`uniform`/`gleich` erzwingt gleich lange Lücken, "
        "jeder andere Wert (Standard) berechnet die Lückenlänge approximativ aus der Wortlänge."
    ),
    "block:columns.gap": (
        "Horizontaler Abstand zwischen den Spalten als CSS-Länge (z. B. `1cm`)."
    ),
    "block:qrcode.height": (
        "Alias von `h` -- Höhe des QR-Codes, folgt derselben CSS-Größen-Logik wie Bildgrößen in "
        "Markdown (z. B. `3cm`, `120px`, `60%`, `auto`); ungültige Werte werden als `OP002` gemeldet."
    ),
    "block:table.width": ("Gesamtbreite der Tabelle als CSS-Länge."),
    "block:qrcode.width": ("Alias von `w` -- Breite des QR-Codes, siehe `height`/`w`/`h`/`maxw`."),
    # -- Block-spezifische Optionen ohne geteiltes Konzept ------------------
    "block:info.type": (
        "Hervorhebungsstil der Hinweisbox: `default` (Standard), `warning` oder `note`."
    ),
    "block:task.points": ("Vergibt eine Punktzahl für die Aufgabe, wird neben der Aufgabe angezeigt."),
    "block:task.hint": (
        "Siehe `option:hint` -- bei `task` zusätzlich mit passendem Emoji direkt neben der Aufgabe "
        "gerendert."
    ),
    "block:geometry.axis": (
        "Aktiviert ein mathematisches Koordinatensystem mit x-/y-Achse, Tick-Marks und "
        "Achsenbeschriftung (Standard: aus, dann gelten reine Rasterkoordinaten `col`/`row`). "
        "**Wichtig:** `axis=true` wirkt nur zusammen mit einem gültigen `origin` -- fehlt `origin` "
        "oder ist er ungültig, fällt der Block still (ohne Fehler/Warnung) auf den Rasterkoordinaten-"
        "Modus zurück. In diesem Fall werden `functions`-Einträge komplett ignoriert, und `points`/"
        "`pairs` interpretieren ihre `x`/`y`-Werte als `col`/`row` statt als Mathe-Koordinaten."
    ),
    "block:geometry.axis_label_x": ("Beschriftung der x-Achse (Standard `x`), nur wirksam bei aktivem Achsenmodus (siehe `axis`)."),
    "block:geometry.axis_label_y": ("Beschriftung der y-Achse (Standard `y`), nur wirksam bei aktivem Achsenmodus (siehe `axis`)."),
    "block:geometry.origin": (
        "Ursprung des Koordinatensystems im Raster, Format `\"spalte,zeile\"` (z. B. `\"10,10\"`). "
        "**Pflicht, sobald `axis=true` gesetzt ist** -- ohne (oder mit ungültigem) `origin` bleibt der "
        "Achsenmodus trotz `axis=true` inaktiv, siehe Besonderheit dort."
    ),
    "block:geometry.step_x": (
        "Skalierung zwischen mathematischer x-Koordinate und Rasterzellen (Standard `1`), nur bei "
        "`axis=true`."
    ),
    "block:geometry.step_y": (
        "Skalierung zwischen mathematischer y-Koordinate und Rasterzellen (Standard `1`), nur bei "
        "`axis=true`."
    ),
    "block:table.headers": ('Spaltenüberschriften, `|`-getrennt (z. B. `headers="A|B|C"`).'),
    "block:table.header_columns": (
        "Rendert die ersten `n` Spalten im Tabellenkörper als Header-Spalten."
    ),
    "block:table.header_cols": ("Alias von `header_columns`."),
    "block:table.row_labels": ('Zeilenbeschriftungen, `|`-getrennt (z. B. `row_labels="Zeile 1|Zeile 2"`).'),
    "block:table.row_height": ("Zeilenhöhe als CSS-Länge."),
    "block:mc.inline": (
        "Schaltet auf ein kompaktes, horizontal fließendes Layout der Antwortoptionen um "
        "(Standard: aus)."
    ),
    "block:mc.tf": (
        "Schaltet auf Wahr-Falsch-Layout um (akzeptiert u. a. `1`/`true`/`yes`/`on`/`tf`/"
        "`richtigfalsch`/`richtig_false` als \"an\"; Standard: aus)."
    ),
    "block:mc.true_false": ("Alias von `tf`."),
    "block:mc.correct": ("Kennzeichnet die richtige(n) Antwortoption(en)."),
    "block:mc.options": ("Listet die Antwortmöglichkeiten."),
    "block:wordsearch.diagonal": (
        "Erlaubt diagonale Wortplatzierung im Rätsel (Standard: aus). Akzeptiert auch eine "
        "Richtungsliste statt eines einfachen Ein/Aus-Werts."
    ),
    "block:wordsearch.horizontal": (
        "Erlaubt horizontale Wortplatzierung (Standard: aus). Akzeptiert auch eine Richtungsliste."
    ),
    "block:wordsearch.vertical": (
        "Erlaubt vertikale Wortplatzierung (Standard: aus). Akzeptiert auch eine Richtungsliste."
    ),
    "block:wordsearch.min_size": ("Mindestrastergröße (Zeilen und Spalten gemeinsam)."),
    "block:wordsearch.min_rows": ("Mindestanzahl Zeilen des Rätselrasters."),
    "block:wordsearch.min_cols": ("Mindestanzahl Spalten des Rätselrasters."),
    "block:solution.label": ('Blendet das Label "Lösung" vor dem Text ein/aus (Standard: an).'),
    "block:columns.ratio": ("Alias von `widths` -- relative Spaltengewichte."),
    "block:cloze.gap_length": ("Feste Lückenlänge in Zeichen bei `gap=fixed` (Standard `10`)."),
    "block:cloze.words_multi": (
        "Erlaubt Mehrfachauswahl in der Wortbank (Standard: an)."
    ),
    "block:matching.left": ("Linke-Seite-Einträge bei horizontalem Layout, `|`-getrennt."),
    "block:matching.right": ("Rechte-Seite-Einträge bei horizontalem Layout, `|`-getrennt."),
    "block:matching.top": ("Obere-Seite-Einträge bei vertikalem Layout, `|`-getrennt."),
    "block:matching.bottom": ("Untere-Seite-Einträge bei vertikalem Layout, `|`-getrennt."),
    "block:matching.matches": ("Definiert die korrekten Verbindungen zwischen beiden Seiten."),
    "block:matching.links": ("Alias von `left`."),
    "block:matching.worksheet_matches": (
        "Zeigt zusätzlich Beispielverbindungen bereits im Arbeitsblatt (nicht nur in der Lösung)."
    ),
    "block:matching.layout": (
        "Legt fest, ob die beiden Seiten horizontal (`left`/`right`) oder vertikal (`top`/`bottom`) "
        "angeordnet werden."
    ),
    "block:matching.orientation": ("Alias von `layout`."),
    "block:matching.height_mode": (
        "`content` (Standard) richtet jeden Block nach eigenem Inhalt aus; `uniform` macht alle "
        "Blöcke gleich hoch."
    ),
    "block:matching.show_guides": (
        "Blendet gestrichelte Platzhalterblöcke und Canvas-Rand ein (Standard: aus)."
    ),
    "block:matching.lane_align": (
        "Richtet beide Seiten entlang ihrer gemeinsamen Mittelachse aus: `start`, `center` (Standard) "
        "oder `end`."
    ),
    "block:cloze.words": (
        "Position der Wortbank relativ zum Lückentext -- nicht die Lückenwörter selbst (die stehen "
        "im Blockinhalt)."
    ),
    "block:numberline.min": ("Untere Grenze des dargestellten Zahlenbereichs."),
    "block:numberline.max": ("Obere Grenze des dargestellten Zahlenbereichs."),
    "block:numberline.minimum": ("Alias von `min`."),
    "block:numberline.maximum": ("Alias von `max`."),
    "block:numberline.tick_step": ("Abstand zwischen zwei Tick-Marken in Zahlenraum-Einheiten."),
    "block:numberline.ticks": ("Explizite Liste anzuzeigender Tick-Werte."),
    "block:numberline.tick_spacing_mm": ("Physischer Abstand zwischen Tick-Marken in Millimetern."),
    "block:numberline.tick_spacing_cm": ("Physischer Abstand zwischen Tick-Marken in Zentimetern."),
    "block:numberline.tick_spacing": ("Physischer Abstand zwischen Tick-Marken (Einheit im Wert enthalten)."),
    "block:numberline.major_every": ("Jede n-te Tick-Marke wird als Hauptmarkierung hervorgehoben."),
    "block:numberline.max_width_mm": ("Maximale Darstellungsbreite des Zahlenstrahls in Millimetern."),
    "block:numberline.max_width_cm": ("Maximale Darstellungsbreite des Zahlenstrahls in Zentimetern."),
    "block:numberline.full_width": ("Erzwingt volle verfügbare Breite für den Zahlenstrahl."),
    "block:numberline.positive_sign": (
        "Zeigt bei positiven Zahlen explizit ein `+`-Vorzeichen an (Standard: aus)."
    ),
    "block:numberline.signed_positive": ("Alias von `positive_sign`."),
    "block:qrcode.url": (
        "Pflichtoption: Ziel-Link des QR-Codes (http/https-URL oder relativer Pfad ohne "
        "Leerzeichen). Ungültige Werte werden als `QR002` gemeldet, ein fehlender Wert als `QR001`."
    ),
    "block:qrcode.w": (
        "Breite des QR-Codes als CSS-Größe (z. B. `3cm`, `120px`, `60%`, `auto`); ungültige Werte "
        "werden als `OP002` gemeldet."
    ),
    "block:qrcode.h": (
        "Höhe des QR-Codes als CSS-Größe, gleiche Regeln wie `w`."
    ),
    "block:qrcode.maxw": ("Maximale Breite des QR-Codes als CSS-Größe, gleiche Regeln wie `w`."),
    "block:qrcode.max-width": ("Alias von `maxw`."),
}
