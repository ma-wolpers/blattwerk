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
- KeyBindings werden zentral in `app/ui/keybinding_registry.py` verwaltet (inkl. Modus-Sicht auf aktive Bindings).
- Pop-up-Verhalten wird zentral in `app/ui/popup_policy.py` verwaltet.
- Neue Shortcuts und neue Pop-ups werden nicht mehr verteilt implementiert, sondern zuerst in diesen Zentralmodulen registriert und dann angebunden.

7. Feature-Commit und Push-Disziplin
- Feature-Aenderungen werden in eigenstaendigen Commits gebuendelt (ein Feature = ein klarer Commit-Block).
- Push erfolgt manuell durch den Nutzer nach eigener Freigabe; kein Auto-Push.
