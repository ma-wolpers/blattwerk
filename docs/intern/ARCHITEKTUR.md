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
- `document_type_registry.py` (reine Daten/Capabilities je Typ), `document_semantics.py` (Typ aus Endung, Konsistenzmarker), `document_type_templates.py` (Startinhalte), `document_preview_build.py`, `document_export_build.py`, `document_diagnostics.py` (dokumenttypabhaengige Routing-/Diagnostikadapter), `plain_markdown_render.py` (eine Pipeline fuer schlichtes Markdown), `save_as_staging.py` (Inhalt fuer Speichern-unter mit Typwechsel)
- `kurzentwurf_runtime/*` (eingebettete Kurzentwurf-DSL-Runtime fuer Parse/Validate/Render/Build). Zellentext-Konvention (einfacher Umbruch = `<br>`, Leerzeile = Absatz, abschliessendes `\` = Umbruch innerhalb eines `s<`-Eintrags): der Parser (`dsl_segments.py`) haelt Leerzeilen innerhalb einer Spalte fest, `cell_text.py` setzt die Marker-Labels (**S:innen**/**Antizipiert:**) und entfernt `\`, `render_html._render_text` baut daraus Absaetze/Listen. `math_support.py` ist die einzige Kurzentwurf-Stelle fuer Formeln: MathJax-`<head>`-Schnipsel (`$$...$$` und `$...$` beide inline, `displayMath` leer) und die Diagnosen `KZF160`/`KZF161` (Region `region.KURZENTWURF_DOCUMENT_REGION_ID`). `render_html.py` (~690 Zeilen) und `validator.py` (~400 Zeilen) liegen ueber der 300-Zeilen-Konvention: `render_html.py` besteht zum Grossteil aus der eingebetteten CSS/HTML-Vorlage, `validator.py` aus der zusammenhaengenden Zeitrechnung -- neue Teilaufgaben werden in eigene Module ausgelagert statt dort ergaenzt.
- `inline_markup/*` (einzige Quelle fuer Inline-Formatierungs-Semantik -- fett/kursiv/unterstrichen/Hervorhebung/durchgestrichen/Hoch-/Tiefstellung/Code/Spoiler/Kommentar/Worterklaerung (`word_notes.py`, geschuetzte Span-Familie); Kurzentwurf ruft sie direkt auf, `blatt_kern_shared_parsing.py`/`answer_special_shared.py` binden sie als python-markdown-Preprocessor ein (`inline_markup/markdown_bridge.py`); `app/ui/editor_marker_shortcuts.py` liest dieselbe Marker-Tabelle fuer die Editor-Tasten, `markdown_conventions.py` fuer die generierte Doku)
- `color_mentions.py` (fachliche BW/Farb-Regel)
- `diagnostic_identity.py`/`diagnostic_acknowledgment.py` (generische, dokumenttypunabhaengige Occurrence-Identitaet fuer abgehakte Warnungen im Editor -- kennt keine Blocktypen/Codes/Dokumentfamilien, nur `code`/`region_id`/`anchor`; jede Diagnosequelle liefert ihre eigene Region/Anker, z. B. `blatt_validator_region.py` fuer Arbeitsblatt-`:::`-Bloecke, `kurzentwurf_runtime/region.py` fuer Kurzentwurf-Phasen)
- `block_computation_cache.py` (generischer, blocktyp-unabhaengiger Cache fuer teure deterministische Blockberechnungen; wird von der Anwendungsschicht geoeffnet, nie von `build_worksheet`/`build_help_cards` selbst, und ueber `inspect_markdown_text(..., cache=...)`/`render_html(..., cache=...)` an Validate- und Render-Schritt durchgereicht, damit beide dasselbe Ergebnis wiederverwenden koennen)
- `operator_legend.py` (einzige Stelle, die weiss, was ein `!!...!!`-Aufgaben-Operator, ein Fach->Operatorenliste- und ein Stufe->Gruppe-Bezug fachlich bedeuten; laedt `data/operatoren/<fach>.json`, versorgt Validator (`OPR001`/`OPR003`), Arbeitsblatt-Legende und Editor-Autocomplete aus demselben `OperatorDataset`/derselben Verfuegbarkeits-Logik. Bewusst **nicht** weiter aufgeteilt trotz > 300 Zeilen -- die drei Konsumenten sind eine fachlich eng zusammengehoerige Einheit; eine Aufteilung (z. B. `operator_catalog.py`/`operator_matching.py`) erfolgt erst bei einem tatsaechlich unabhaengigen zweiten Verantwortungsbereich, nicht vorsorglich)
- `blatt_kern_layout_*.py` (vier Module, einseitige/azyklische Abhaengigkeitskette, keins importiert ein tieferes zurueck): `blatt_kern_layout_estimate.py` (Platzbedarfs-Schaetzung pro Block fuer automatische Spaltenbreiten) -> `blatt_kern_layout_columns.py` (baut darauf auf: `columns`/`nextcol`/`endcolumns`-Rendering, normaler Block-Body) -> `blatt_kern_layout_presentation.py` (baut darauf auf: Folien + vollstaendiges Praesentations-HTML-Dokument) -> `blatt_kern_layout_render.py` (baut darauf auf: `render_html`, der von aussen genutzte Arbeitsblatt/Praesentation-Einstiegspunkt, re-exportiert zusaetzlich `render_columns_container` fuer bestehende Call-Sites). Entstanden aus einem Split der urspruenglichen, 950-zeiligen `blatt_kern_layout_render.py` (siehe `docs/intern/DEVELOPMENT_LOG.md`). `blatt_kern_layout_presentation.py` liegt mit 305 Zeilen minimal ueber der 300-Zeilen-Konvention -- bewusst nicht weiter zerlegt, da der Ueberhang fast vollstaendig aus der eingebetteten MathJax/HTML-Template-Zeichenkette in `_render_presentation_html` stammt, keiner eigenstaendigen zweiten Verantwortlichkeit.

## Dokument-Invarianten

Jede Invariante hat genau eine Implementierung; Guardrail-Tests verhindern lokale Sonderregeln.

- **I1 – Typidentitaet.** Der Typ einer gespeicherten Datei kommt ausschliesslich aus der Endung (`.abw` worksheet, `.pbw` presentation, `.kbw` exam, `.ebw` kurzentwurf, `.md` markdown; Gross/Klein egal). Einzige Zugaenge: `document_semantics.type_for_path`/`type_for_tab`; in der UI nur `BlattwerkDocumentTypeMixin._read_document_type` (`app/ui/blatt_ui_document_type.py`). `tab_state["document_type"]` ist bei gespeicherten Dateien nur Cache und wird bei jedem Anwenden aus dem Pfad gesetzt. Unbekannte Endung: Rueckfrage im zentralen Oeffnen-Pfad (`_open_input_path`); bei Zustimmung gilt der Tab voruebergehend als Markdown (`_interpreted_as_markdown_paths`, nie persistiert), Speichern/Autosave schreiben nie in die Originaldatei, sondern fuehren zu Speichern-unter mit `.md`. Inhalt bestimmt nie den Typ.
- **I2 – Konsistenzmarker `document_type`.** Pflicht nur in den vier Blattwerk-Endungen, optional in `.md`. Einzige Interpretation: `canonicalize_document_type` (Absent bei fehlend/`null`/leer, Invalid bei jedem Nicht-String und unbekannten Werten, sonst kanonischer Typ; Aliase nur `arbeitsblatt`, `slide_deck`, `lesson_plan`). Diagnosen in `marker_diagnostics`, vor dem typspezifischen Validator: FM008 (passt nicht zur Endung, alle Endungen), FM009 (fehlt, nur Blattwerk-Endungen), FM010 (ungueltig). Templates, Quick-Fixes, Migration und Speichern-unter zwischen Blattwerk-Typen schreiben den kanonischen Wert; Speichern-unter nach `.md` laesst ihn unveraendert (FM008 danach ist gewollt).
- **I3 – Kein Frontmatter-`mode`.** Typbedingtes Verhalten steht nur als Capability in der Registry: `slide_layout` (Folien), `solutions_renderable` (keine Loesungsfassung bei Praesentationen), `work_hints` (keine Sozialform-Icons bei Klausuren). Renderer erhalten `document_type`; `app/styles` erhaelt nur `slide_layout: bool`. Die Fassung (Arbeitsblatt/Loesung) ist ausschliesslich GUI-/Export-Zustand (`include_solutions`), nie persistiert. Die Block-Option `mode=`/`show=` ist davon unabhaengig. Historisches `mode` liest nur die Migration (geplant: `migration/legacy_decode.py`). Guardrail: `tests/test_guardrail_no_frontmatter_mode.py`.
- **I4 – Gemeinsamer Punktkern.** `points_model.build_points_model(blocks)` ist die einzige semantische Interpretation von `points=` (Einheiten task + folgende subtasks, Ende auch an `aidsplit`; effektive Punkte: ohne bepunktete Subtasks `task.points`, vollstaendig bepunktete Subtasks = Summe, `task.points` darf dann fehlen, Abweichung = PK001, teilweise bepunktet = PK004, jeweils `effective=None`; `Decimal`). Der Renderer zeigt nur `points_display` (Originaltext). `solution_items.py` ist die einzige Zuordnung von `:::solution` (naechste vorangehende Aufgabe/Teilaufgabe, Stopp an `aidsplit`, `target=task|<buchstabe>` innerhalb der Einheit) und die einzige `(xP)`-Regex. Diagnosen in `blatt_validator_points.py` (nur `worksheet`/`exam`; `inspect_markdown_text(..., document_type=...)`). Guardrail: `tests/test_points_model.py` (kein direktes Lesen der `points`-Option ausserhalb von `points_model`).
- **I5 – Hilfsmittel-Trenner `--hm`.** Kontrollmarker (`CONTROL_MARKERS`, Pseudoblock `aidsplit`), vom Parser typunabhaengig erzeugt. Einzige Semantik: `document_semantics.resolve_aid_split(blocks, document_type)` -- nur bei Capability `aid_split` (Klausur), genau einmal, Position nach `aid_split_position_problem` (Aufgabe davor und danach, nicht in `:::columns`, naechster aufgabenbezogener Block ist `task`). `annotate_aid_parts` setzt fuer den Renderer die Teilmarken A (Dokumentanfang) und B (am Trenner); `_render_aid_part` rendert Teil B mit dem vorhandenen `ab-pagebreak`, ohne Annotation nichts. Die Loesungszuordnung (`solution_items`) und die Einheiten im Punktmodell stoppen an `aidsplit`. Diagnosen KL001/KL002/KL004/KL005 in `blatt_validator_exam.py`.
- **Klausur-Auswertung.** `exam_analysis.analyze_exam` (Blaetter aus `points_model`: bepunktete Teilaufgaben mit eigener oder geerbter AFB, sonst der Task; Teile nur bei gueltigem Split). Prozente immer bezogen auf die Gesamtpunktzahl und nur bei vollstaendiger Auswertung mit Gesamtpunkten > 0; `format_analysis_lines` ist die eine Textform fuer Editor-Panel (`app/ui/blatt_ui_exam_overview.py`) und Erwartungshorizont. KL003/KL006 nutzen dieselbe Blatt-Logik.
- **Erwartungshorizont.** `exam_expectation_horizon.py` nutzt nur `solution_items`, `points_model`, `exam_analysis` und `resolve_aid_split`; kein Aufgabentext. Blockierende Diagnosen verhindern den Export (`ValueError`), SL005/SL007 sind Export-Warnungen (in `_SURFACED_COMPILE_WARNING_CODES`). PDF ueber `write_pdf_from_html`, HTML direkt. In der UI eine Inhaltsoption "Erwartungshorizont" im Arbeitsblatt-Exportdialog, nur fuer Typen mit Capability `expectation_horizon` (Klausur) und nur als PDF/HTML.
- **Schlichtes Markdown (`.md`).** python-markdown mit `tables`, `fenced_code`, `sane_lists`; kein `nl2br`, kein vollstaendiges GFM, keine Blattwerk-Inline-Marker, Raw HTML durchgereicht; Formeln `$…$`/`$$…$$` ueber `math_span_protection` + MathJax. Frontmatter (Grenzregel I6) wird nicht gerendert, `Titel` wird Dokumenttitel, alle anderen Keys inkl. `mode` werden ignoriert. Blattwerk-Syntax bleibt Text. Vorschau, HTML, PDF und PNG nutzen `render_plain_markdown_html`. Kein Validator, keine Lernhilfen, keine Block-Completion.
- **Registry.** `DocumentTypeSpec` ist reine Daten-/Capability-Beschreibung ohne Builder und ohne UI-Importe; `export_formats` ist ein geordnetes Tupel (UI-Reihenfolge) und ausdruecklich **keine** Export-Format-Registry -- die Format-Implementierungen bleiben in den Exportdialogen, deren Erlaubt-Listen aus der Registry abgeleitet sind.
- **I6 – Frontmatter-Kern.** `app/core/frontmatter.py` ist die einzige Grenzbestimmung (`frontmatter_bounds`): erste Zeile nach optionalem BOM exakt `---`, Schluss an der naechsten Zeile `---` oder `...` (jeweils mit optionalem Leerraum), Zeilen nur an `
` getrennt. `split_front_matter` (Parser) und `_extract_validation_content_and_base_line` (Validator) delegieren dorthin. YAML laedt `load_frontmatter_yaml`: zur Laufzeit wie `yaml.safe_load` (letzter Wert bei Duplikaten), in Edit-/Migrationspfaden strikt (`reject_duplicates=True`, eigener `SafeLoader`-Subtyp mit expliziter Duplikat-Pruefung auf jeder Ebene). `app/core/frontmatter_edit.py` (`FrontmatterEditor`) ist die einzige Edit-Engine fuer Frontmatter-Schluessel: zerlegt den Rumpf in Top-Level-Eintraege (Spalte-0-`key:` plus eingerueckte Fortsetzung), ersetzt/entfernt/fuegt nur ganze Eintraege ein und verifiziert (a) die erwartete YAML-Semantik, (b) unveraenderte Zeichen ausserhalb der editierten Eintraege, (c) `EditUnsafe` bei Duplikaten, Flow-Mappings, Listen oder YAML-Fehlern. Bewusst ausgenommen: der Kurzentwurf-DSL-Kopf (`kurzentwurf_runtime/dsl_frontmatter.py`) -- er liest kein YAML, sondern tolerant einzelne Metazeilen (auch nach Leerzeilen); `FrontmatterEditor.ensure_frontmatter` verweigert deshalb Dokumente, die nach Leerzeilen mit `---` beginnen.

## Dateiendungs-Migration (`app/core/migration/`)

Migriert alte Blattwerk-`.md`-Dateien auf die typgebundenen Endungen. Alles in diesem Paket betrifft nur Altbestaende.

- **Klassifikation** (`classify.py`): reine Funktion `classify(name, text)`, dieselbe fuer GUI und CLI. Explizite Signalmatrix (starke Signale `S_LEGACY_PRES/TEST`, `S_DT`, `S_KZ_PATH/META/DSL`, `S_WS`; `M_DT_MD`, `X_DT_INVALID`; schwache `W_*`), feste Pruefreihenfolge ohne Typ-Prioritaet: ungueltiger Marker → `ungueltiger_marker`; `document_type: markdown` → `kein_blattwerk` bzw. `conflict`; mehrere Ziele → `conflict`; genau ein Ziel → `sicher` (Kurzentwurf + `S_WS` → `conflict`); nur `S_WS` → `sicher` worksheet; sonst `unklar`/`kein_blattwerk`. Nur `sicher` wird je migriert. Body-Signale nur ausserhalb von Code-Fences und nicht auf ≥ 4 Leerzeichen/Tab eingerueckten Zeilen. `S_WS` ist das groesste False-Positive-Risiko: mehrdeutige Blocknamen (`info`, `raw`, `table`, `columns`, `space`, `help`) zaehlen nicht, der Dry-Run listet `S_WS`-Treffer gesondert. Historisches `mode` liest nur `legacy_decode.py`.
- **Plan** (`plan.py`): Scan mit Ausschluessen (`.git`, versteckt per `.` oder HIDDEN/SYSTEM, Symlinks/Junctions/Reparse Points nie betreten, `*Lerngruppen*`, `--exclude`) und technischen Schutzgrenzen als Skip-Gruende (`uebersprungen_groesse` ab 20 MB, `nicht_utf8`, `nicht_lokal` fuer Cloud-Platzhalter, ungelesen). `plan.json` enthaelt Versionen (Schema, Klassifikator, Rewrite), Identitaets-Fingerprint (Groesse, `mtime_ns`, SHA-256, `st_dev`/`st_ino`), Metadaten-Snapshot (`atime` vor dem Lesen, `mtime`, Creation Time, Attribute, Read-only) und Rewrite-Hash. `--write` fuehrt genau diesen Plan aus.
- **Laufzeitpruefungen vor jedem Eintrag** (`runner.runtime_check`): Pfade im Root, keine neuen Reparse Points, Zielname nach der Namensregel, Zieltyp = Neu-Klassifikation, Rewrite-Hash = Plan.
- **Zustandsmaschine** (`context.py`, `forward.py`, `rollback.py`): PLANNED → BACKED_UP → TARGET_WRITTEN → TARGET_VERIFIED → TARGET_ATTRS_APPLIED → SOURCE_QUARANTINED → SOURCE_RO_CLEARED → SOURCE_REMOVED → COMMITTED → SIDE_STATE_APPLIED; rueckwaerts ROLLED_BACK/SIDE_STATE_REVERTED, dazu SKIPPED, CONFLICT, KEPT. Jeder Schritt ist idempotent und prueft den tatsaechlichen Plattenzustand (frischer Lauf und Fortsetzen nutzen denselben Code). Umbenennen nur ueber `fs_ops.rename_no_replace` (Windows `os.rename`, POSIX `link`+`unlink`; der Zwei-Namen-Zwischenzustand wird ueber gleiche Inode erkannt). Nie `os.replace`/`atomic_write_text`. Entscheidungen haengen an Hash **und** Identitaet; ohne verfuegbare Identitaet → `CONFLICT`. Vor der Quarantaene und unmittelbar vor dem Loeschen der Quelle wird das Ziel erneut geprueft (Existenz, Identitaet, Rewrite-Hash). Read-only der Quarantaenedatei wird mit journaliertem Originalwert entfernt; ein Rollback setzt genau diesen Wert.
- **Journal** (`journal.py`): JSON-Zeilen mit `seq` und `crc32`, Append + `flush` + `os.fsync`; verbindlich nach `fsync`. Abgerissene letzte Zeile = nie geschrieben, Schaden davor = `JournalCorrupt`. Kein Verzeichnis-fsync unter Windows (akzeptiert, die Recovery prueft den Plattenzustand).
- **Begleitzustand** (`side_state.py`, Adapter `app/storage/migration_side_state_store.py` ueber den Port `SideStateStore`): delta-basiert pro Item (`alt → neu`), nie Snapshots; Undo invertiert nur fuer tatsaechlich zurueckgerollte Items; Vergleich ueber `canonical_path_key` (absolut, `/`, Windows ohne Gross/Klein).
- **Gegenseitiger Ausschluss** (`app/bootstrap/process_locks.py`): OS-Byte-Locks; App haelt `app-<pid>.lock` und prueft dann `migration.lock`, die Migration haelt `migration.lock` und prueft dann alle `app-*.lock`. Lock-Ordner `app/storage/.state/locks` (gemeinsam fuer App und CLI). Der Single-Instance-Port ist kein Lock.
- **Metadaten:** garantiert Inhalt, BOM und Zeilenenden; explizit uebertragen (Fehlschlag = Warnung) Read-only, `atime` (aus dem Plan), `mtime`, Hidden/Archive/System, Creation Time (best effort). Nicht abgedeckt: ACLs/Besitzer, Alternate Data Streams, Extended Attributes, Komprimierung/Verschluesselung, Hardlink-Identitaet/File-ID.
- **Threat-Model-Grenze:** gleiche Inode gilt als eigener Zustand; ein absichtlich stoerender lokaler Prozess (eigener Hardlink) ist nicht abgedeckt. Ein Prozess, der die Quelle schon offen haelt, kann nach der Quarantaene noch schreiben; das erkennt der Hash nach der Quarantaene -- die Quarantaene macht den Vorgang nicht vollstaendig race-frei.
- **Idempotenz:** `resume` auf abgeschlossenem Lauf = No-op; erneutes `--write` mit verbrauchtem Plan wird abgelehnt; ein neuer Dry-Run sieht migrierte Dateien nicht mehr (nach Undo wieder).
- **CLI** `tools/migrate_file_extensions.py`: Dry-Run (Standard) → `plan.json` in `%APPDATA%\Blattwerk\migrations\<run>`, `--write --run`, `--resume`, `--undo`, `--non-interactive`; Ausgabe nur Pfade, Zieltypen, Status und Signalnamen.

## Schichtenmodell

| Schicht | Verantwortung | Nicht erlaubt | Primärmodule |
|---|---|---|---|
| `app/core` | Fachregeln, Parse/Validate/Render/Build | UI-Dialoge, Persistenzdetails | `blatt_kern_io_build.py`, `blatt_validator.py`, `blatt_kern_layout_render.py` |
| `app/bootstrap` | Composition Root, Startup-Koordination (Single-Instance-Uebergabe, ohne Tk) | Fachregeln, Tk-Widgets | `wiring.py`, `single_instance.py` |
| `app/ui` | Input, View-State, Anzeige | Fachregel-Ownership, Persistenzpolicy | `blatt_ui_*.py` |
| `app/storage` | Laden/Speichern, Persistenzformat, Pfad-/Systemadapter | Render-/Validierungslogik | `local_config_store.py`, `history_paths_adapter.py`, `system_settings_adapter.py`, `acknowledged_warnings_store.py` |
| `app/styles` | Profilauflösung, Designnormalisierung, CSS | Dokumentdiagnostik, Persistenzentscheidungen | `blatt_styles.py`, `worksheet_design.py`, `page_geometry.py` (Randspalten-Breiten und -CSS), `ui_profile_adapter.py` |
| `app/cli` | Adapter auf Kern-API | Regelduplikation | `blatt_diagnostics_cli.py` |

UI-Zuschnitt im Hauptfenster:
- KeyBindings werden zentral ueber `bw_libs/ui_contract/keybinding.py` modelliert und modebasiert nachvollziehbar gehalten.
- Pop-up-Verhalten wird zentral ueber `bw_libs/ui_contract/popup.py` mit einheitlicher Lifecycle-/Fokus-Policy gefuehrt.
- Tk-Modifier-Semantik (`event.state`) wird nie app-lokal gedeutet, sondern ausschliesslich ueber den bw-gui-Keybinding-Contract (`bw_gui.contracts.modifiers_from_event`; Windows: `0x0008` = NumLock). Das erzwingt der AST-Guard `tests/test_no_raw_tk_state_bitmasks.py`.
- HSM-Vertragslogik fuer Intent-Katalog, Escape-Prioritaet und Transition-Validierung liegt zentral in `bw_libs/ui_contract/hsm.py`; Shortcut-Semantik nutzt den zentralen Intent-Katalog aus `app/ui/ui_intents.py`.
- Die Hauptansicht verwendet ein horizontales Paned-Layout mit zwei Bereichen: links Schreibbereich, rechts Vorschau.
- Der Schreibbereich ist nur interaktiv (editierbar/fokussierbar), wenn ein Dokument tatsaechlich geladen ist -- Single Source of Truth dafuer ist `_editor_document_state` (`app/ui/blatt_ui_editor.py`, Werte `EDITOR_DOCUMENT_NOT_LOADED`/`_LOADING`/`_LOADED` aus `ui_constants.py`), nicht die aktive Dokument-Tab-Auswahl oder `input_var`. Ansichtswechsel (Nur Schreibbereich/Beides) fokussieren das Widget nur bei `EDITOR_DOCUMENT_LOADED`, sonst faellt der Fokus auf das Hauptfenster zurueck. Ein Klick in den deaktivierten Schreibbereich fokussiert ihn ebenfalls nicht (`_on_editor_mouse_click` bricht Tks Klassen-Binding per `"break"` ab), und `_set_editor_document_state()` entzieht einem bereits fokussierten Editor beim Uebergang nach `NOT_LOADED` aktiv den Fokus (nicht beim rein internen, synchronen `LOADING`-Zwischenschritt) -- damit blockieren globale Kurzbefehle (z. B. Datei oeffnen) nie faelschlich durch die Text-Input-Fokus-Sperre. Der Primaer-Ladevorgang (`_load_editor_content`) committet neuen Editorinhalt sowie die zugehoerigen Baselines (Quell-Snapshot, Block-Type-Counts) nur gemeinsam nach vollstaendigem Erfolg; jeder Fehlschlag (Lesefehler eines anderen Dokuments, fehlgeschlagene Baseline-Ermittlung, Exception beim Befuellen) setzt ueber `_reset_editor_widget_to_empty()` konsistent auf leer/`NOT_LOADED` zurueck, nie eine Mischung aus neuem Dokument und alten Baselines.
- Oberhalb des Paned-Layouts fuehrt die UI eine dokumentorientierte Tab-Leiste; jedes geoeffnete Markdown wird als eigener Tab verwaltet. Die Leiste (`app/ui/blatt_ui_tab_strip.py`) sitzt in einem horizontalen `bw_gui.widgets.ScrollableFrame`: bei vielen Tabs scrollt sie (Scrollleiste, Mausrad) statt Tab-Koepfe zu quetschen, und der aktive Tab wird automatisch in den sichtbaren Bereich gescrollt. Der Schliessen-Button steht ausserhalb des scrollbaren Bereichs (vor der Leiste gepackt) und bleibt immer sichtbar.
- Bereichsauswahl (Vorschau/Beides/Schreibbereich) und Tab-Leiste teilen eine gemeinsame Control-Strip-Zeile in `app/ui`; visuelle Segment-/Tab-Stile sind themeseitig zentral in `app/ui/ui_theme.py` definiert.
- Der tab-lokale View-State (u. a. Aufgabe/Loesung, DIN A4/A5, Kontrast/Farbprofil/Schrift, Layout/Fit) liegt in `app/ui` und wird beim Tab-Wechsel explizit geladen/gesichert.
- Der tab-lokale View-State umfasst zusaetzlich Praesentationsoptionen (z. B. Black-Screen-Modus und Folienformat-Presets).
- Der tab-lokale View-State umfasst ebenfalls Zoom, aktive Seite und Canvas-Scrollposition (x/y), damit der Ansichtskontext pro Dokument erhalten bleibt.
- Alle Oeffnungspfade (Dateidialog, Recent-Menue, Shortcut `Z`) laufen ueber einen zentralen Open-Dispatcher in `app/ui`; bei bereits offenen Dateien fokussiert die UI den vorhandenen Tab statt eine zweite Instanz zu erstellen.
- Tab-Schließen erfolgt ueber den festen `×`-Button rechts der Tab-Leiste (schliesst den aktiven Tab) und bleibt in `app/ui` als reine View-State-Operation ohne Kernlogik.
- Das Hauptfenster (`bw_gui.BwBaseWindow`) startet maximiert (`AppShellConfig.start_maximized`, Quelle `app/bootstrap/wiring.py`). Eine gemerkte Fenstergeometrie (`remember_window_geometry`) hat Vorrang: `_restore_window_geometry_if_enabled` verlaesst dafuer den maximierten Zustand (`state("normal")` vor `geometry(...)`).
- Dateien von aussen (Kommandozeile, Windows "Oeffnen mit") laufen in derselben Instanz zusammen: `blattwerk.py` belegt als Erstes den Port (`app/bootstrap/single_instance.py`, Loopback-TCP, nur stdlib, ohne Tk); wer ihn nicht bekommt, uebergibt den Pfad an die laufende Instanz und beendet sich bei Bestaetigung ohne GUI-Import, wer ihn bekommt, importiert die GUI und startet. Der Server-Thread beruehrt kein Tk, sondern queued `OpenRequest`s; `app/ui/blatt_ui_external_open.py` pollt sie im Tk-Thread und oeffnet ueber den zentralen Open-Dispatcher (`_open_input_path`). Der Server bestaetigt einem wartenden Start nur die Lebendigkeit der Oberflaeche (Heartbeat bei jedem Poll), nicht das fertige Oeffnen (Rendering kann Sekunden dauern, mehrere parallele Starts warten nicht aufeinander); ohne lebendige Oberflaeche innerhalb des Timeouts bleibt die Bestaetigung aus und der wartende Start oeffnet ein eigenes Fenster. Die Startdatei oeffnet erst der erste Poll in der laufenden Ereignisschleife, vor allen wartenden Anfragen; sie hat Vorrang vor `start_with_last_file`.
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

- `app/bootstrap/*`
   - darf: Komposition der Startabhaengigkeiten, Startup-Koordination ohne Tk (Single-Instance-Uebergabe)
   - darf nicht: Fachregeln, Widgets, Persistenzschema

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
