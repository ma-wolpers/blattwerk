# Development Log (Blattwerk)

Dieses Dokument trackt technische Aenderungen fuer Feature- und Architekturarbeit.

Regel:
- Keine Feature- oder Architekturaenderung ohne Update in diesem Log.
- Bugfix-Only-Changes koennen ohne Eintrag erfolgen.

## [Unreleased]

### Changed
- Grid-Semantik hart getrennt: `grid_field` dient jetzt als textbasiertes Kaestchen-/Schreibfeld mit Marker-Overlay, waehrend `grid_system` das bisherige YAML-basierte Raster/Koordinatensystem (`points`, `pairs`, `functions`, `axis`, `origin`, `step_x`, `step_y`) uebernimmt; `AN004` gilt damit nur noch fuer echte YAML-Pflichttypen.
- Validator und Blattwerker-Guardrails erweitert: markerbasierte Inhalte mit explizitem `§` ohne sichtbares Loesungs-Gegenstueck erzeugen jetzt `AN010`; zusaetzlich ist die Pruefregel in den Blattwerker-Agentvorgaben und im lokalen/CI-Guardrail verankert.
- Lernhilfen-Kartenkopf erweitert: die sichtbare Kartenueberschrift verwendet jetzt dieselbe Labelableitung wie die Task-Verweise und rendert Tags als `Tag - Titel`, inklusive lokaler `help tag=...`-Overrides.
- Task-Header erweitert: `:::task` unterstuetzt jetzt `title=...`; die Kopfzeile rendert `Aufgabe N - Titel` und zeigt den Titel links vor dem Arbeitsmodus-Hinweis.
- Validator-Katalog fuer Task-Optionen erweitert: `title` ist als gueltiger Task-Key freigeschaltet (kein `OP001` mehr fuer `task title=...`).
- Task-/Subtask-Header erweitert: sichtbare `help`/`hilfe`-Bloecke werden jetzt dem jeweils letzten vorangehenden `task`/`subtask` zugeordnet und als rechtsbuendiger Verweis dargestellt; Labelableitung erfolgt automatisch aus der globalen Lernhilfe-Reihenfolge und optionalem Frontmatter-`tag`.
- Lernhilfe-Tagging auf Frontmatter umgestellt: neuer optionaler Meta-Key `tag` steuert die automatische Labelbildung (`1A/1B`, `1A/2A`, `TAG1/TAG2`); zusaetzlich kann `help`/`hilfe` mit blocklokalem `tag=...` die Labelquelle ueberschreiben, und diese lokal getaggten Bloecke werden nicht in die globale Auto-Zaehlung einbezogen.
- Blockoption `key=...` ist nicht mehr Teil des Schemas und wird als unbekannte Option diagnostiziert.
- VSCode-Grammatik synchronisiert: Blockoptions-Key `tag` fuer Lernhilfen ist in der Option-Highlighting-RegEx enthalten.
- Preview-Zoombereich erweitert: minimale Zoomstufe auf 10% gesenkt (zuvor 40%), damit in der Vorschau ein staerkeres Herauszoomen moeglich ist.
- Task-/Subtask-Rendering erweitert: Inhalte in `:::task` und `:::subtask` werden jetzt markerbasiert (`§/%/&`) nach Ausgabeziel (Arbeitsblatt vs. Loesung) gefiltert; ohne Marker bleibt der Default `both` (sichtbar in beiden Modi).
- Validator-Syntaxregel erweitert: Abschnittstrenner `---` und `--` innerhalb offener `:::`-Bloecke werden jetzt als Fehler `BL005` diagnostiziert (Trenner nur auf Top-Level erlaubt).
- Guardrail-Check erweitert: `tools/ci/check_ai_guardrails.py` prueft jetzt die Synchronitaet zwischen Core-Validator (`KNOWN_BLOCK_TYPES`/`BLOCK_ALLOWED_OPTIONS`) und VSCode-Extension-RegExen (Blocktypen + Option-Keys).
- VSCode-Extension-Grammatik synchronisiert: fehlende Option-Keys aus dem Core (u. a. `axis_label_x`, `height_mode`, `words_multi`, `worksheet_matches`, `show_guides`) werden jetzt als Blockparameter hervorgehoben.
- `lines`-Antwortblock erweitert: neue Option `height=<css-laenge>` steuert die konkrete Zeilenhoehe (Pitch) im Linienraster; Validator-Optionen, Renderer-Ausgabe und Tests wurden synchron angepasst.
- Answer-Syntax hart umgestellt: statt `:::answer type=...` gelten jetzt dedizierte Blocktypen (`:::lines`, `:::grid_field`, `:::grid_system`, `:::dots`, `:::space`, `:::table`, `:::numberline`, `:::mc`, `:::cloze`, `:::matching`, `:::wordsearch`); Legacy-Syntax wird als Fehler diagnostiziert.
- Escape-Verhalten fuer Antwortzeilen erweitert: Escaped-Leerzeichen (`\ `) bleiben beim Rendering als sichtbare Platzhalter erhalten (HTML als Non-Breaking-Spaces), damit Muster wie `(\ \ \ \ )` nicht kollabieren.
- Marker-Highlighting konsolidiert: Editor und VSCode-Extension verwenden jetzt konsistent `§/%/&` (statt veralteter `$`-Erkennung); Guardrail-Check prueft zusaetzlich auf Marker-Drift in den relevanten Dateien.
- Validator auf blocktyp-spezifische Key-Mengen umgestellt; `type=` ist in dedizierten Antwort-Blocktypen unzulaessig und wird als Fehler diagnostiziert.
- Render-Wiring umgestellt: Dispatch fuer Antwortflaechen erfolgt direkt ueber den Blocktyp statt ueber `answer type`.
- Migrationswerkzeug `tools/migrate_answer_blocks.py` hinzugefuegt (Dry-Run/Write/Report) und Beispiele auf dedizierte Blocktypen migriert.
- Markdown-Rendering fuer allgemeine Blattwerk-Inhalte vereinheitlicht: in Aufgaben/Material/Info/Loesungen sowie freiem Markdowntext gilt jetzt durchgaengig die Semantik einfacher Umbruch = Shift+Enter und doppelter Umbruch = Enter; Mehrfach-Leerzeilen (3+) werden auf einen Absatzwechsel reduziert.
- Tabellenantworten erweitert: `table`-Block unterstuetzt jetzt `header_columns` (Alias `header_cols`), um fuehrende Body-Spalten als Header-Spalten zu rendern.
- Tabellenantworten erweitert: `table`-Block unterstuetzt jetzt den neuen Key `alignment` (`left|center|right|justify`) fuer die Textausrichtung in Tabellenzellen, inklusive spaltenindividueller Kurzform wie `alignment="l r c c"`.
- Spaltenlayout erweitert: `columns` unterstuetzt jetzt optional `gap` als expliziten horizontalen Spaltenabstand (CSS-Laenge) zusaetzlich zu `cols` und `widths/ratio`.
- Abschnittstrenner erweitert: `--` fungiert jetzt als zusaetzliche Solltrennstelle; `---` erzeugt weiterhin die Solltrennstelle und fuegt im Seitenlayout zusaetzlich einen vertikalen Abstand von `1cm` zwischen Abschnitten ein.
- Lernhilfen-Rendering auf kartenorientierten Fluss umgestellt: Karten erzwingen keinen Seitenumbruch mehr (`break-after: page` entfernt), sodass PDF-Ausgabe als fortlaufendes Dokument mit natuerlichem Seitenwechsel laeuft.
- Running-Elements im Lernhilfen-Builder entkoppelt: Lernhilfen-Pfade koennen PDFs ohne nachtraegliche Kopf-/Fusszeile und ohne Seitenzahlen erzeugen (Arbeitsblattpfad unveraendert).
- Lernhilfen-Vorschau und Lernhilfen-PNG-Export nutzen jetzt ein gemeinsames robustes Cropping gegen nahezu-weisse Seitenreste, damit nur der Kartenbereich sichtbar/gespeichert wird.
- Export-Dialoge fachlich getrennt: eigener Arbeitsblatt-Exportdialog und eigener Lernhilfen-Exportdialog statt gemischtem Modus-Switch.
- Export-Shortcut umgestellt: exportbezogen jetzt durchgaengig `Strg+E`; Enter/KP-Enter loesen Export in den Dialogen nicht mehr aus.
- Lernhilfen-Vorschaufenster erweitert: eigener `Exportieren`-Button in der Fenster-Toolbar, ebenfalls via `Strg+E` ausloesbar.
- Lernhilfen-Vorschau auf durchgehende Stapelansicht umgestellt: Karten werden untereinander in einem Scrollbereich dargestellt; Pfeiltasten springen zur vorherigen/naechsten Lernhilfe.
- Vorschau-Zeile erweitert: neuer `Lernhilfen`-Button direkt neben `Aktualisieren`; Button bleibt sichtbar und wird ohne Lernhilfen im aktiven Dokument deaktiviert.
- UI-Terminologie vereinheitlicht: Nutzertexte von Hilfekarten/Hilfebloecke auf Lernhilfen umgestellt (ohne Aenderung der Markdown-Blocksyntax `help`/`hilfe`).
- Exportmodus `Nur Hilfekarten` erweitert: Exportdialog und Workflow unterstuetzen jetzt `PDF`, `PNG` und `PNG (ZIP)` statt nur `PNG`.
- Hilfekarten-Exportpfade getrennt verdrahtet: `PDF` und `PNG (ZIP)` laufen jetzt ueber dedizierte Help-Cards-Builderpfade statt ueber Worksheet-Exportzweige.
- Neue Ansichtsfunktion in `Ansicht`: `Hilfekartenansicht` oeffnet das separate Hilfekarten-Vorschaufenster direkt aus der Menueleiste.
- Fokusverhalten im Schreibbereich-/Vorschau-Kontext angepasst: Hover ueber die Vorschau zieht den Fokus nicht mehr automatisch; Fokuswechsel erfolgt jetzt erst per Klick (bzw. Fensterwechsel).
- Blattwerker-Agentregel fuer Mathe-Notation ergaenzt: Multiplikation soll konsequent als `·` und Division als `:` ausgegeben werden.
- Blattwerker-Agentregel fuer Tabellen ergaenzt: Tabellen sollen konsequent in Blattwerk-Syntax erstellt werden; Markdown-Tabellen sind zu vermeiden.
- Validator-Syntaxregeln fuer `:::` verschaerft: Nach `:::` ist kein Leerzeichen mehr erlaubt (nur `:::blocktyp` oder `:::`), und verwaiste schliessende Marker ohne offenen Block werden als Fehler diagnostiziert.
- Validator-Markerablauf weiter verschaerft: Verschachtelte `:::`-Bloecke sind jetzt explizit unzulaessig; Marker muessen strikt als oeffnen/schliessen abwechseln, inklusive Fehlerdiagnose fuer Oeffner oder Selbstschliesser innerhalb offener Bloecke.
- Menüzeile wieder auf eigene Custom-Popup-Architektur umgestellt (statt nativer Tk-Menüs): vollständig themefähige Dark-Popups mit verschachtelten Side-Submenus für Datei/Ansicht/Shortcuts.
- Menüinteraktion stabilisiert: offene Popups schließen jetzt zuverlässig bei Klick außerhalb sowie bei Fenster-Deaktivierung (inkl. Alt+Tab).
- Alt-Mnemonics für Top-Menüs wiederhergestellt (`Alt+D`, `Alt+A`, `Alt+S`) inklusive unterstrichener Buchstaben in der Menüzeile.
- Steuerzeile modernisiert: Bereichsauswahl und Dokument-Tabs stehen jetzt in einer gemeinsamen Leiste; die Bereichsauswahl nutzt ein segmentiertes Chip-Design statt klassischer Legacy-Radiobutton-Anmutung.
- Tab-Interaktion angepasst: das Schließen im Tabtitel wurde entfernt; stattdessen gibt es einen kleinen dedizierten Schließen-Button am rechten Rand derselben Dokument-Zeile.
- Theme-Standards modernisiert: Standard-Theme auf `slate_indigo` gesetzt und neue Styles für Control-Strip, Segmente und Notebook-Tabs eingeführt, um braunlastige Legacy-Wirkung zu vermeiden.
- Oeffnen-Pfade (Dateidialog, Recent-Menue, Shortcut `Z`) auf zentralen Dokument-Dispatcher umgestellt; bereits geoeffnete Dateien werden nicht doppelt geoeffnet, melden stattdessen "ist schon offen" und fokussieren den vorhandenen Tab.
- `Z` oeffnet jetzt das juengste noch nicht geoeffnete Markdown aus der Recent-Liste und ueberspringt bereits offene Eintraege.
- Vorschau-Headerzeilen "Blattwerk Vorschau" und "Markdown laden, Vorschau pruefen, danach gezielt exportieren." aus dem Vorschaubereich entfernt; Fenstertitel lautet nun "Blattwerk".
- Cloze-Renderer erweitert: neue Option `words_multi` (Standard `true`) steuert, ob identische Loesungswoerter in der Wortbank mehrfach oder dedupliziert angezeigt werden.
- Completion-Einstellungen terminologisch hart umgestellt: `snippet_*`/`snippets_*` durch `completion_*` ersetzt; obsolete Snippet-Only-Settings entfernt.
- `completion_catalogs` ergänzt Value-Kataloge jetzt automatisch aus Core-`KNOWN_*`-Konstanten statt fester Handliste.
- Interner Editor-Cleanup: verbliebene Snippet-Session-Logik (Placeholder-Markierungen, Tab/Shift-Tab-Feldnavigation, Session-Sync) entfernt, nachdem Snippet-Vorlagen deaktiviert wurden.
- Snippet-Vorlagen im Schreibbereich deaktiviert; Completion zeigt nur noch kontextbezogene Fachvorschläge statt Block-Template-Einfügen.
- `Strg+Shift+.` öffnet nach Einfügen von `::: :::` jetzt die normale Completion statt einer erzwungenen Snippetliste.
- Completion-SSOT-Refactor gestartet: fachliche Kandidatenlisten (Blocktypen, Option-Keys/-Values) werden im Editor nicht mehr statisch gehalten, sondern dynamisch über `app/core/completion_catalogs.py` aus dem Kern abgefragt.
- Completion für Text-Optionen (z. B. `type` in `info`) nutzt jetzt die vollständigen Kern-Kataloge statt UI-lokaler Ableitungen.
- Completion stabilisiert bei Modifier-Key-Releases: Loslassen von `Shift` schließt geöffnete Vorschlagslisten nicht mehr sofort.
- Auto-Completion nach `key=` im Blockkopf/Optionsfluss ergänzt (nicht mehr nur manuell via `Ctrl+Space`).
- Wert-Vorschläge nach `key=` nutzen jetzt dieselbe lokale Decay-Gewichtung wie Blocktyp-Vorschläge.
- Snippet-Fallback im Header-/Optionsfluss stärker begrenzt; `Answer-Lines` wird dort nicht mehr als störender Auto-Vorschlag angeboten.
- Completion-Hotfix für Blockkopf-Kontext abgeschlossen: nach `:::blocktyp ` erscheinen Key-Vorschläge sofort und werden nur ergänzend eingefügt.
- Auto-Completion unterdrückt auf reiner `:::`-Zeile im bereits offenen Block (typischer Blockabschluss), um unerwünschte Vorschläge beim Schließen zu vermeiden.
- Completion zeigt jetzt direkt nach `:::` (ohne Leerzeichen) alle verfügbaren Blocktypen an.
- Blocktyp-Vorschläge werden lokal pro Installation per Nutzungsstatistik mit Zeitverfall gewichtet; Gleichstand folgt der festen Kern-Reihenfolge.
- Nutzungsstatistik wird aus drei Quellen gespeist: Blocktyp-Completion, blocktyptragende Snippet-Annahmen und manuell hinzugefügte Blocktypen beim Speichern (Delta-basiert).
- Einstellungen enthalten nun eine Reset-Aktion für die lokale Completion-Rangfolge.
- Auto-Snippet-Trigger im Schreibbereich erweitert: reagiert jetzt auch auf `:` / `=` / `Enter` und damit besser auf Blockkopf-/Optionskontexte.
- Auto-Snippets in `:::`-Zeilen nur noch für öffnende Blockköpfe (nicht für schließende Marker).
- Bezeichnung im Schreibbereich zurück auf "Struktur" (statt "Folding-Ersatz"), da die Funktion als Outline-Navigation gedacht ist.
- Neuer Editor-Shortcut `Strg+Shift+.`: fügt `::: :::` ein, positioniert den Cursor dazwischen und öffnet direkt die Snippet-Auswahl.
- Unvollständig geschlossene Blöcke werden jetzt als Diagnostik-Fehler `SY002` gemeldet.
- Gegenstück-Markierung von Blockgrenzen aktualisiert jetzt auch bei Cursorbewegung per Pfeiltasten.
- Click-Navigation in Diagnostik- und Struktur-Liste robuster gemacht: auch erneute Klicks auf bereits markierte Einträge triggern den Zeilensprung.
- Snippet-Vorschläge werden jetzt im passenden Kontext automatisch angezeigt (zusätzlich zur manuellen Auslösung).
- Snippet-Liste im Popup verbreitert, damit Vorschlagstexte vollständig lesbar sind.
- Kontextsensitives Snippet-Einfügen ergänzt: innerhalb eines bereits passenden Blocks wird nur der Inhaltsanteil eingefügt statt den Blockkopf zu duplizieren.
- Outline im Schreibbereich als Folding-Äquivalent erweitert: verschachtelte Blocktiefe wird jetzt eingerückt dargestellt und bleibt per Zeilensprung navigierbar.
- Schließende `:::`-Marker werden jetzt wie öffnende Marker farblich hervorgehoben.
- Zusatztext hinter einem schließenden `:::` wird nun als Fehler (`SY001`) markiert (inkl. Zeilenhighlight und Diagnostik-Eintrag).
- Cursor-Kontext in einem `:::`-Block hebt jetzt das zugehörige Gegenstück (öffnend/schließend) visuell mit hervor.
- Hervorhebung des aktiven Snippet-Felds ist jetzt themebasiert (nutzt das aktive UI-Farbprofil statt fixer Highlight-Farbe).
- Aktives Snippet-Feld wird jetzt visuell hervorgehoben, damit die aktuelle Tab-Position im Editor klar erkennbar ist.
- Snippet-Session endet automatisch, sobald der Cursor den aktiven Feldbereich verlässt (neben dem Abschluss per Tab am letzten Feld).
- Snippet-Session mit echten Mehrfach-Platzhaltern eingeführt: `Tab` springt jetzt feldweise durch mehrere Snippet-Felder, `Shift+Tab` zurück.
- Platzhalterbereiche werden als aktive Session im Editor geführt und bei Escape/Klick sauber beendet.
- Snippet-Vorschläge berücksichtigen jetzt den Blockkontext stärker: bei Blockkopf-/Inline-Kontext werden nur fachlich passende Snippets je Blocktyp angeboten (z. B. Answer-Snippet im `answer`-Kontext).
- Completion-Snippets setzen den Cursor nach dem Einfügen jetzt gezielt auf die erste Bearbeitungsstelle (Cursor-Marker im Snippet-Template), statt immer ans Ende zu springen.
- Snippet-Vorschläge werden kontextabhängig gefiltert: Frontmatter nur am Dokumentanfang ohne vorhandenes Frontmatter, Block-Snippets primär in Leerzeile/Block-Kontext.
- Completion-UX im Schreibbereich ausgebaut: Vorschlagsliste ist jetzt direkt über Pfeil hoch/runter, Enter und Tab aus dem Editor steuerbar (ohne Fokuswechsel in die Liste).
- Completion-MVP um Snippet-Einfügen erweitert (Task, Answer-Lines, Help, Frontmatter) und bei manueller Auslösung als Fallback-Vorschläge verfügbar.
- Schreibbereich um Struktur-Navigation als Folding-Äquivalent ergänzt: Frontmatter und Block-Header werden als klickbare Outline-Liste mit Zeilensprung angezeigt.
- Schreibbereich um Syntax-Highlighting erweitert: Frontmatter, Block-Header (`:::`), Blockoptionen (`key=value`) und Marker (`§/$/&`) werden im Editor farblich hervorgehoben.
- Keyword-Vervollständigung als MVP ergänzt: kontextbezogene Vorschläge für Blocktypen, Blockoptionen, `answer type`-Werte und Frontmatter-Felder (manuell per `Ctrl+Space`, zusätzlich leichtes Auto-Triggern beim Tippen).
- Schreibbereich um Live-Diagnostik erweitert: bestehende Validator-Regeln aus `app/core/blatt_validator.py` werden debounced auf den aktuellen Editor-Text angewendet.
- Diagnostiken werden im Schreibbereich visuell auf Zeilenebene markiert (Warnung/Fehler) und in einer klickbaren Liste unter dem Editor angezeigt.
- Editor-Events vereinheitlicht: Laden, Tippen und Speichern triggern jetzt dieselbe Diagnose-Pipeline (inkl. Debounce), damit Status und Markierungen konsistent bleiben.
- Shortcut-Abdeckung der Standardfunktionen erweitert: fehlende Menü-/Ansichtsaktionen erhielten zentrale Bindings in `build_preview_shortcuts`.
- Neue globale Shortcuts ergänzt: `Strg+O` (Markdown öffnen), `Strg+,` (Einstellungen), `Strg+1/2/3` (Bereichsansicht), `Strg+T` (Theme-Zyklus), `Strg+F` (Schriftprofil-Zyklus).
- Theme- und Schriftprofilwechsel über dedizierte zyklische Helfer im Style-Mixin zentralisiert, damit Persistenz/Redraw weiter über bestehende Pfade läuft.
- Nutzerhandbuch-Abschnitt zu Vorschau-Shortcuts auf den aktuellen Stand erweitert.
- Architektur-Dokumentrollen getrennt: `docs/ARCHITEKTUR.md` und `docs/ARCHITEKTUR_EINFACH.md` beschreiben nur den Ist-Zustand; Verlaufsinhalte wurden entfernt.
- Guardrails erweitert: Feature-/Architekturaenderungen erfordern jetzt ein gleichzeitiges Update dieses Development-Logs.
- Hauptfenster auf splitbare Zwei-Bereichs-Ansicht erweitert: Vorschau und Schreibbereich koennen einzeln oder gemeinsam angezeigt werden.
- Neuer Schreibbereich als einfacher Markdown-Editor integriert; Aenderungen werden debounced live auf Dateiebene gespeichert (ohne Auto-Refresh der Vorschau).
- Speicherrueckmeldung im Editor sichtbar gemacht: klare Stati fuer "Ungespeichert", "Speichert…" und "Gespeichert".
- Neuer Datei-Workflow fuer "Neue Markdown-Datei": per Systemdialog Pfad waehlen, Datei mit Standardinhalt erzeugen und direkt oeffnen.
- Hauptfenster-Layout praezisiert: oberhalb des Splits bleibt nur die Markdown-Datei-Zeile; Format-/Gestaltungsoptionen, Navigations- und Export-Buttons wurden in den rechten Vorschau-Bereich verlegt.
- Bereichsumschaltung als zweite bereichsuebergreifende Zeile direkt unter dem Dateipfad positioniert (nicht mehr in der Formatzeile).
- Responsive Zeilenumbruchlogik fuer Vorschau-Controls eingefuehrt: Seitenformat (DIN A4/A5), Farbprofil und Schrift/Größe brechen bei Platzmangel eingerueckt in so viele Zeilen um wie noetig.
- Responsive Zeilenumbruchlogik auf Vorschau-Aktionsleiste erweitert (Navigation, Zoom, Aktualisieren).
- Beenden und Exportieren in die globale Dateipfad-Zeile verschoben.

### Added
- `CHANGELOG.md` als oeffentliche, nutzerorientierte Kommunikation.
- `.github/pull_request_template.md` mit Pflichtfeldern fuer Architektur/Development-Log/Changelog.
- Neues UI-Modul `app/ui/blatt_ui_editor.py` fuer Editor-Ownership (Laden, debounced Speichern, Bereichsumschaltung).
- Diagnostikliste im Schreibbereich mit Zeilen-Navigation per Auswahl.

## [History]

### 2026-04-12
- Recent-Files-Ownership auf `app/storage/local_config_store.py` konsolidiert; separater Store entfernt.
- Core-Re-Export-Fassaden entfernt und auf `app/core/wiring.py` als explizite Schnittstelle reduziert.
- Wordsearch-Generierung auf explizites Strategiemodell (`app/core/wordsearch_strategy.py`) umgestellt.
