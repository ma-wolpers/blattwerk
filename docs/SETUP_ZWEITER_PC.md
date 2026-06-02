# Setup Zweiter PC: Blattwerk + Kurzentwerfer Nebenstrang

Diese Anleitung richtet einen zweiten PC so ein, dass du gleichzeitig

- Blattwerk-Hauptarbeit auf `main` machen kannst,
- den dauerhaften Kurzentwerfer-Integrationsnebenstrang weiterentwickeln kannst,
- und KI-Agenten das Setup nicht versehentlich beschaedigen.

## Zielbild

Empfohlene Ordnerstruktur:

- `a:/Code/blattwerk-main` -> Blattwerk `main` (Hauptstrang)
- `a:/Code/blattwerk` -> Blattwerk `feat/add-kurzentwerfer-mod-phase0` (Nebenstrang)
- `a:/Code/kurzentwerfer` -> Kurzentwerfer-Repo (aktive Facharbeit)

Wichtig:

1. Der Nebenstrang wird nicht nach `main` gemerged.
2. Kurzentwerfer-Entwicklung passiert im eigenstaendigen Repo `a:/Code/kurzentwerfer`.
3. Im Blattwerk-Nebenstrang wird nur der Submodule-Pointer nachgezogen.

## Voraussetzungen

- Git
- Python 3.11+ (3.14 ist ebenfalls ok)
- PowerShell
- VS Code mit GitHub Copilot Chat

## 1) Repos klonen

```powershell
Push-Location a:/Code
git clone https://github.com/ma-wolpers/blattwerk.git blattwerk
git clone https://github.com/ma-wolpers/kurzentwerfer.git kurzentwerfer
Pop-Location
```

## 2) Blattwerk Nebenstrang aktivieren

```powershell
Push-Location a:/Code/blattwerk
git fetch origin
git switch -c feat/add-kurzentwerfer-mod-phase0 --track origin/feat/add-kurzentwerfer-mod-phase0
git submodule update --init --recursive
Pop-Location
```

Wenn der Branch lokal bereits existiert:

```powershell
Push-Location a:/Code/blattwerk
git switch feat/add-kurzentwerfer-mod-phase0
git submodule update --init --recursive
Pop-Location
```

## 3) Blattwerk main als zweiten Worktree anlegen

```powershell
Push-Location a:/Code/blattwerk
git worktree add a:/Code/blattwerk-main main
Pop-Location

Push-Location a:/Code/blattwerk-main
git submodule update --init --recursive
Pop-Location
```

Kontrolle:

```powershell
Push-Location a:/Code/blattwerk
git worktree list
Pop-Location
```

## 4) Python-Umgebungen einrichten

Blattwerk Nebenstrang:

```powershell
Push-Location a:/Code/blattwerk
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Pop-Location
```

Blattwerk main:

```powershell
Push-Location a:/Code/blattwerk-main
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Pop-Location
```

Kurzentwerfer:

```powershell
Push-Location a:/Code/kurzentwerfer
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Pop-Location
```

## 5) Erstvalidierung

Blattwerk Nebenstrang:

```powershell
Push-Location a:/Code/blattwerk
.\.venv\Scripts\python.exe tools/ci/check_ai_guardrails.py
.\.venv\Scripts\python.exe -m pytest -q
git submodule status kurzentwerfer
Pop-Location
```

Kurzentwerfer:

```powershell
Push-Location a:/Code/kurzentwerfer
.\.venv\Scripts\python.exe tools/ci/check_ai_guardrails.py
.\.venv\Scripts\python.exe -m pytest -q
Pop-Location
```

## 6) VS Code Arbeitsweise

Empfohlenes Multi-Root-Workspace-Set:

1. `a:/Code/blattwerk-main`
2. `a:/Code/blattwerk`
3. `a:/Code/kurzentwerfer`

Klare Regel im Alltag:

1. Blattwerk-Features/Fixes nur in `a:/Code/blattwerk-main`.
2. Kurzentwerfer-Facharbeit nur in `a:/Code/kurzentwerfer`.
3. Integrations-/Pointer-Arbeit nur in `a:/Code/blattwerk`.

## 7) Pointer-Bump-Workflow (Kurzentwerfer -> Blattwerk Nebenstrang)

1. In `a:/Code/kurzentwerfer`: aendern, testen, committen, pushen.
2. In `a:/Code/blattwerk`: Submodule auf neuen Stand ziehen.
3. Guardrails/Tests im Blattwerk-Nebenstrang laufen lassen.
4. Pointer-Bump committen und nur auf Nebenstrang pushen.

Beispiel:

```powershell
Push-Location a:/Code/blattwerk
git submodule update --remote kurzentwerfer
.\.venv\Scripts\python.exe tools/ci/check_ai_guardrails.py
.\.venv\Scripts\python.exe -m pytest -q
git add kurzentwerfer
git commit -m "chore(mod): bump kurzentwerfer submodule"
git push origin feat/add-kurzentwerfer-mod-phase0
Pop-Location
```

## 8) Wie KI-Regeln das Setup schuetzen

Diese Dateien enthalten bindende Regeln fuer KI-Agenten:

- `AGENTS.md`
- `.github/copilot-instructions.md`
- `.github/pull_request_template.md`
- `tools/ci/check_ai_guardrails.py`

Aktive Schutzmechanismen:

1. Dauerhafter Nebenstrang ist explizit dokumentiert.
2. PR-Template fordert Side-Thread-Regel explizit ab.
3. Guardrail-Hardstop blockiert main-targeted Kontexte, wenn Kurzentwerfer-Submodule-Artefakte enthalten sind.

## 9) Tagesroutine (30 Sekunden)

Hauptstrang aktualisieren:

```powershell
Push-Location a:/Code/blattwerk-main
git fetch origin
git pull --ff-only origin main
Pop-Location
```

Nebenstrang mit main synchronisieren:

```powershell
Push-Location a:/Code/blattwerk
git fetch origin
git merge origin/main
.\.venv\Scripts\python.exe tools/ci/check_ai_guardrails.py
.\.venv\Scripts\python.exe -m pytest -q
Pop-Location
```

## 10) Fehlerfall und schnelle Reparatur

Wenn der Nebenstrang-Arbeitsbaum im Submodule unerwartet abweicht:

```powershell
Push-Location a:/Code/blattwerk
git submodule update --init kurzentwerfer
git submodule status kurzentwerfer
Pop-Location
```

Wenn versehentlich ein PR Richtung `main` mit Nebenstrang-Artefakten erstellt wurde:

1. Nicht mergen.
2. PR schliessen.
3. Weiterarbeit auf `feat/add-kurzentwerfer-mod-phase0`.
