# Development Log (Blattwerk)

Dieses Dokument trackt technische Aenderungen fuer Feature- und Architekturarbeit.

Regel:
- Keine Feature- oder Architekturaenderung ohne Update in diesem Log.
- Bugfix-Only-Changes koennen ohne Eintrag erfolgen.

## [Unreleased]

### Changed
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
