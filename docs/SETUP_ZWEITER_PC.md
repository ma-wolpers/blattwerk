# Setup Zweiter PC: Blattwerk + Kurzentwerfer Add-on auf main

Diese Anleitung richtet einen zweiten PC so ein, dass du gleichzeitig

- Blattwerk auf `main` weiterentwickeln kannst,
- Kurzentwerfer im eigenen Repo pflegst,
- und Integrationsaenderungen als normale Blattwerk-main-Changes sauber validierst.

## Zielbild

Empfohlene Ordnerstruktur:

- `a:/Code/blattwerk` -> Blattwerk-Repo (main als Integrations- und Hauptbranch)
- `a:/Code/kurzentwerfer` -> Kurzentwerfer-Repo (aktive Facharbeit)

Wichtig:

1. Kurzentwerfer darf als Add-on auf Blattwerk-`main` integriert werden.
2. Kurzentwerfer-Entwicklung passiert weiterhin im eigenstaendigen Repo `a:/Code/kurzentwerfer`.
3. Im Blattwerk-Repo wird der Kurzentwerfer-Submodule-Pointer nachvollziehbar aktualisiert.

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

## 3) Integrationsbasis aktualisieren

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

## 4) Python-Umgebungen einrichten

Blattwerk (einmalig):

```powershell
Push-Location a:/Code/blattwerk
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

Blattwerk main:

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

1. `a:/Code/blattwerk`
2. `a:/Code/kurzentwerfer`

Klare Regel im Alltag:

1. Blattwerk-Features/Fixes in `a:/Code/blattwerk` auf Branch `main`.
2. Kurzentwerfer-Facharbeit nur in `a:/Code/kurzentwerfer`.
3. Integrations-/Pointer-Arbeit in `a:/Code/blattwerk` ebenfalls auf Branch `main`.

## 7) Pointer-Bump-Workflow (Kurzentwerfer -> Blattwerk main)

1. In `a:/Code/kurzentwerfer`: aendern, testen, committen, pushen.
2. In `a:/Code/blattwerk`: Submodule auf neuen Stand ziehen.
3. Guardrails/Tests in Blattwerk laufen lassen.
4. Pointer-Bump auf `main` committen und via normalem PR-/Merge-Fluss integrieren.

Beispiel:

```powershell
Push-Location a:/Code/blattwerk
git submodule update --remote kurzentwerfer
.\.venv\Scripts\python.exe tools/ci/check_ai_guardrails.py
.\.venv\Scripts\python.exe -m pytest -q
git add kurzentwerfer
git commit -m "chore(mod): bump kurzentwerfer submodule"
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

1. Kurzentwerfer-Integration als Add-on auf Blattwerk-main ist explizit geregelt.
2. PR-Template erzwingt weiterhin zentrale Governance-Checks (Doku, Changelog, Tests).
3. Guardrails pruefen weiterhin Integrationskonfiguration und DSL-Trennungsanker fuer das Kurzentwerfer-Submodule.

## 9) Tagesroutine (30 Sekunden)

Blattwerk main aktualisieren:

```powershell
Push-Location a:/Code/blattwerk
git fetch origin
git switch main
git pull --ff-only origin main
Pop-Location
```

Kurzentwerfer-Submodule auf neuesten Stand ziehen:

```powershell
Push-Location a:/Code/blattwerk
git fetch origin
git switch main
git submodule update --remote kurzentwerfer
.\.venv\Scripts\python.exe tools/ci/check_ai_guardrails.py
.\.venv\Scripts\python.exe -m pytest -q
Pop-Location
```

## 10) Fehlerfall und schnelle Reparatur

Wenn der Submodule-Arbeitsbaum unerwartet abweicht:

```powershell
Push-Location a:/Code/blattwerk
git submodule update --init kurzentwerfer
git submodule status kurzentwerfer
Pop-Location
```

Wenn Integrationsaenderungen auf `main` nicht valide sind:

1. Nicht mergen bzw. nicht freigeben.
2. Guardrails/Tests lokal reproduzieren.
3. Submodule-Pointer, Doku und Governance-Dateien konsistent nachziehen.

