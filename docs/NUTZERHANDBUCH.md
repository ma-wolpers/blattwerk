# Blattwerk – Nutzerhandbuch

Dieses Dokument beschreibt die Bedienung und Funktionalität der App im Alltag.
Installation/Setup steht bewusst in `README.md`.

## 1) Grundidee der Oberfläche

- **Links/oben**: Eingabe und Steuerung (Datei, Modus, Format, Profil)
- **Mitte**: Navigation, Zoom, Aktualisieren
- **Rechts**: Export starten
- **Unten**: Vorschau-Canvas mit Scrollbars und Seitenstatus
- **Schreibbereich** (wenn aktiv): Markdown-Editor mit Live-Speichern und Live-Diagnostik

## 2) Grundablauf

1. Markdown-Datei laden
2. Vorschau prüfen
3. Einstellungen anpassen (Format/Modus/Profil)
4. Exportdialog öffnen und Ausgabe erzeugen

## 2a) Einstellungen (Registerkarten)

- Einstellungen öffnen: `Datei > Einstellungen…` oder `Strg+,`.
- Die Einstellungen sind in Registerkarten organisiert (links scrollbare Tab-Liste, rechts scrollbare Inhalte).
- Es gibt `Anwenden` (speichert sofort und bleibt offen), `Speichern` (speichert und schließt), `Abbrechen` (verwirft nicht gespeicherte Änderungen).
- Wichtige Bereiche:
	- Allgemein (z. B. maximale Zahl zuletzt geöffneter Dateien, Startverhalten)
	- Editor (Snippets, Diagnostik, Outline)
	- Ansicht/Layout, Design/Theme, Export
	- Identität/Copyright und Dokument-Defaults
	- Accessibility, Backup, Shortcut-Gruppen
- Der frühere `Root-Anker (Verlauf)` existiert nicht mehr. Zuletzt geöffnete Dateien werden direkt als normale Dateipfade verwaltet.

## 3) Vorschau – was passiert bei welcher Einstellung?

- **Seitenformat** (`DIN A4` / `DIN A5`) steuert die Seitengröße im späteren Export.
- **Modus** (`Aufgabe` / `Lösung`) steuert, welche Inhalte in der Vorschau gerendert werden.
- **Druckprofil** (`Standard` / `Stärker`) erhöht bzw. reduziert den Kontrast für den Ausdruck.
- **Schrift** steuert die Schriftfamilie für das gesamte Arbeitsblatt.
- **Größe** steuert die Grundschriftgröße (`Klein` / `Normal` / `Groß`). Dabei passen sich die Puffer von Antwortboxen automatisch an (kleiner = enger, größer = luftiger).
- **Ansicht** (`Seitenbreite` / `Ganze Seite`) setzt Fit-Presets; bei manuellem Zoom wird auf Custom gewechselt.
- **Layout** (`Einzelseite` / `Nebeneinander` / `Untereinander`) betrifft nur die Vorschau-Darstellung.
- **AB-YAML Dokumentmodus** (`mode` im Frontmatter):
	- `mode: ws` (Standard) zeigt normale Arbeitsform-Hinweise.
	- `mode: test` blendet `work`-Emoji und `work`-Label in Aufgaben/Teilaufgaben aus (auch in der Loesungsausgabe).
	- `action`- und `hint`-Symbole bleiben sichtbar.

## 4) Wichtige Shortcuts (Vorschau)

- `← / →`: Seitenwechsel
- `↑ / ↓`: Scrollen
- `S`: Druckprofil wechseln
- `F`: Farbprofil wechseln
- `4 / 5`: DIN A4 / DIN A5
- `0 / 1`: Seitenbreite / ganze Seite
- `E / N / U`: Einzel / nebeneinander / untereinander
- `- / +`: Zoom
- `Tab`: Aufgabe/Lösung
- `Leertaste`: Vorschau aktualisieren
- `Enter`: Exportdialog öffnen
- `O`: Markdown öffnen
- `Strg+O`: Markdown öffnen
- `Strg+N`: neue Markdown-Datei
- `Z`: zuletzt geladenes Markdown öffnen
- `Strg+,`: Einstellungen öffnen
- `Strg+1 / Strg+2 / Strg+3`: Nur Vorschau / Vorschau+Schreibbereich / Nur Schreibbereich
- `Strg+T`: Theme wechseln
- `Strg+F`: Schriftprofil wechseln
- `Esc`: App beenden

