# Development Log (Blattwerk)

Dieses Dokument trackt technische Aenderungen fuer Feature- und Architekturarbeit.

Regel:
- Keine Feature- oder Architekturaenderung ohne Update in diesem Log.
- Bugfix-Only-Changes koennen ohne Eintrag erfolgen.

## [Unreleased]

### Changed
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

## [History]

### 2026-04-12
- Recent-Files-Ownership auf `app/storage/local_config_store.py` konsolidiert; separater Store entfernt.
- Core-Re-Export-Fassaden entfernt und auf `app/core/wiring.py` als explizite Schnittstelle reduziert.
- Wordsearch-Generierung auf explizites Strategiemodell (`app/core/wordsearch_strategy.py`) umgestellt.
