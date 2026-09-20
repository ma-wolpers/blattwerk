# Architekturübersicht Blattwerk

Ziel: klare Schichtung ohne Klebercode. Jede fachliche Entscheidung hat genau einen Ort.

## Dokumentregel (verbindlich)

Diese Datei ist die technische Architekturfassung.

Sie ist immer synchron mit [docs/intern/ARCHITEKTUR_EINFACH.md](docs/intern/ARCHITEKTUR_EINFACH.md) zu pflegen.
Änderungen an nur einer der beiden Dateien sind nicht erlaubt.

Dokumentrollen:
- `docs/intern/ARCHITEKTUR.md` und `docs/intern/ARCHITEKTUR_EINFACH.md` beschreiben nur den aktuellen Architekturzustand.
- Verlaufs- und Aenderungsdokumentation liegt ausschließlich in `docs/intern/DEVELOPMENT_LOG.md`.

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
- `document_types.py`, `document_preview_build.py`, `document_export_build.py`, `document_diagnostics.py` (dokumenttypabhaengige Routing-/Diagnostikadapter)
- `kurzentwurf_runtime/*` (eingebettete Kurzentwurf-DSL-Runtime fuer Parse/Validate/Render/Build)
- `inline_markup/*` (einzige Quelle fuer Inline-Formatierungs-Semantik -- fett/kursiv/unterstrichen/Hervorhebung/durchgestrichen/Hoch-/Tiefstellung/Code/Spoiler/Kommentar; Kurzentwurf ruft sie direkt auf, `blatt_kern_shared_parsing.py`/`answer_special_shared.py` binden sie als python-markdown-Preprocessor ein (`inline_markup/markdown_bridge.py`); `app/ui/editor_marker_shortcuts.py` liest dieselbe Marker-Tabelle fuer die Editor-Tasten, `markdown_conventions.py` fuer die generierte Doku)
- `color_mentions.py` (fachliche BW/Farb-Regel)
- `diagnostic_identity.py`/`diagnostic_acknowledgment.py` (generische, dokumenttypunabhaengige Occurrence-Identitaet fuer abgehakte Warnungen im Editor -- kennt keine Blocktypen/Codes/Dokumentfamilien, nur `code`/`region_id`/`anchor`; jede Diagnosequelle liefert ihre eigene Region/Anker, z. B. `blatt_validator_region.py` fuer Arbeitsblatt-`:::`-Bloecke, `kurzentwurf_runtime/region.py` fuer Kurzentwurf-Phasen)
- `block_computation_cache.py` (generischer, blocktyp-unabhaengiger Cache fuer teure deterministische Blockberechnungen; wird von der Anwendungsschicht geoeffnet, nie von `build_worksheet`/`build_help_cards` selbst, und ueber `inspect_markdown_text(..., cache=...)`/`render_html(..., cache=...)` an Validate- und Render-Schritt durchgereicht, damit beide dasselbe Ergebnis wiederverwenden koennen)
- `operator_legend.py` (einzige Stelle, die weiss, was ein `!!...!!`-Aufgaben-Operator, ein Fach->Operatorenliste- und ein Stufe->Gruppe-Bezug fachlich bedeuten; laedt `data/operatoren/<fach>.json`, versorgt Validator (`OPR001`/`OPR003`), Arbeitsblatt-Legende und Editor-Autocomplete aus demselben `OperatorDataset`/derselben Verfuegbarkeits-Logik. Bewusst **nicht** weiter aufgeteilt trotz > 300 Zeilen -- die drei Konsumenten sind eine fachlich eng zusammengehoerige Einheit; eine Aufteilung (z. B. `operator_catalog.py`/`operator_matching.py`) erfolgt erst bei einem tatsaechlich unabhaengigen zweiten Verantwortungsbereich, nicht vorsorglich)
- `blatt_kern_layout_*.py` (vier Module, einseitige/azyklische Abhaengigkeitskette, keins importiert ein tieferes zurueck): `blatt_kern_layout_estimate.py` (Platzbedarfs-Schaetzung pro Block fuer automatische Spaltenbreiten) -> `blatt_kern_layout_columns.py` (baut darauf auf: `columns`/`nextcol`/`endcolumns`-Rendering, normaler Block-Body) -> `blatt_kern_layout_presentation.py` (baut darauf auf: Folien + vollstaendiges Praesentations-HTML-Dokument) -> `blatt_kern_layout_render.py` (baut darauf auf: `render_html`, der von aussen genutzte Arbeitsblatt/Praesentation-Einstiegspunkt, re-exportiert zusaetzlich `render_columns_container` fuer bestehende Call-Sites). Entstanden aus einem Split der urspruenglichen, 950-zeiligen `blatt_kern_layout_render.py` (siehe `docs/intern/DEVELOPMENT_LOG.md`). `blatt_kern_layout_presentation.py` liegt mit 305 Zeilen minimal ueber der 300-Zeilen-Konvention -- bewusst nicht weiter zerlegt, da der Ueberhang fast vollstaendig aus der eingebetteten MathJax/HTML-Template-Zeichenkette in `_render_presentation_html` stammt, keiner eigenstaendigen zweiten Verantwortlichkeit.

