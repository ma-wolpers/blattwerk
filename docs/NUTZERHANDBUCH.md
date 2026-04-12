# Blattwerk – Nutzerhandbuch

Dieses Dokument beschreibt die Bedienung und Funktionalität der App im Alltag.
Installation/Setup steht bewusst in `README.md`.

## 1) Grundidee der Oberfläche

- **Links/oben**: Eingabe und Steuerung (Datei, Modus, Format, Profil)
- **Mitte**: Navigation, Zoom, Aktualisieren
- **Rechts**: Export starten
- **Unten**: Vorschau-Canvas mit Scrollbars und Seitenstatus

## 2) Grundablauf

1. Markdown-Datei laden
2. Vorschau prüfen
3. Einstellungen anpassen (Format/Modus/Profil)
4. Exportdialog öffnen und Ausgabe erzeugen

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
- `4 / 5`: DIN A4 / DIN A5
- `0 / 1`: Seitenbreite / ganze Seite
- `E / N / U`: Einzel / nebeneinander / untereinander
- `- / +`: Zoom
- `Tab`: Aufgabe/Lösung
- `Leertaste`: Vorschau aktualisieren
- `Enter`: Exportdialog öffnen
- `O`: Markdown öffnen
- `Z`: zuletzt geladenes Markdown öffnen
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