## 5) Exportdialog-Shortcuts

- `Enter`: Exportieren
- `Esc`: Abbrechen
- `4 / 5`: DIN A4 / DIN A5
- `A / L / B`: Aufgaben / Lösung / Beides
- `S`: Druckprofil wechseln
- `P`: PDF/PNG umschalten
- `D`: Durchsuchen öffnen
- `?`: Shortcut-Hilfe im Dialog ein/ausblenden

## 6) Hinweise zur Druckfreundlichkeit

- Vorschau immer kurz gegenprüfen (Umbrüche, Seitenwechsel, Lesbarkeit).
- Für stärkeren Ausdruck `Stärker` nutzen.
- Bei Bedarf CSS in `assets/worksheet.css` anpassen.

## 7) Farb- und Druckprofile (praktisch erklärt)

- In der GUI steuerst du den Druckkontrast über `Standard` und `Stärker`.
- `Standard` ist für normale Ausdrucke gedacht.
- `Stärker` erhöht Kontrast und Linienstärke (z. B. für schwächere Drucker, Kopien oder schlechte Lichtverhältnisse).
- Empfehlung: Bei knappen Linien, blassen Gittern oder schwer lesbaren Symbolen direkt auf `Stärker` wechseln.

## 8) CSS-Nutzung – was passiert dabei?

- Die Basisgestaltung liegt in `assets/worksheet.css`.
- Beim Export ergänzt Blattwerk dynamische CSS-Overrides (Seitenformat + Druckprofil) automatisch.
- Zusätzlich werden Schriftfamilie und Schriftgröße aus der GUI als CSS-Variablen gesetzt.
- Deshalb gilt praktisch: **GUI-Auswahl hat Vorrang** gegenüber widersprüchlichen Werten in der CSS-Datei.
- Sinnvolle Aufteilung:
	- Layout/Look allgemein in `worksheet.css` pflegen
	- Format und Druckstärke über die GUI steuern
- Für tiefergehende CSS-Anpassungen: `docs/CSS_ANLEITUNG.md`.

## 9) Wo finde ich was?

- Setup/Installation: `README.md`
- Markdown-Syntax: `docs/MD_FORMAT.md`
- CSS-Anpassung: `docs/CSS_ANLEITUNG.md`
- Arbeitsblatt-Regeln (Praxis): `docs/ARBEITSBLATT_NOTIZEN.md`

## 10) Schreibbereich mit Live-Diagnostik

- Beim Tippen im Schreibbereich wird die Diagnostik automatisch mit kurzer Verzögerung aktualisiert.
- Warnungen und Fehler werden zeilenweise farbig markiert.
- Unter dem Editor steht eine Diagnostikliste mit Zeile, Code und Meldung.
- Klick auf einen Eintrag springt direkt zur betroffenen Zeile (auch bei erneutem Klick auf denselben Eintrag).
- Beim Laden und Speichern einer Datei wird die Diagnostik ebenfalls neu berechnet.

## 11) Syntax-Highlighting und Completion im Schreibbereich

- Blattwerk-Syntax wird im Editor farbig dargestellt (Frontmatter, `:::`-Blockkopf, `key=value`-Optionen, Marker `§/$/&`).
- Für Vervollständigung im aktuellen Kontext `Strg+Leertaste` drücken.
- Direkt nach `:::` (ohne Leerzeichen) werden automatisch alle möglichen Blocktypen vorgeschlagen.
- `Strg+Shift+.` fügt `::: :::` ein, setzt den Cursor dazwischen und öffnet sofort die Snippet-Liste.
- Snippet-Vorschläge erscheinen zusätzlich automatisch im passenden Kontext (ohne `Strg+Leertaste`).
- Als passender Kontext gilt aktuell insbesondere:
	- in öffnenden `:::`-Blockkopfzeilen (nicht bei schließenden `:::`)
	- nach `Enter` innerhalb eines Blocks
	- in Frontmatter-Zeilen
	- direkt nach `key=` in Blockoptionen
