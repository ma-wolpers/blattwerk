# Agent Guardrails (blattwerk)

Dieses Repository hat verbindliche Leitplanken fuer KI-Programmierer.

Ziel in einfachen Worten:
- Architektur als stabilen Ist-Zustand dokumentieren.
- Aenderungsverlauf getrennt und nachvollziehbar fuehren.
- Oeffentliche Kommunikation konsistent ueber Changelog und Releases.

Verbindliche Regeln:

1. Architektur-Dokumentrollen
- `docs/ARCHITEKTUR.md` und `docs/ARCHITEKTUR_EINFACH.md` enthalten nur den aktuellen Zustand.
- Historie/Abschluesse gehoeren nicht in diese Dateien.

2. Development-Log-Pflicht
- Bei Feature- und Architektur-Aenderungen muss `docs/DEVELOPMENT_LOG.md` im selben Zyklus aktualisiert werden.
- Reine Bugfix-Only-Aenderungen koennen ohne Development-Log-Eintrag erfolgen.

3. Public-Kommunikation
- Nutzerrelevante Aenderungen werden in `CHANGELOG.md` gepflegt.
- PRs verwenden die Checkliste in `.github/pull_request_template.md`.

4. Automatische Gates
- Lokaler Check und CI pruefen die Guardrails ueber `tools/ci/check_ai_guardrails.py`.
- Ein Verstoß blockiert den Build.

5. Marker-/Tokenizer-Konsistenz
- Bei Aenderungen an Marker-/Tokenlogik (z. B. `§/%/&`, Regexe, Syntax-Highlighting, Validator-Diagnostik) muessen Core/Validator, Blattwerk-Editor und VSCode-Extension im selben Zyklus synchron angepasst werden.
- Nach solchen Aenderungen sind mindestens `pytest-verify` und `guardrails-verify` verpflichtend.

6. Zentrale UI-Steuerung
- KeyBindings werden zentral in `bw_libs/ui_contract/keybinding.py` verwaltet (inkl. Modus-Sicht auf aktive Bindings).
- Pop-up-Verhalten wird zentral in `bw_libs/ui_contract/popup.py` verwaltet.
- Neue Shortcuts und neue Pop-ups werden nicht mehr verteilt implementiert, sondern zuerst in diesen Zentralmodulen registriert und dann angebunden.

7. Strict bw-gui-only-Policy
- Keine lokale tkinter/ttk-Widgetimplementierung in Repos.
- Neue wiederverwendbare GUI-Bausteine zuerst in bw-gui implementieren und erst danach in Repos anbinden.

8. Feature-Commit und Push-Disziplin
- Feature-Aenderungen werden in eigenstaendigen Commits gebuendelt (ein Feature = ein klarer Commit-Block).
- Push erfolgt manuell durch den Nutzer nach eigener Freigabe; kein Auto-Push.

9. Dauerhafter Nebenstrang fuer Kurzentwerfer
- Der Branch `feat/add-kurzentwerfer-mod-phase0` ist ein dauerhafter Integrations-/Nebenstrang und darf nicht nach `main` gemerged werden.
- Blattwerk-Hauptarbeit erfolgt im bestehenden Ordner `c:/Users/7thpl/Desktop/Code/blattwerk` auf `main`.
- Dieser Ordner `c:/Users/7thpl/Desktop/Code/blattwerk-side` bleibt der Integrations-/Nebenstrang fuer `feat/add-kurzentwerfer-mod-phase0`.
- Kurzentwerfer-Facharbeit erfolgt im eigenstaendigen Repo `a:/Code/kurzentwerfer`; im Blattwerk-Nebenstrang wird nur der Submodule-Pointer nachgezogen.
- Kein automatisches Erzeugen eines zusaetzlichen `blattwerk-main`-Worktrees oder Parallel-Ordners.
- Nebenstrangpflege beinhaltet regelmaessiges Uebernehmen von `origin/main` in den Nebenstrang (Merge/Rebase) plus anschliessende Guardrail-/Test-Validierung.
