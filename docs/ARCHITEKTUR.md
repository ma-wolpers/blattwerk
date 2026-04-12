# Architekturübersicht Blattwerk

Diese Struktur ist auf Erweiterbarkeit ausgelegt (neue Blöcke, neue View-Modi, andere Designs):

```text
blattwerk/
├─ blattwerk.py              # App-Start (einziger Python-Einstieg im Hauptordner)
├─ docs/                     # Projektdokumentation (gebündelt)
├─ examples/                 # Beispiele, Assets und Beispiel-Outputs
├─ vscode-extension/         # VS Code Extension (Language Tools)
├─ app/                      # Interne Implementierungsmodule
│  ├─ ui/                    # GUI-Controller + Vorschau/Navigation
│  ├─ core/                  # Markdown→HTML/PDF Kernpipeline
│  ├─ cli/                   # Python-CLI-Bridge (z. B. Diagnostik-JSON)
│  ├─ styles/                # Druckprofile + Stylesheet-Building
│  ├─ storage/               # Verlaufspersistenz
│  └─ __init__.py
├─ assets/
│  └─ worksheet.css          # Externe CSS-Vorlage (direkt editierbar)
└─ ...
```

## Verantwortlichkeiten

- `app/ui/blatt_ui.py`
  - Reine UI-Interaktion (Dateiauswahl, Vorschau, Zoom, Layoutmodus, Export)
  - Orchestriert Export über `app/ui/export_dialog.py`
  - Nutzt zentrale Werte aus `app/ui/ui_constants.py`
  - Delegiert Geometrie an `app/ui/preview_geometry.py`
  - Delegiert Verlaufsspeicherung an `app/storage/recent_files_store.py`

- `app/core/blatt_kern.py`
  - Parsing/Rendering-Pipeline
  - HTML/PDF-Erzeugung
  - PDF-Laufelemente (Seitenzahl/Lauftitel)
  - propagiert Frontmatter-Dokumentmodus (`mode`) bis in den Task-Renderer

- `app/core/blatt_validator.py`
  - dedizierte Dokumentvalidierung fuer Frontmatter, Blocktypen und Optionen
  - liefert stabile/oeffentliche Diagnosecodes fuer UI, CLI und spaetere Editor-Integration
  - markiert kritische Fehler (severity `error`) fuer teilweise blockierenden Build
  - validiert Dokumentmodus im Frontmatter (`mode: ws|test`)

- `app/cli/blatt_diagnostics_cli.py`
  - JSON-Bridge auf den Validator fuer externe Tools (z. B. VS Code Diagnostics)
  - liefert range-basierte Meldungen fuer Editor-Markierungen

- `vscode-extension/blattwerk-language`
  - VS Code Integration fuer Blattwerk-Markdown (Highlighting, Folding, Snippets, Diagnostics)
  - bezieht Diagnosen bewusst aus Python statt Regelduplikation in TypeScript

- `app/core/color_mentions.py`
  - zentrale Erkennung von Farbbegriffen in Markdown-Texten
  - bewusst UI-unabhängig, damit Prüfregeln nicht in Widgets dupliziert werden
  - nutzbar für GUI-Warnungen und spätere Prüf-/Linting-Pfade

- `app/core/answer_grid_plot.py`
  - Renderer für visuelle Antwortfelder mit SVG-Overlay-Logik
  - aktuell: `grid` (inkl. Achsen/Ticks/Labels/Punkte/Funktionen), `dots`
  - unterstützt markerbasierte Sichtbarkeit auf Elementebene (`show: "§"|"%"|"&"`)

- `app/core/answer_numberline.py`
  - dedizierter Renderer für horizontale Zahlengeraden/Zahlenstrahle
  - Tick-/Skalenlogik, Label-Rendering und Antwortkästchen
  - markerbasierte Sichtbarkeit auf Elementebene (`show: "§"|"%"|"&"`)