## Schichtenmodell

| Schicht | Verantwortung | Nicht erlaubt | Primärmodule |
|---|---|---|---|
| `app/core` | Fachregeln, Parse/Validate/Render/Build | UI-Dialoge, Persistenzdetails | `blatt_kern_io_build.py`, `blatt_validator.py`, `blatt_kern_layout_render.py` |
| `app/ui` | Input, View-State, Anzeige | Fachregel-Ownership, Persistenzpolicy | `blatt_ui_*.py` |
| `app/storage` | Laden/Speichern, Persistenzformat, Pfad-/Systemadapter | Render-/Validierungslogik | `local_config_store.py`, `history_paths_adapter.py`, `system_settings_adapter.py`, `acknowledged_warnings_store.py` |
| `app/styles` | Profilauflösung, Designnormalisierung, CSS | Dokumentdiagnostik, Persistenzentscheidungen | `blatt_styles.py`, `worksheet_design.py`, `ui_profile_adapter.py` |
| `app/cli` | Adapter auf Kern-API | Regelduplikation | `blatt_diagnostics_cli.py` |

UI-Zuschnitt im Hauptfenster:
- KeyBindings werden zentral ueber `bw_libs/ui_contract/keybinding.py` modelliert und modebasiert nachvollziehbar gehalten.
- Pop-up-Verhalten wird zentral ueber `bw_libs/ui_contract/popup.py` mit einheitlicher Lifecycle-/Fokus-Policy gefuehrt.
- HSM-Vertragslogik fuer Intent-Katalog, Escape-Prioritaet und Transition-Validierung liegt zentral in `bw_libs/ui_contract/hsm.py`; Shortcut-Semantik nutzt den zentralen Intent-Katalog aus `app/ui/ui_intents.py`.
- Die Hauptansicht verwendet ein horizontales Paned-Layout mit zwei Bereichen: links Schreibbereich, rechts Vorschau.
- Der Schreibbereich ist nur interaktiv (editierbar/fokussierbar), wenn ein Dokument tatsaechlich geladen ist -- Single Source of Truth dafuer ist `_editor_document_state` (`app/ui/blatt_ui_editor.py`, Werte `EDITOR_DOCUMENT_NOT_LOADED`/`_LOADING`/`_LOADED` aus `ui_constants.py`), nicht die aktive Dokument-Tab-Auswahl oder `input_var`. Ansichtswechsel (Nur Schreibbereich/Beides) fokussieren das Widget nur bei `EDITOR_DOCUMENT_LOADED`, sonst faellt der Fokus auf das Hauptfenster zurueck. Ein Klick in den deaktivierten Schreibbereich fokussiert ihn ebenfalls nicht (`_on_editor_mouse_click` bricht Tks Klassen-Binding per `"break"` ab), und `_set_editor_document_state()` entzieht einem bereits fokussierten Editor beim Uebergang nach `NOT_LOADED` aktiv den Fokus (nicht beim rein internen, synchronen `LOADING`-Zwischenschritt) -- damit blockieren globale Kurzbefehle (z. B. Datei oeffnen) nie faelschlich durch die Text-Input-Fokus-Sperre. Der Primaer-Ladevorgang (`_load_editor_content`) committet neuen Editorinhalt sowie die zugehoerigen Baselines (Quell-Snapshot, Block-Type-Counts) nur gemeinsam nach vollstaendigem Erfolg; jeder Fehlschlag (Lesefehler eines anderen Dokuments, fehlgeschlagene Baseline-Ermittlung, Exception beim Befuellen) setzt ueber `_reset_editor_widget_to_empty()` konsistent auf leer/`NOT_LOADED` zurueck, nie eine Mischung aus neuem Dokument und alten Baselines.
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
- Der Schreibbereich nutzt die dokumenttypabhaengige Diagnostik-API aus `app/core` direkt fuer debounced Live-Diagnostik; die UI mappt nur auf Zeilenmarkierung und Navigationsliste.
- Syntax-Highlighting und Completion im Schreibbereich liegen als UI-Feature in `app/ui`; fachliche Kandidatenquellen (z. B. bekannte Block-/Antworttypen) kommen aus `app/core` ohne Regelduplikation.
- Completion-Kataloge werden zentral aus `app/core/completion_catalogs.py` abgefragt; `app/ui` darf diese Kataloge nicht als statische Listen duplizieren.
- Ein Folding-Äquivalent wird in `app/ui` als Outline-Navigation umgesetzt (Struktur lesen, Einträge anspringen), ohne den Parser im Kern zu duplizieren.
- Die Vorschau bleibt weiterhin explizit manuell aktualisiert und bezieht ihren Inhalt wie bisher ausschließlich aus dem aktuellen Dateisystemstand.
- `app/core` rendert dokumenttyp- und dokumentmodusabhaengig: Arbeitsblatt-/Loesungsseiten im Worksheet-Pfad, folienbasiertes Rendering im Praesentationspfad (`mode: presentation`) und Kurzentwurf ueber die eingebettete DSL-Runtime.
- Warnungen in der Diagnostik-Treeview unter dem Schreibbereich lassen sich einzeln als gelesen abhaken (Checkbox-Spalte, Kontextmenue). Persistiert wird ueber `app/storage/acknowledged_warnings_store.py`, gekoppelt an "Zuletzt geoeffnet" (Eintrag verschwindet, wenn das Dokument aus `recent_files` faellt). `app/core` erreicht diese Persistenz ausschliesslich ueber den injizierten `AcknowledgedWarningsRepository`-Port (`diagnostic_acknowledgment.py`) -- niemals per Direktimport aus `app/storage`; die UI-Schicht (`blatt_ui_preview.py`/`blatt_ui_export.py`) uebergibt die konkrete Store-Implementierung. Erste Anwendung dieses Port-Musters im Projekt, als Referenz fuer kuenftige core→storage-Anbindungen.
- Bloecke werden ueber den Menuepunkt "Einfuegen" (`Alt+I`, ueber `bw_gui`s natives Mnemonic-System, kein eigener Shortcut-Code) eingefuegt, nicht mehr per Strg+B-Popup. Bewusst "Einfuegen" statt eines block-spezifischen Titels, damit kuenftig auch Nicht-Block-Aktionen (z. B. Seitenumbruch) direkt daneben Platz finden. Die Menuestruktur (Familien-Untermenues + Einzelgaenger) kommt aus `app/core/block_insert_menu_families.py` (`BLOCK_INSERT_FAMILIES`/`BLOCK_INSERT_STANDALONE`) -- eine bewusst rein redaktionelle Praesentationsgruppierung, keine Blocktyp-Taxonomie und keine Grundlage fuer Validierungs-/Domaenenlogik (die bleibt bei `KNOWN_BLOCK_TYPES`/`BLOCK_OPTION_SPECS` in `blatt_validator_constants.py`). Angebunden ueber `app/ui/blatt_ui_block_insert_menu.py` (`BlattwerkAppBlockInsertMenuMixin`), Einfuegetext weiterhin einzig aus `BLOCK_INSERT_SNIPPETS` (`block_insert_snippets.py`). Die Blockerklaerung beim Hovern kommt aus `bw_gui`s generischem `MenuItem.description` (nicht-interaktives, Submenue-positioniertes Flyout, lebt vollstaendig im bestehenden Popup-Stack von `CustomMenuBar` -- kein separat verwalteter Tooltip-Lifecycle mehr wie zuvor). Jedes Menue in der Menueleiste (nicht nur "Einfuegen") ist zusaetzlich per Tastatur bedienbar (Auf/Ab/Rechts/Links/Enter/Escape) -- ebenfalls generisch in `CustomMenuBar` geloest, inklusive eines wiedereintrittsfesten `_focus_watchdog_suspended()`-Kontextmanagers, der die bestehende "Klick-ausserhalb-schliesst-alles"-Ueberwachung waehrend interner Fokus-Uebergaben zwischen Popups pausiert (sonst missverstaendlich als Klick nach aussen gelesen).

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
Historische Änderungen, Migrationsschritte und laufende Arbeitsprotokolle stehen nur im `docs/intern/DEVELOPMENT_LOG.md`.

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
   - keine Feature- oder Architekturänderung ohne Update in `docs/intern/DEVELOPMENT_LOG.md`
   - der Log-Eintrag wird im selben Arbeitszyklus gepflegt

## Merge-Checkliste

Vor Merge einer Architektur-relevanten Änderung:
1. Eigentümer der Fachentscheidung benennen.
2. Schichtgrenzen gegen diese Datei prüfen.
3. Prüfen, ob Brute-Force-Regel verletzt wird.
4. Beide Architekturdateien gemeinsam aktualisieren.
5. Bei Feature- oder Architekturänderung: `docs/intern/DEVELOPMENT_LOG.md` aktualisieren.
