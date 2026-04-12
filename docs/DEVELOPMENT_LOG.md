# Development Log (Blattwerk)

Dieses Dokument trackt technische Aenderungen fuer Feature- und Architekturarbeit.

Regel:
- Keine Feature- oder Architekturaenderung ohne Update in diesem Log.
- Bugfix-Only-Changes koennen ohne Eintrag erfolgen.

## [Unreleased]

### Changed
- Architektur-Dokumentrollen getrennt: `docs/ARCHITEKTUR.md` und `docs/ARCHITEKTUR_EINFACH.md` beschreiben nur den Ist-Zustand; Verlaufsinhalte wurden entfernt.
- Guardrails erweitert: Feature-/Architekturaenderungen erfordern jetzt ein gleichzeitiges Update dieses Development-Logs.
- Hauptfenster auf splitbare Zwei-Bereichs-Ansicht erweitert: Vorschau und Schreibbereich koennen einzeln oder gemeinsam angezeigt werden.
- Neuer Schreibbereich als einfacher Markdown-Editor integriert; Aenderungen werden debounced live auf Dateiebene gespeichert (ohne Auto-Refresh der Vorschau).

### Added
- `CHANGELOG.md` als oeffentliche, nutzerorientierte Kommunikation.
- `.github/pull_request_template.md` mit Pflichtfeldern fuer Architektur/Development-Log/Changelog.
- Neues UI-Modul `app/ui/blatt_ui_editor.py` fuer Editor-Ownership (Laden, debounced Speichern, Bereichsumschaltung).

## [History]

### 2026-04-12
- Recent-Files-Ownership auf `app/storage/local_config_store.py` konsolidiert; separater Store entfernt.
- Core-Re-Export-Fassaden entfernt und auf `app/core/wiring.py` als explizite Schnittstelle reduziert.
- Wordsearch-Generierung auf explizites Strategiemodell (`app/core/wordsearch_strategy.py`) umgestellt.
