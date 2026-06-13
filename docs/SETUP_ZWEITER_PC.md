# Setup Zweiter PC: Blattwerk mit integriertem Kurzentwurf

Diese Anleitung richtet einen zweiten PC so ein, dass du Blattwerk auf `main` inklusive Kurzentwurf weiterentwickeln und lokal sauber validieren kannst.

## Zielbild

Empfohlene Ordnerstruktur:

- `a:/Code/blattwerk` -> Blattwerk-Repo (main als Hauptbranch)

Wichtig:

1. Kurzentwurf ist Teil von Blattwerk und wird direkt im Blattwerk-Repo gepflegt.
2. Der eingebettete Runtime-Pfad liegt unter `app/core/kurzentwurf_runtime`.
3. Guardrails und Tests werden nur noch im Blattwerk-Repo ausgefuehrt.

## Voraussetzungen

- Git
- Python 3.11+ (3.14 ist ebenfalls ok)
- PowerShell
- VS Code mit GitHub Copilot Chat

## 1) Repo klonen

```powershell
Push-Location a:/Code
git clone https://github.com/ma-wolpers/blattwerk.git blattwerk
Pop-Location
```

## 2) Blattwerk main aktivieren

```powershell
Push-Location a:/Code/blattwerk
git fetch origin
git switch main
git pull --ff-only origin main
git submodule update --init --recursive
Pop-Location
```

Wenn `main` lokal noch nicht existiert:

```powershell
Push-Location a:/Code/blattwerk
git switch -c main --track origin/main
git pull --ff-only origin main
git submodule update --init --recursive
Pop-Location
```

## 3) Arbeitsbasis aktualisieren

```powershell
Push-Location a:/Code/blattwerk
git fetch origin
git switch main
git pull --ff-only origin main
git submodule update --init --recursive
Pop-Location
```

Kontrolle:

```powershell
Push-Location a:/Code/blattwerk
git branch --show-current
Pop-Location
```

## 4) Python-Umgebung einrichten

```powershell
Push-Location a:/Code/blattwerk
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Pop-Location
```

## 5) Erstvalidierung

```powershell
Push-Location a:/Code/blattwerk
.\.venv\Scripts\python.exe tools/ci/check_ai_guardrails.py
.\.venv\Scripts\python.exe -m pytest -q
Pop-Location
```

## 6) VS Code Arbeitsweise

Empfohlenes Multi-Root-Workspace-Set:

1. `a:/Code/blattwerk`

Klare Regel im Alltag:

1. Blattwerk-Features/Fixes in `a:/Code/blattwerk` auf Branch `main`.
2. Kurzentwurf-Funktionen ebenfalls in `a:/Code/blattwerk` auf Branch `main`.
3. Historische Vergleiche mit `a:/Code/kurzentwerfer` sind optional, aber nicht Teil der Routine.

## 7) Routine fuer Kurzentwurf-Aenderungen

1. In `a:/Code/blattwerk`: aendern.
2. Guardrails und Tests lokal ausfuehren.
3. Aenderungen ueber normalen PR-/Merge-Fluss nach `main` integrieren.

Beispiel:

```powershell
Push-Location a:/Code/blattwerk
.\.venv\Scripts\python.exe tools/ci/check_ai_guardrails.py
.\.venv\Scripts\python.exe -m pytest -q
git add .
git commit -m "feat(blattwerk): update integrated kurzentwurf runtime"
git push origin main
Pop-Location
```

## 8) Wie KI-Regeln das Setup schuetzen

Diese Dateien enthalten bindende Regeln fuer KI-Agenten:

- `AGENTS.md`
- `.github/copilot-instructions.md`
- `.github/pull_request_template.md`
- `tools/ci/check_ai_guardrails.py`

Aktive Schutzmechanismen:

1. Kurzentwurf ist als integrierter Dokumenttyp in Blattwerk geregelt.
2. PR-Template erzwingt weiterhin zentrale Governance-Checks (Doku, Changelog, Tests).
3. Guardrails pruefen weiterhin den eingebetteten Kurzentwurf-Runtime-Pfad und die DSL-Trennungsanker.

## 9) Tagesroutine (30 Sekunden)

```powershell
Push-Location a:/Code/blattwerk
git fetch origin
git switch main
git pull --ff-only origin main
.\.venv\Scripts\python.exe tools/ci/check_ai_guardrails.py
.\.venv\Scripts\python.exe -m pytest -q
Pop-Location
```

## 10) Fehlerfall und schnelle Reparatur

Wenn der Arbeitsbaum unerwartet abweicht:

```powershell
Push-Location a:/Code/blattwerk
git status --short
Pop-Location
```

Wenn Aenderungen auf `main` nicht valide sind:

1. Nicht mergen bzw. nicht freigeben.
2. Guardrails/Tests lokal reproduzieren.
3. Runtime-Pfad, Doku und Governance-Dateien konsistent nachziehen.

