# Blattwerk (Arbeitsblatt-Generator)

Blattwerk erzeugt aus strukturierten Markdown-Dateien druckfreundliche Arbeitsblätter (PDF, optional Lösung und PNG-ZIP).

## Was dieses README abdeckt

- Zweck des Tools
- Installation & Setup
- Start/Update/Grund-Fehlerbehebung
- Verweise auf weiterführende Doku

## Voraussetzungen

- Windows (die Startpfade hier sind Windows-orientiert)
- Python 3.10+ (empfohlen 3.11+)
- Internetzugang für die Erstinstallation der Pakete

## Installation (Ersteinrichtung)

Im Ordner `blattwerk` ausführen:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Danach kannst du normalerweise direkt per Doppelklick starten.

## Start

### Option A (empfohlen)

- `start-blattwerk.bat` per Doppelklick

### Option B (Terminal)

```powershell
.\.venv\Scripts\Activate.ps1
python blattwerk.py
```

## VS Code Extension (Blattwerk Language Tools)

Die Extension liegt im Projekt unter `vscode-extension/blattwerk-language`.

### Dev Host (lokale Entwicklung)

```powershell
cd vscode-extension/blattwerk-language
npm install
npm run build
```

Danach in VS Code `F5` starten (Extension Development Host).

### VSIX (lokale Installation)

```powershell
cd vscode-extension/blattwerk-language
npm install
npm run build
npx @vscode/vsce package
```

Dann in VS Code: `Extensions: Install from VSIX...`.

### Python-Bridge fuer Diagnosen

Die Extension ruft den Validator ueber Python auf:

```powershell
python -m app.cli.blatt_diagnostics_cli --file <datei.md>
```

Empfohlene VS Code Setting in diesem Repo:

- `blattwerk.diagnostics.pythonCommand = a:/7thCloud/.venv/Scripts/python.exe`

## Kurzer Nutzerfluss

1. App starten.
2. Markdown-Datei öffnen.
3. Vorschau prüfen (Format, Modus, Druckprofil).
4. Exportieren.

## Lokale Konfiguration

- Blattwerk speichert lokale, systemnahe Einstellungen in `app/storage/.state/blattwerk_local_config.json`.
- Diese Datei ist fuer den lokalen Rechner gedacht und wird von Git ignoriert.
- Bestehende Altdateien (`blattwerk_recent.json`, `blattwerk_ui_settings.json`) werden beim Start automatisch migriert und danach entfernt.

Einstellungen aendern:

1. In der App `Datei > Einstellungen...` oeffnen.
2. `Max. zuletzt geoeffnete Dateien` und weitere Nutzeroptionen anpassen.
3. Speichern.

## Update auf neuem Rechner / nach frischem Clone

1. Ordner kopieren/auschecken
2. Installation wie oben ausführen
3. Start über `start-blattwerk.bat`

Hinweis: `.venv` nicht zwischen Rechnern kopieren, immer lokal neu erstellen.

## Parallelbetrieb: Hauptstrang + Nebenstrang

Dieses Repo nutzt fuer die Downstream-Integration mit Kurzentwerfer einen dauerhaften Nebenstrang.

Verbindliche Arbeitsaufteilung:

- `a:/Code/blattwerk`: Hauptarbeit auf Branch `main` (Blattwerk-Hauptstrang).
- `a:/Code/blattwerk`: Integrations-/Nebenstrang `feat/add-kurzentwerfer-mod-phase0` (per Branch-Wechsel im selben Repo).
- `a:/Code/kurzentwerfer`: aktive Kurzentwerfer-Entwicklung im eigenstaendigen Repo.

Wichtige Regeln:

1. Der Nebenstrang wird nicht nach `main` gemerged.
2. Kurzentwerfer-Aenderungen passieren im Kurzentwerfer-Repo, nicht dauerhaft im Submodule-Checkout unter Blattwerk.
3. Wenn ein neuer Kurzentwerfer-Stand integriert werden soll:
	- Kurzentwerfer committen und pushen,
	- im Blattwerk-Nebenstrang den Submodule-Pointer aktualisieren,
	- Pointer-Bump im Nebenstrang committen.
4. Damit der Nebenstrang von Blattwerk profitiert, `origin/main` regelmaessig in den Nebenstrang uebernehmen (Merge oder Rebase) und danach Guardrails/Tests ausfuehren.

Kurzroutine fuer den Nebenstrang:

```powershell
Push-Location a:/Code/blattwerk
git fetch origin
git merge origin/main
git submodule status kurzentwerfer
.\.venv\Scripts\python.exe tools/ci/check_ai_guardrails.py
.\.venv\Scripts\python.exe -m pytest -q
Pop-Location
```

## Häufige Probleme

### `py` wird nicht erkannt

- Python ist nicht installiert oder nicht im PATH.
- Python neu installieren und „Add Python to PATH“ aktivieren.

### PowerShell blockiert Skripte

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Start klappt nicht

- Einmal im Terminal starten, um Fehlermeldung zu sehen:

```powershell
.\.venv\Scripts\Activate.ps1
python blattwerk.py
```

## Dokumentation

- Nutzerhandbuch (Funktionen/Bedienlogik): `docs/NUTZERHANDBUCH.md`
- Markdown-Syntax: `docs/MD_FORMAT.md`
- Formale Grammatik: `docs/GRAMMAR.md`
- Validator und Diagnosecodes: `docs/VALIDATOR.md`
- Agent-Setup und Agent-Erstellung: `docs/AGENT_SETUP.md`
- Setup Zweiter PC (Worktrees + Nebenstrang + KI-Regeln): `docs/SETUP_ZWEITER_PC.md`
- CSS-Anleitung: `docs/CSS_ANLEITUNG.md`
- Architektur (intern): `docs/ARCHITEKTUR.md`
- Architektur (einfach): `docs/ARCHITEKTUR_EINFACH.md`
- Development-Log (technischer Verlauf): `docs/DEVELOPMENT_LOG.md`
- Changelog (oeffentliche Aenderungen): `CHANGELOG.md`
- Copilot-Workflow (Prompt- und Review-Standard): `docs/COPILOT_WORKFLOW.md`

## Lizenz

Dieses Material ist als Open Educational Resource (OER) veröffentlicht unter
Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0):
https://creativecommons.org/licenses/by-sa/4.0/

Copyright (c) 2026 Alex Wolpers