- `app/styles/blatt_styles.py`
  - Druckprofilauflösung (`standard`/`strong`)
  - Mapping Profil/Schrift/Schriftgröße → CSS-Variablen
  - Laden von `assets/worksheet.css` als Basis-CSS
  - Ergänzen dynamischer Laufzeit-Overrides (`@page`, `:root`)
  - Metadatenbasierte Seitenrand-Overrides (z. B. Lochrand über YAML `lochen: ja/nein`)
  - Übergabe des Kontrastprofils an die Design-CSS-Erzeugung
  - Farbkonvertierung für PDF-Laufelemente

- `app/styles/worksheet_design.py`
  - Farbschema-/Design-Overrides je Farbprofil
  - zentrale Symbolstil-Entscheidung über `_resolve_symbol_style(...)`
  - Symbolwerte über dataclass-basierte Presets (`Filter`, `Stroke`, `Shadow`) gebündelt
  - robuste Regel: genau ein Symbolfilter-Pfad (kein doppelter `task-work-symbol`-Override in S/W)

- `assets/worksheet.css`
  - Alle visuellen Regeln zentral als Datei
  - Standardkonformes CSS mit Defaults (direkt editierbar/lintbar)
  - Keine Python-String-CSS-Blöcke mehr im Kern

## UI-Architektur (integriert)

```text
app/
├─ ui/
│  ├─ blatt_ui.py         # Haupt-UI-Controller (BlattwerkApp)
│  ├─ export_dialog.py    # ExportDialog (modal)
│  ├─ ui_constants.py     # Zoom/Layout-Konstanten + Modus-Schlüssel
│  └─ preview_geometry.py # Geometrie-/Zoom-Berechnungen (ohne Tk-Abhängigkeit)
└─ storage/
   └─ recent_files_store.py  # Laden/Speichern der Verlaufsliste
```

- `app/ui/blatt_ui.py`
  - Eventfluss, Vorschauzustand, Navigation, Exportablauf
  - nutzt `app/ui/export_dialog.py` und `app/ui/ui_constants.py`
  - verwaltet Designauswahl (Farbprofil, Schriftprofil, Schriftgrößenprofil)
  - triggert S/W-Farbwarnungen, delegiert Textanalyse an `app/core/color_mentions.py`

- `app/ui/export_dialog.py`
  - ausschließlich Exportoptionen und Ergebnisobjekt
  - kann später separat erweitert werden (weitere Formate/Optionen)

- `app/ui/ui_constants.py`
  - zentrale Anpassung von Grenzen und Modi
  - vermeidet Magic Numbers und String-Duplikate

- `app/ui/preview_geometry.py`
  - reine Mathe-/Geometrie-Helfer (Zoomgröße, Zentrierung, aktive Seite)
  - reduziert UI-Kopplung in `app/ui/blatt_ui.py`

- `app/storage/recent_files_store.py`
  - JSON-Persistenz der zuletzt geöffneten Dateien
  - testbar und unabhängig von Tk-Widgets

## Erweiterungspunkte

1. Neues Druckprofil:
  - in `PRINT_PROFILE_PRESETS` (`app/styles/blatt_styles.py`) ergänzen
2. Neues Seitenformat:
  - in `PAGE_LAYOUTS` (`app/styles/blatt_styles.py`) ergänzen
3. Neues visuelles Design:
   - direkt in `assets/worksheet.css` anpassen
4. Neue Vorschau-Layoutidee:
  - in `app/ui/blatt_ui.py` als eigener Renderpfad (wie `single`/`strip`/`stack`)
5. Neue Exportoption:
  - Dialogelement in `app/ui/export_dialog.py`
  - Übergabe im Exportpfad in `app/ui/blatt_ui.py`
6. Geometrieverhalten ändern (aktive Seite/Zentrierung):
  - in `app/ui/preview_geometry.py`
7. Verlaufsspeicherung austauschen (z. B. sqlite):
  - in `app/storage/recent_files_store.py`

## Stabilitätsprinzipien

- Verantwortlichkeiten pro Datei getrennt
- CSS aus Python ausgelagert
- Fallbacks bei unbekannten Profilen/Formaten
- Keine harte Kopplung von UI-Details mit Rendering-Details
- Dokumentweite Darstellungsmodi werden zentral im Renderfluss weitergereicht (Frontmatter -> Layout-Renderer -> Block-Renderer), statt lokal dupliziert
