# Copilot Instructions (blattwerk)

Arbeite in klarer Dokumenttrennung und halte Guardrails strikt ein.

Pflichtregeln:

1. Architektur-Referenz
- `docs/ARCHITEKTUR.md` und `docs/ARCHITEKTUR_EINFACH.md` beschreiben nur den aktuellen Zustand.
- Keine Abschluss-/Historienlisten in Architekturdokumenten.

2. Development-Log
- Bei Feature- und Architektur-Aenderungen immer `docs/DEVELOPMENT_LOG.md` im selben Zyklus aktualisieren.
- Bugfix-Only-Aenderungen sind davon ausgenommen.

3. Public Changelog
- Nutzerrelevante Aenderungen in `CHANGELOG.md` eintragen.

4. PR-Disziplin
- `.github/pull_request_template.md` verwenden und Checkliste vollstaendig pflegen.

5. Guardrails sind bindend
- `tools/ci/check_ai_guardrails.py` muss lokal und in CI bestehen.

6. Marker-/Tokenizer-Aenderungen immer synchron halten
- Bei Aenderungen an Markierungen/Token (z. B. `§/%/&`, Regex, Syntax-Highlighting, Validator-Diagnostik) muessen Core-Parser/Validator, Blattwerk-Editor und VSCode-Extension im selben Zyklus angepasst werden.
- Nach solchen Aenderungen immer mindestens `pytest-verify` und `guardrails-verify` ausfuehren.

7. Zentrale UI-Module
- KeyBindings in `bw_libs/ui_contract/keybinding.py` zentral halten und modebasiert dokumentieren.
- Pop-up-Regeln in `bw_libs/ui_contract/popup.py` zentral halten.
- Neue Shortcut-/Popup-Features zuerst in den Zentralmodulen definieren, danach in Views anbinden.

8. Strict bw-gui-only-Policy
- Keine lokale tkinter/ttk-Widgetimplementierung in Repos.
- Neue wiederverwendbare GUI-Bausteine zuerst in bw-gui implementieren und erst danach in Repos anbinden.

9. Commit-/Push-Workflow
- Feature-Aenderungen als eigene Commits strukturieren.
- Kein automatisches Pushen; Push bleibt bewusst manuell.

10. Dauerhafter Kurzentwerfer-Nebenstrang
- `feat/add-kurzentwerfer-mod-phase0` ist ein dauerhafter Integrations-/Nebenstrang und wird nicht nach `main` gemerged.
- Blattwerk-Hauptarbeit laeuft auf `main` (empfohlener separater Worktree: `a:/Code/blattwerk-main`).
- Kurzentwerfer-Aenderungen werden im eigenstaendigen Repo `a:/Code/kurzentwerfer` umgesetzt; im Blattwerk-Nebenstrang wird nur der Submodule-Pointer aktualisiert.
- Nebenstrang regelmaessig mit `origin/main` synchronisieren (Merge/Rebase) und danach Guardrails/Tests laufen lassen.