- Vorschläge orientieren sich am Cursor-Kontext:
	- Blocktyp nach `:::`
	- Blockoptionen nach Blocktyp (z. B. direkt nach `:::answer `)
	- `answer type`-Werte
	- Frontmatter-Feldnamen
- Bei Eingaben mit gedrückter `Shift`-Taste bleibt die geöffnete Vorschlagsliste stabil (kein sofortiges Schließen beim Loslassen von `Shift`).
- Nach `key=` in Blockoptionen erscheinen Vorschläge auch automatisch (nicht nur per `Strg+Leertaste`).
- Wert-Vorschläge nach `key=` nutzen dieselbe lokale Gewichtungsmechanik wie Blocktyp-Vorschläge.
- In Blockkopfzeilen wird nur ergänzend eingefügt (z. B. Key nach `:::answer `), kein zusätzlicher Block-Wrapper.
- Auf einer reinen `:::`-Zeile im bereits offenen Block (typischer Blockabschluss) öffnet kein Auto-Popup.
- Blocktyp-Vorschläge werden lokal pro Installation gewichtet (häufiger und zuletzt genutzt zuerst).
- Gleichstand bei Blocktypen wird über die feste Blattwerk-Standardreihenfolge aufgelöst.
- Vorschlag mit Doppelklick oder `Enter` übernehmen.
- Solange die Vorschlagsliste offen ist, funktionieren `Pfeil hoch/runter`, `Enter` und `Tab` direkt im Editor.
- Bei manueller Auslösung ohne passenden Kontext erscheinen zusätzlich Snippet-Vorschläge (Task, Answer-Lines, Help, Frontmatter).
- Snippets setzen den Cursor nach dem Einfügen automatisch auf die erste sinnvolle Bearbeitungsstelle.
- Snippet-Vorschläge sind kontextabhängig (z. B. Frontmatter-Snippet nur am Dokumentanfang, wenn noch keines vorhanden ist).
- Zusätzlich werden Snippets nach Blocktyp gefiltert, damit nur fachlich passende Vorlagen erscheinen.
- Befindest du dich schon im passenden Block (z. B. `answer`), wird beim Snippet-Einfügen nur der Inhalt ergänzt statt den Blockkopf erneut einzufügen.
- Bei Snippets mit mehreren Feldern springt `Tab` zum nächsten Feld und `Shift+Tab` zurück.
- Das aktive Snippet-Feld ist visuell hervorgehoben.
- Die Feldhervorhebung passt sich dem aktiven Theme an.
- Die Snippet-Navigation endet automatisch, wenn du den Feldfluss verlässt.
- Die lokale Completion-Gewichtung kann in den Einstellungen über `Ranking zurücksetzen` gelöscht werden.
- Störende Snippet-Fallbacks in Blockkopf-/Optionsfluss sind reduziert (z. B. kein automatisches `Answer-Lines`-Snippet im laufenden `answer`-Headerfluss).

## 12) Struktur-Outline

- Unter der Diagnostik gibt es eine Struktur-Liste mit Frontmatter und Blattwerk-Blockköpfen.
- Verschachtelte Blöcke werden eingerückt dargestellt.
- Klick auf einen Eintrag springt direkt zur passenden Zeile im Schreibbereich (auch bei erneutem Klick auf denselben Eintrag).
- Die Struktur-Liste wird beim Tippen, Laden und Speichern automatisch aktualisiert.

## 13) Block-Markierung und Blockabschluss

- Öffnende und schließende `:::`-Marker werden farblich hervorgehoben.
- Wenn der Cursor innerhalb eines `:::`-Blocks steht, werden Start- und Endmarker des Blocks als Paar markiert.
- Nach einem schließenden `:::` darf kein weiterer Text in derselben Zeile stehen.
- Falls doch, erscheint ein Diagnostik-Fehler `SY001` und die Zeile wird entsprechend markiert.
- Offene, nicht geschlossene Blöcke werden als Diagnostik-Fehler `SY002` markiert.
