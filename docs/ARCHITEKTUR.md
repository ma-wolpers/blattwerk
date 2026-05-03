# Architekturübersicht Blattwerk

Ziel: klare Schichtung ohne Klebercode. Jede fachliche Entscheidung hat genau einen Ort.

## Dokumentregel (verbindlich)

Diese Datei ist die technische Architekturfassung.

Sie ist immer synchron mit [docs/ARCHITEKTUR_EINFACH.md](docs/ARCHITEKTUR_EINFACH.md) zu pflegen.
Änderungen an nur einer der beiden Dateien sind nicht erlaubt.

Dokumentrollen:
- `docs/ARCHITEKTUR.md` und `docs/ARCHITEKTUR_EINFACH.md` beschreiben nur den aktuellen Architekturzustand.
- Verlaufs- und Aenderungsdokumentation liegt ausschließlich in `docs/DEVELOPMENT_LOG.md`.

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

UI-Zuschnitt im Hauptfenster:
- KeyBindings werden zentral ueber `app/ui/keybinding_registry.py` modelliert und modebasiert nachvollziehbar gehalten.
- Pop-up-Verhalten wird zentral ueber `app/ui/popup_policy.py` mit einheitlicher Lifecycle-/Fokus-Policy gefuehrt.
- Die Hauptansicht verwendet ein horizontales Paned-Layout mit zwei Bereichen: links Schreibbereich, rechts Vorschau.
- Oberhalb des Paned-Layouts fuehrt die UI eine dokumentorientierte Tab-Leiste; jedes geoeffnete Markdown wird als eigener Tab verwaltet.
- Bereichsauswahl (Vorschau/Beides/Schreibbereich) und Tab-Leiste teilen eine gemeinsame Control-Strip-Zeile in `app/ui`; visuelle Segment-/Tab-Stile sind themeseitig zentral in `app/ui/ui_theme.py` definiert.
- Der tab-lokale View-State (u. a. Aufgabe/Loesung, DIN A4/A5, Kontrast/Farbprofil/Schrift, Layout/Fit) liegt in `app/ui` und wird beim Tab-Wechsel explizit geladen/gesichert.
- Der tab-lokale View-State umfasst zusaetzlich Praesentationsoptionen (z. B. Black-Screen-Modus und Folienformat-Presets).
- Der tab-lokale View-State umfasst ebenfalls Zoom, aktive Seite und Canvas-Scrollposition (x/y), damit der Ansichtskontext pro Dokument erhalten bleibt.
- Alle Oeffnungspfade (Dateidialog, Recent-Menue, Shortcut `Z`) laufen ueber einen zentralen Open-Dispatcher in `app/ui`; bei bereits offenen Dateien fokussiert die UI den vorhandenen Tab statt eine zweite Instanz zu erstellen.
- Tab-Schließen ist als Tab-spezifische Interaktion im Notebook selbst umgesetzt (Klick auf `×` im Tabtitel) und bleibt in `app/ui` als reine View-State-Operation ohne Kernlogik.
- Die Vorschau verwendet tab-lokale Cache-Keys aus Dateistand plus Render-Optionen; unveraenderte Tab-Wechsel nutzen den Cache ohne erneuten Build.
- Sichtbarkeit ist ein expliziter View-State (`preview_only`, `both`, `editor_only`) in der UI-Schicht.
- Der Schreibbereich speichert Markdown-Aenderungen debounced direkt auf Dateiebene (UTF-8), ohne automatische Vorschau-Aktualisierung.
- Der Schreibbereich nutzt die Validator-API aus `app/core` direkt fuer debounced Live-Diagnostik; die UI mappt nur auf Zeilenmarkierung und Navigationsliste.
- Syntax-Highlighting und Completion im Schreibbereich liegen als UI-Feature in `app/ui`; fachliche Kandidatenquellen (z. B. bekannte Block-/Antworttypen) kommen aus `app/core` ohne Regelduplikation.
- Completion-Kataloge werden zentral aus `app/core/completion_catalogs.py` abgefragt; `app/ui` darf diese Kataloge nicht als statische Listen duplizieren.
- Ein Folding-Äquivalent wird in `app/ui` als Outline-Navigation umgesetzt (Struktur lesen, Einträge anspringen), ohne den Parser im Kern zu duplizieren.
- Die Vorschau bleibt weiterhin explizit manuell aktualisiert und bezieht ihren Inhalt wie bisher ausschließlich aus dem aktuellen Dateisystemstand.
- `app/core` rendert dokumentmodusabhaengig: Arbeitsblatt-/Loesungsseiten im Worksheet-Pfad, folienbasiertes Rendering im Praesentationspfad (`mode: presentation`) mit Marker-gesteuerten Frame-/Abschnittsregeln.

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

## Dokumentationsgrenzen

Diese Architekturdokumente enthalten keine Historie, keine "zuletzt ergänzt"-Notizen und keine Abschlusslisten.
Historische Änderungen, Migrationsschritte und laufende Arbeitsprotokolle stehen nur im `docs/DEVELOPMENT_LOG.md`.

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
5. Development-Log-Pflicht:
   - keine Feature- oder Architekturänderung ohne Update in `docs/DEVELOPMENT_LOG.md`
   - der Log-Eintrag wird im selben Arbeitszyklus gepflegt

## Merge-Checkliste

Vor Merge einer Architektur-relevanten Änderung:
1. Eigentümer der Fachentscheidung benennen.
2. Schichtgrenzen gegen diese Datei prüfen.
3. Prüfen, ob Brute-Force-Regel verletzt wird.
4. Beide Architekturdateien gemeinsam aktualisieren.
5. Bei Feature- oder Architekturänderung: `docs/DEVELOPMENT_LOG.md` aktualisieren.
