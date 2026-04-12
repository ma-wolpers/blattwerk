# Architekturübersicht Blattwerk

Ziel: klare Schichtung ohne Klebercode. Jede fachliche Entscheidung hat genau einen Ort.

## Dokumentregel (verbindlich)

Diese Datei ist die technische Architekturfassung.

Sie ist immer synchron mit [docs/ARCHITEKTUR_EINFACH.md](docs/ARCHITEKTUR_EINFACH.md) zu pflegen.
Änderungen an nur einer der beiden Dateien sind nicht erlaubt.

## Programmkern

Der Programmkern liegt in `app/core`.

Kernaufgaben:
1. Parse (`split_front_matter`, `parse_blocks`)
2. Validate (`inspect_markdown_text`)
3. Render (`render_html`, Block-/Answer-Dispatch)
4. Build (`build_worksheet`, `build_help_cards`)

Zusätzliche Kern-Usecases:
- `diagnostic_warnings.py` (Warnaufbereitung)
- `build_requests.py` (typisierte Build-Schnittstelle)
- `color_mentions.py` (fachliche BW/Farb-Regel)

## Schichtenmodell

| Schicht | Verantwortung | Nicht erlaubt | Primärmodule |
|---|---|---|---|
| `app/core` | Fachregeln, Parse/Validate/Render/Build | UI-Dialoge, Persistenzdetails | `blatt_kern_io_build.py`, `blatt_validator.py`, `blatt_kern_layout_render.py` |
| `app/ui` | Input, View-State, Anzeige | Fachregel-Ownership, Persistenzpolicy | `blatt_ui_*.py` |
| `app/storage` | Laden/Speichern, Persistenzformat, Pfad-/Systemadapter | Render-/Validierungslogik | `local_config_store.py`, `history_paths_adapter.py`, `system_settings_adapter.py` |
| `app/styles` | Profilauflösung, Designnormalisierung, CSS | Dokumentdiagnostik, Persistenzentscheidungen | `blatt_styles.py`, `worksheet_design.py`, `ui_profile_adapter.py` |
| `app/cli` | Adapter auf Kern-API | Regelduplikation | `blatt_diagnostics_cli.py` |

## Ablauf-Invarianten

1. Parse genau einmal.
2. Validate genau einmal.
3. Render genau einmal.
4. Output genau einmal schreiben.
5. Optionaler Postprozess nur mit expliziten Erfolgskriterien.

## Brute-Force-Regel

Verboten als Primärstrategie:
- blindes Retry mit pauschalem `sleep`
- zweite Parser-Implementierung neben dem Kernparser
- stille Fallback-Semantik ohne dokumentierten Vertrag

Erlaubt als Ausnahme:
- Retry nur an I/O-Grenzen
- Retry nur bei klassifizierten transienten Fehlern
- begrenzte Versuche mit nachvollziehbarem Abbruchfehler

Aktueller Status:
- PDF-Retry in `blatt_kern_io_pdf.py` ist klassifiziert und begrenzt (zulässige Ausnahme)
- Wordsearch-Erzeugung nutzt weiterhin harte Suchgrenzen/Heuristiken (`answer_special_wordsearch.py`) und bleibt offene Architekturaufgabe

## Anti-Glue-Regeln

1. Keine Sammel-Import-Fassade in UI.
2. Jede Persistenz-Ressource hat genau eine führende API.
3. Re-Exports im Core sind nur in `app/core/wiring.py` erlaubt.
4. Adapter dürfen transformieren, aber keine fachlichen Entscheidungen übernehmen.
5. UI zeigt Ergebnisse an, Kern liefert Entscheidungsinhalt.

## Leitfragen-Check (Soll = Ja)

1. Macht die GUI etwas außer I/O und View-State?
    - Soll: nein.
2. Gibt es Speichermodule und werden sie konsequent genutzt?
    - Soll: ja, mit eindeutiger API pro Ressource.
3. Weiß jedes Modul nur, was es wissen muss?
    - Soll: ja, nach Schichtvertrag und Modulmatrix.

## Modulmatrix (Wissensgrenzen)

- `app/ui/*`
   - darf: Eventfluss, Dialogzustand, View-State
   - darf nicht: Regeldefinition, Parserdetails, Persistenzschema

- `app/core/*`
   - darf: Dokumentmodell, Regeln, Renderentscheidungen, Buildablauf
   - darf nicht: Tk-Widgets, Theme-UI, Speicherpfadkonfiguration

- `app/storage/*`
   - darf: Persistenzschema, Pfadauflösung, Konfigurationsnormalisierung
   - darf nicht: Render-/Fachentscheidungen

- `app/styles/*`
   - darf: Profil- und Designregeln
   - darf nicht: Dokumentdiagnostik, GUI-Interaktion

## Offene Architekturaufgaben

Aktuell keine offenen Architekturaufgaben aus diesem Review.

Abgeschlossen:
- Recent-Files-Ownership ist auf `local_config_store.py` konsolidiert; separater Store wurde entfernt.
- Core-Re-Export-Fassaden wurden entfernt; explizite Public-Wiring-Schnittstelle ist `app/core/wiring.py`.
- Wordsearch-Generierung nutzt jetzt ein explizites Strategie-/Konfigurationsmodell in `app/core/wordsearch_strategy.py` (statt harter Suchgrenzen).

## Guardrails (Build/Export/CI)

1. Diagnostik-Strenge ist adaptergesteuert und explizit:
   - CLI unterstuetzt `--mode standard|strict|permissive`
   - `standard`: blockiert kritische Diagnostik
   - `strict`: blockiert jede Diagnostik
   - `permissive`: blockiert nur `severity=error`
2. Export-Entscheidungen bleiben im Kern:
   - UI liefert nur Dateipfad/Optionen
   - Blockierlogik wird nicht in UI dupliziert
   - Export-Ziele werden vor dem Schreiben zentral validiert (`app/core/export_path_guardrails.py`)
   - gesperrt sind interne Technikordner wie `.git` oder `.venv`
3. Persistierte JSON-Pfade im Repo bleiben portabel:
   - keine absoluten Systempfade in getrackten State-JSON-Dateien
   - CI prueft das ueber `tools/repo_ci/check_no_absolute_paths.py`
4. Markdown-Bildquellen bleiben portabel:
   - Validator meldet absolute lokale Bildpfade als `PT001`
   - erlaubt bleiben relative Pfade sowie Web-URLs (`http/https`)

## Merge-Checkliste

Vor Merge einer Architektur-relevanten Änderung:
1. Eigentümer der Fachentscheidung benennen.
2. Schichtgrenzen gegen diese Datei prüfen.
3. Prüfen, ob Brute-Force-Regel verletzt wird.
4. Beide Architekturdateien gemeinsam aktualisieren.
