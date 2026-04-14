# Changelog

All notable user-facing changes to this project will be documented in this file.

The format is based on Keep a Changelog.

## [Unreleased]

### Changed

## [0.2.0] - 2026-04-14

### Changed
- Answer blocks now use dedicated block types instead of `:::answer type=...`.
	Supported forms are `:::lines`, `:::grid`, `:::dots`, `:::space`, `:::table`, `:::numberline`, `:::mc`, `:::cloze`, `:::matching`, and `:::wordsearch`.
- Legacy syntax `:::answer type=...` is now rejected with explicit diagnostics.
- Option validation for answer blocks is now type-specific; `type=` inside dedicated answer blocks is invalid.
- Example markdown files were migrated to the new dedicated answer block syntax.
- Blattwerk-internales Markdown fuer Aufgaben/Material/Info/Loesungen und freien Text nutzt jetzt konsistente Umbruch-Semantik: einfacher Zeilenumbruch wirkt wie Shift+Enter (sichtbarer Zeilenumbruch), doppelter Zeilenumbruch wie Enter (Absatzwechsel); 3+ aufeinanderfolgende Leerzeilen werden auf einen Absatzwechsel begrenzt.
- Table answer blocks (`table`) now support `header_columns` (alias `header_cols`) to render leading body columns as row headers.
- Table answer blocks (`table`) now support `alignment=left|center|right|justify` to control cell text alignment, including per-column shorthand like `alignment="l r c c"`.
- `columns` blocks now support an optional `gap` option for explicit horizontal column spacing (for example `gap=1cm`), in addition to `cols` and `widths/ratio`.
- Section-break behavior was extended: `--` now acts as a soft split marker, and `---` now inserts an additional vertical `1cm` gap between sections while still serving as the regular split marker.
- Lernhilfen now render and export card-native without worksheet-style running elements: no auto-inserted header/footer texts and no page numbering in lernhilfen PDF output.
- Lernhilfen PDF output now uses a flowing card layout in one document (cards continue naturally on the next page when needed) instead of forcing one card per page.
- Lernhilfen preview and lernhilfen PNG/PNG-ZIP export now use robust card-content cropping to remove empty page remainder and show/save only the visible card region.
- Export workflows are now split by intent: worksheets and lernhilfen use separate export dialogs.
- Export interaction is now standardized on `Ctrl+E` for export actions; `Enter` no longer triggers export confirmation in export dialogs.
- The lernhilfen preview window now has its own `Exportieren` button and supports `Ctrl+E` directly in that window.
- Lernhilfen are now shown as one vertically stacked, scrollable stream in the preview window; arrow keys jump directly to the previous/next lernhilfe.
- The preview control row now includes a `Lernhilfen` button next to `Aktualisieren`; it stays visible and is automatically disabled when the active document has no lernhilfen.
- `Ctrl+H` now opens the lernhilfen preview when lernhilfen exist in the active document (otherwise no action).
- User-facing UI terminology now consistently uses `Lernhilfen` while markdown block syntax (`help` / `hilfe`) remains unchanged.
- `Help cards only` export mode now supports `PDF`, `PNG`, and `PNG (ZIP)` from one unified export flow.
- Help-card exports now use dedicated mode-aware pipelines: PDF and ZIP exports no longer fall through worksheet export branches.
- The `View` menu now includes `Hilfekartenansicht`, opening the separate help-cards preview window directly.
- Hovering over preview areas no longer steals keyboard focus from the write area; focus now changes on click (or window switch), matching toolbar-style interaction expectations.
- The Blattwerker agent now enforces math notation defaults in generated worksheets: multiplication uses `·` and division uses `:`.
- The Blattwerker agent now requires Blattwerk-native table syntax and avoids standard Markdown tables when generating worksheet content.
- Validator checks for `:::` markers are now stricter: whitespace directly after `:::` is rejected, and orphan closing markers (`:::` without an open block) are now reported as errors.
- The top menu now uses fully themed custom popup menus (instead of native Tk menus), including dark popup surfaces, dark borders, and nested side submenus.
- Menu popups now close consistently on outside click and when the window deactivates (including Alt+Tab).
- Alt mnemonics were restored for top-level menus (`Alt+D`, `Alt+A`, `Alt+S`) with underlined menu labels.
- Tab close was moved out of the tab title: documents now use a dedicated small close button at the right side of the same control row.
- `Ctrl+O` / open dialog now supports selecting multiple markdown files at once and opens up to 8 sheets in one operation.
- Boolean settings in the settings dialog now use modern toggle switches (Ein/Aus) with theme-consistent dark styling.
- Editor dark-theme visuals were refined: diagnostics and outline lists are now dark-compatible, syntax colors are tuned for dark readability (VS Code-like palette), and dark-theme primary text is slightly less bright.
- Dark-theme frame/border tones were further softened centrally (including editor diagnostics/outline containers and common input/frame outlines) to reduce harsh bright edges.
- Editor syntax highlighting colors were strengthened in both light and dark themes for clearer visual distinction while editing.
- Beim Fokus auf den Schreibbereich (und beim Tab-Wechsel) gleicht Blattwerk den Editor jetzt zuerst mit der Quelldatei ab: externe Dateiaenderungen werden automatisch uebernommen, und bei Konflikten mit lokalen ungespeicherten Aenderungen erscheint ein Dialog mit den Optionen `Verwerfen` oder `Ueberschreiben` inklusive Altersanzeige der externen Aenderung.
- Bereichsauswahl und Dokument-Tabs teilen jetzt eine gemeinsame obere Steuerzeile fuer ein kompakteres, moderneres Layout.
- Bereichsumschaltung (Vorschau/Beides/Schreibbereich) wurde visuell als segmentierte Auswahl modernisiert.
- Default theme is now `slate_indigo`, reducing the previous brown-heavy look in the default UI.
- Blattwerk now supports multiple open markdown documents via tabs in the main window, with per-document preview settings (for example task/solution mode, DIN format, contrast, and design profile) restored on tab switch.
- Tab switches now also restore per-document view position (zoom level, active page, horizontal/vertical scroll position).
- Preview switching between tabs now reuses cached preview pages when the source file and render options are unchanged, avoiding unnecessary recompilation.
- Opening a markdown file that is already open no longer creates a duplicate tab: Blattwerk now shows an "ist schon offen" warning and focuses the existing tab.
- `Z` now opens the newest recent markdown that is not already open, skipping already-open entries instead of repeatedly reopening only the latest one.
- The preview heading texts "Blattwerk Vorschau" and "Markdown laden, Vorschau prüfen, danach gezielt exportieren." were removed, and the window title is now "Blattwerk".
- Cloze answer blocks now support `words_multi` (default `true`) to control whether duplicate solution words appear multiple times in the word bank or only once.
- Completion preference names are now consistently `completion_*`; legacy snippet-oriented preference keys were removed.
- Option value catalogs for completion are now discovered automatically from core `KNOWN_*` constants.
- Write-area snippet templates are now disabled to avoid intrusive block-template insertions during normal completion flow.
- `Ctrl+Shift+.` now inserts `::: :::` and opens regular completion instead of forcing snippet-template suggestions.
- Completion candidates are now sourced dynamically from a core catalog API, reducing stale suggestions after core option/type catalog updates.
- Text option completion (for example `type` in `info`) now uses the full available core value catalogs.
- Completion popups no longer close immediately when releasing modifier keys like `Shift` during typing.
- Option value suggestions after `key=` now open automatically (not only via manual `Ctrl+Space`).
- Option value suggestions now use the same local decay-based personalization mechanism as block-type suggestions.
- Auto snippet fallback is now reduced in block-header/option flows (including removal of noisy `Answer-Lines` auto suggestions there).
- Auto completion is now suppressed on pure closing-marker lines (`:::`) when already inside an open block, reducing unwanted popups while closing blocks.
- Completion now opens immediately after typing `:::` (without needing a space) and suggests all available block types.
- Block-type suggestion order is now locally personalized per installation using usage frequency with time decay.
- Ties in block-type ranking now fall back to Blattwerk's fixed core block-type order.
- Local completion ranking can now be reset from the settings dialog.
- Auto snippet triggering now also reacts to `:` / `=` / `Enter`, improving automatic suggestions in block-header and option-value flows.
- Auto snippet suggestions in `:::` lines now only appear for opening block headers, not for closing `:::` markers.
- The write-area panel label is now back to `Struktur` (instead of folding-equivalent wording).
- New write-area shortcut `Ctrl+Shift+.` inserts `::: :::`, places the cursor between both markers, and opens snippet suggestions immediately.
- Unclosed blocks are now reported as diagnostics error `SY002`.
- Matching `:::` pair highlighting now also updates when moving the cursor with arrow keys.
- Diagnostic and outline list clicks now reliably trigger line jumps even when re-clicking an already selected item.
- Snippet suggestions now open automatically in matching contexts (in addition to manual trigger).
- Snippet suggestion popup is wider, so entries are easier to read.
- When already inside a matching block, snippet insertion now adds only the inner content instead of duplicating block wrappers.
- Editor outline now reflects nested block depth as a folding-equivalent navigation aid.
- Closing `:::` markers are now syntax-highlighted like opening markers.
- Text after a closing `:::` is now flagged as a syntax error (`SY001`) and shown in diagnostics.
- When the cursor is inside a `:::` block, the corresponding opening/closing marker pair is now highlighted.
- Active snippet-field highlighting now follows the selected UI theme.
- The currently active snippet field is now visually highlighted while a snippet session is running.
- Snippet sessions now auto-finish when the cursor leaves the active field flow.
- Snippets now support real multi-field tab stops: `Tab` jumps to the next snippet field and `Shift+Tab` jumps back.
- Snippet suggestions are now block-type-aware and only appear in matching contexts (for example, answer snippets in `answer` context).
- Snippet completion now places the cursor on the first editing spot after insertion instead of always moving to the end.
- Snippet suggestions are now context-aware (for example, frontmatter snippet only appears near document start when no frontmatter exists yet).
- Completion in the write area now supports direct keyboard control from the editor (`Up`, `Down`, `Enter`, `Tab`) and can insert snippets as fallback suggestions.
- The write area now includes a structure outline (frontmatter and block headers) as a folding-equivalent navigation aid with direct line jumps.
- The write area now highlights Blattwerk syntax (frontmatter, block headers, option keys/values, and marker symbols) directly while editing.
- The write area now offers context-aware keyword completion (block types, option keys, answer types, and frontmatter fields), available via `Ctrl+Space`.
- The write area now shows live diagnostics while typing: warnings and errors are highlighted by line and listed below the editor.
- Standardfunktionen sind jetzt konsistent per Tastatur erreichbar: neue Shortcuts für Einstellungen, Bereichsansicht, Theme- und Schriftprofilwechsel wurden ergänzt.
- Shortcut-Set für Dateiaktionen erweitert: Markdown öffnen ist nun zusätzlich mit `Ctrl+O` verfügbar.
- Architecture documentation now cleanly separates stable architecture reference from internal development history.
- Main window now supports three area modes: preview only, split view, or editor only.
- Split view opens editor and preview side-by-side with draggable divider and equal default width.
- Markdown editing in the new write area saves debounced live to the selected file.
- Save state in the editor is now clearly visible as Unsaved, Saving, and Saved.
- In split view, preview controls (format, design, navigation, export) now live inside the right preview pane; only the markdown file row remains above both panes.
- Area mode controls (preview/both/editor) are now shown as a dedicated global row directly under the markdown file path.
- Preview control rows now wrap responsively with indentation across as many lines as needed when horizontal space is tight (including DIN format, color profile, and font/size controls).
- Preview action controls (navigation, zoom, refresh) now also use responsive multi-line wrapping when space is tight.
- Beenden and Exportieren are now placed in the global markdown-path row.

### Added
- Public-facing changelog workflow and PR checklist for clearer release communication.
- Ctrl+N now opens a system dialog to create a new markdown file with default starter content.
