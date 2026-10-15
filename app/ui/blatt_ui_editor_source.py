"""Schreibbereich: Dokumentzustand, Laden, Abgleich mit der Datei, automatisches Speichern und Vorschau-Aktualisierung (BlattwerkApp-Mixin).

Aus ``blatt_ui_editor.py`` ausgelagert (300-Zeilen-Regel), Methoden unverändert."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
import shutil

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui, widgets

from .dialog_services import messagebox
from .ui_constants import EDITOR_DOCUMENT_LOADED, EDITOR_DOCUMENT_LOADING, EDITOR_DOCUMENT_NOT_LOADED


class BlattwerkAppEditorSourceMixin:
    """Schreibbereich: Dokumentzustand, Laden, Abgleich mit der Datei, automatisches Speichern und Vorschau-Aktualisierung (BlattwerkApp-Mixin)."""

    def _set_editor_document_state(self, state: str):
        """Updates the editor's load state and applies the resulting UI treatment.

        `state` is one of EDITOR_DOCUMENT_NOT_LOADED, _LOADING or _LOADED
        (ui_constants.py). Only EDITOR_DOCUMENT_LOADED is interactive: the
        Text widget is editable and can receive focus. NOT_LOADED and LOADING
        both render as disabled/inactive -- LOADING is a transient, purely
        synchronous state (the file read and content insert happen within a
        single call, so it is never actually rendered on screen) that exists
        so a failed read can never be mistaken for a successful load, and so
        a future asynchronous loader could hook into it without further
        modeling. This is the single source of truth for whether the editor
        is currently usable; callers must not infer that from `input_var`,
        the active document tab, or the editor's text content, none of which
        are guaranteed to match (e.g. a tab can be selected before its file
        has been confirmed loadable).

        On a transition to NOT_LOADED specifically, any focus the editor
        currently holds is actively taken away (state="disabled" and
        takefocus=0 alone do not do this for an already-focused widget).
        LOADING deliberately does NOT do this -- it is a transient, never
        actually rendered step (see above), so evicting focus on entry and
        having to artificially restore it on a subsequent LOADED would be
        pure overhead; an existing focus is simply left untouched while
        LOADING is in effect.
        """

        self._editor_document_state = state
        interactive = state == EDITOR_DOCUMENT_LOADED
        self.editor_widget.configure(
            state="normal" if interactive else "disabled",
            takefocus=1 if interactive else 0,
        )
        if state == EDITOR_DOCUMENT_NOT_LOADED and self.root.focus_get() is self.editor_widget:
            self.root.focus_set()
        self._apply_editor_widget_theme_colors()

    @contextmanager
    def _editor_widget_unlocked_for_mutation(self):
        """Temporarily makes the Text widget programmatically writable.

        Tk's Text widget silently no-ops insert()/delete() while
        state="disabled" (verified empirically) -- any code that
        programmatically rewrites the editor's content must run inside this
        block. This is a self-contained, exception-safe technical primitive:
        it saves the widget's current -state and the current
        _editor_loading_content flag, forces state="normal" and
        _editor_loading_content=True for the block's duration, and restores
        both previous values in `finally` regardless of success or exception
        -- callers never need to reason about what it changed. It says
        nothing about the editor's *document* state;
        _set_editor_document_state() remains the sole place that decides the
        regular resting state once the caller has determined the outcome
        (loaded / not loaded).
        """

        previous_widget_state = str(self.editor_widget.cget("state"))
        previous_loading_content = self._editor_loading_content
        self.editor_widget.configure(state="normal")
        self._editor_loading_content = True
        try:
            yield
        finally:
            self._editor_loading_content = previous_loading_content
            self.editor_widget.configure(state=previous_widget_state)

    @staticmethod
    def _get_editor_source_snapshot(input_path: Path) -> tuple[Path, int]:
        """Computes (path, mtime_ns) for a document's on-disk source snapshot.

        Pure computation, no object mutation -- raises if the file cannot be
        stat()ed (e.g. deleted between a successful read and this call).
        Shared by _load_editor_content()'s Phase A (where a failure here
        means the whole load failed, see below) and
        _update_editor_source_snapshot() (used after saving, where a failure
        is tolerated and simply skipped), so load and save never diverge on
        how a snapshot is computed.
        """

        return input_path, int(input_path.stat().st_mtime_ns)

    def _reset_editor_widget_to_empty(self):
        """Clears the editor and marks no document as loaded.

        Core recovery (content, all load baselines, document state) always
        runs first and is simple/low-risk -- it never needs to roll back a
        *partial* new baseline, because _load_editor_content()'s Phase A
        only ever commits baselines after complete success; on any failure
        there, nothing new was written yet, so this just resets everything
        to the neutral "no document" baseline. The trailing
        diagnostics/outline/highlighting refresh is derived UI sync -- if it
        fails, the exception propagates, but core recovery has already
        committed by that point, so the editor's resting state stays correct
        regardless.
        """

        with self._editor_widget_unlocked_for_mutation():
            self.editor_widget.delete("1.0", "end")
            self.editor_widget.edit_modified(False)
        self._editor_last_loaded_path = None
        self._editor_last_known_source_path = None
        self._editor_last_known_source_mtime_ns = None
        self._editor_last_saved_block_type_counts = {}
        self._set_editor_document_state(EDITOR_DOCUMENT_NOT_LOADED)

        self._queue_editor_highlighting(immediate=True)
        self._queue_editor_diagnostics(immediate=True)
        self._queue_editor_outline(immediate=True)

    def _load_editor_content(self, input_path: Path):
        """Loads the selected markdown file into the editor widget.

        Phase A (this method's main try block) is the primary load
        transaction: read the file, prepare the source-snapshot and
        block-type-counts baselines as local values (without touching the
        persistent fields yet), replace the widget content, and only then
        commit everything together in one uninterrupted block of plain
        attribute assignments. A failure anywhere in Phase A -- including a
        failing source-snapshot lookup -- therefore never leaves a partially
        updated document identity; recovery just resets to the neutral
        "nothing loaded" baseline. `same_document` only decides what happens
        when `read_text()` itself fails (before Phase A is even entered);
        once reading succeeds, every call goes through the same Phase A,
        including a same-document re-sync.

        Phase B (after EDITOR_DOCUMENT_LOADED) recomputes purely derived
        display state (highlighting/diagnostics/outline) from the
        already-successfully-loaded content; a failure there must not undo
        the primary content that Phase A already committed.
        """

        if self.editor_widget is None:
            return

        same_document = input_path == self._editor_last_loaded_path
        self._set_editor_document_state(EDITOR_DOCUMENT_LOADING)

        try:
            content = input_path.read_text(encoding="utf-8")
        except Exception as error:
            if same_document:
                # Re-Sync/Reload desselben, bereits angezeigten Dokuments
                # fehlgeschlagen -- Widget wurde nie angefasst, Inhalt bleibt
                # unangetastet und gueltig.
                self._set_editor_document_state(EDITOR_DOCUMENT_LOADED)
            else:
                self._reset_editor_widget_to_empty()
            status = (
                "Datei im Tab existiert nicht mehr"
                if isinstance(error, FileNotFoundError)
                else "Datei konnte nicht gelesen werden"
            )
            messagebox.showerror(status, str(error))
            self.status_var.set(status)
            return

        # Phase A: fachliche Baselines zunaechst NUR lokal berechnen -- der
        # persistente Zustand bleibt bis zum gemeinsamen Commit unten
        # unangetastet. Jeder Teilschritt (Snapshot, Block-Type-Counts,
        # Widget-Mutation) muss vollstaendig gelingen; keiner davon wird
        # einzeln toleriert.
        try:
            new_source_path, new_source_mtime_ns = self._get_editor_source_snapshot(input_path)
            new_block_type_counts = self._collect_editor_block_type_counts(content)

            with self._editor_widget_unlocked_for_mutation():
                self.editor_widget.delete("1.0", "end")
                self.editor_widget.insert("1.0", content)
                self.editor_widget.edit_modified(False)

            # Ab hier ist alles Vorbereitete UND die Widget-Mutation
            # erfolgreich abgeschlossen -- gemeinsamer, unterbrechungsfreier
            # Commit. Kein I/O und keine weitere Berechnung mehr zwischen
            # diesen Zeilen und EDITOR_DOCUMENT_LOADED.
            self._editor_has_unsaved_changes = False
            self._editor_last_loaded_path = input_path
            self._editor_last_known_source_path = new_source_path
            self._editor_last_known_source_mtime_ns = new_source_mtime_ns
            self._editor_last_saved_block_type_counts = new_block_type_counts
        except Exception:
            # Nichts von alledem wurde committed (siehe oben) -- Inhalt kann
            # trotzdem unvollstaendig im Widget stehen (falls die Mutation
            # selbst betroffen war) und darf unter keiner Identitaet als
            # "geladen" gelten. Fehler wird NICHT verschluckt, nur der
            # UI-Zustand vorher garantiert konsistent gemacht.
            self._reset_editor_widget_to_empty()
            raise
        else:
            self._set_editor_document_state(EDITOR_DOCUMENT_LOADED)

        # Phase B: rein abgeleitete Darstellung, bewusst ausserhalb des
        # Recovery-Pfads -- ein Fehler hier darf den bereits erfolgreich
        # geladenen Editor nicht zuruecknehmen.
        self._queue_editor_highlighting(immediate=True)
        self._queue_editor_diagnostics(immediate=True)
        self._queue_editor_outline(immediate=True)

    @staticmethod
    def _format_external_change_age(file_mtime_ns: int) -> str:
        """Formats the age of the external file change for conflict prompts."""

        changed_at = datetime.fromtimestamp(file_mtime_ns / 1_000_000_000)
        now = datetime.now()
        delta_seconds = max(0, int((now - changed_at).total_seconds()))
        if delta_seconds < 60:
            relative = f"vor {delta_seconds} s"
        elif delta_seconds < 3600:
            relative = f"vor {delta_seconds // 60} min"
        elif delta_seconds < 86400:
            relative = f"vor {delta_seconds // 3600} h"
        else:
            relative = f"vor {delta_seconds // 86400} Tagen"

        return f"{relative} ({changed_at.strftime('%Y-%m-%d %H:%M:%S')})"

    def _update_editor_source_snapshot(self, input_path: Path):
        """Stores the latest known source timestamp for the active editor file."""

        try:
            path, mtime_ns = self._get_editor_source_snapshot(input_path)
        except Exception:
            return

        self._editor_last_known_source_path = path
        self._editor_last_known_source_mtime_ns = mtime_ns

    def _show_editor_source_conflict_dialog(self, *, input_path: Path, age_text: str) -> str:
        """Shows a modal conflict dialog and returns discard, overwrite, or cancel."""

        dialog = ui.Toplevel(self.root)
        dialog.title("Externe Änderung erkannt")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        try:
            dialog.grab_set()
        except Exception:
            pass

        body = widgets.Frame(dialog, padding=12)
        body.pack(fill="both", expand=True)

        widgets.Label(
            body,
            text=(
                "Die Quelldatei wurde extern geändert.\n"
                f"Datei: {input_path.name}\n"
                f"Geändert: {age_text}\n\n"
                "Lokale ungespeicherte Änderungen sind vorhanden."
            ),
            justify="left",
        ).pack(anchor="w")

        button_row = widgets.Frame(body)
        button_row.pack(fill="x", pady=(12, 0))

        result = {"value": "cancel"}

        def choose(value: str):
            result["value"] = value
            dialog.destroy()

        widgets.Button(button_row, text="Verwerfen", command=lambda: choose("discard")).pack(side="left")
        widgets.Button(button_row, text="Überschreiben", command=lambda: choose("overwrite")).pack(side="left", padx=(8, 0))
        widgets.Button(button_row, text="Abbrechen", command=lambda: choose("cancel")).pack(side="right")

        dialog.protocol("WM_DELETE_WINDOW", lambda: choose("cancel"))
        dialog.wait_window()
        return result["value"]

    def _sync_editor_with_source(self, trigger: str = "focus"):
        """Reconciles editor state with external file changes before editing continues."""

        del trigger  # currently only used for tracing when needed

        if self.editor_widget is None:
            return
        if self._editor_loading_content:
            return
        if self._editor_source_sync_in_progress:
            return

        input_path = self._get_input_path_if_exists()
        if input_path is None:
            return

        try:
            current_mtime_ns = int(input_path.stat().st_mtime_ns)
        except Exception:
            return

        known_path = self._editor_last_known_source_path
        known_mtime_ns = self._editor_last_known_source_mtime_ns

        if known_path != input_path or known_mtime_ns is None:
            self._editor_last_known_source_path = input_path
            self._editor_last_known_source_mtime_ns = current_mtime_ns
            return

        if current_mtime_ns <= known_mtime_ns:
            return

        self._editor_source_sync_in_progress = True
        try:
            if self._editor_has_unsaved_changes:
                age_text = self._format_external_change_age(current_mtime_ns)
                decision = self._show_editor_source_conflict_dialog(input_path=input_path, age_text=age_text)
                if decision == "discard":
                    self._load_editor_content(input_path)
                    self.status_var.set("Externe Änderung übernommen (lokale Änderungen verworfen)")
                elif decision == "overwrite":
                    self._save_editor_content()
                    if self._editor_has_unsaved_changes:
                        self.status_var.set("Überschreiben fehlgeschlagen")
                    else:
                        self.status_var.set("Externe Änderung überschrieben (lokaler Stand gespeichert)")
                else:
                    self.status_var.set("Konflikt mit externer Änderung: keine Aktion")
            else:
                self._load_editor_content(input_path)
                self.status_var.set("Externe Änderung übernommen")
        finally:
            self._editor_source_sync_in_progress = False

    def _cancel_editor_auto_preview_refresh(self):
        """Cancels any pending auto-preview refresh timer."""

        timer_id = getattr(self, "_preview_auto_refresh_after_id", None)
        if timer_id is None:
            return

        try:
            self.root.after_cancel(timer_id)
        except Exception:
            pass
        self._preview_auto_refresh_after_id = None

    def _queue_editor_auto_preview_refresh(self):
        """Schedules a debounced preview refresh after typing pauses."""

        if not bool(getattr(self, "_preview_auto_refresh_on_edit_idle_enabled", False)):
            self._cancel_editor_auto_preview_refresh()
            return

        if self.editor_widget is None:
            return

        self._cancel_editor_auto_preview_refresh()
        delay_ms = int(getattr(self, "_preview_auto_refresh_on_edit_idle_delay_ms", 1200) or 1200)
        self._preview_auto_refresh_after_id = self.root.after(
            delay_ms,
            self._run_editor_auto_preview_refresh,
        )

    def _flush_unsaved_editor_changes(self):
        """Cancels the pending debounced save and writes unsaved changes now.

        Shared by the idle auto-refresh timer and manual compile
        (`_compile_now`) -- both need to guarantee the on-disk file matches
        the editor buffer before triggering a rebuild, since `refresh_preview`
        reads from disk, not from the editor widget. Returns `True` once it
        is safe to proceed (no unsaved changes remain), `False` if saving
        just failed (caller should abort rather than build a stale/broken
        state).
        """
        if self._editor_save_after_id is not None:
            try:
                self.root.after_cancel(self._editor_save_after_id)
            except Exception:
                pass
            self._editor_save_after_id = None

        if self._editor_has_unsaved_changes:
            self._save_editor_content()
            if self._editor_has_unsaved_changes:
                return False

        return True

    def _run_editor_auto_preview_refresh(self):
        """Runs idle auto-refresh and ensures preview uses persisted editor content."""

        self._preview_auto_refresh_after_id = None

        if not bool(getattr(self, "_preview_auto_refresh_on_edit_idle_enabled", False)):
            return

        if self.editor_widget is None:
            return

        if not self._flush_unsaved_editor_changes():
            return

        self.refresh_preview(force_rebuild=True)

    def _compile_now(self, force_rebuild=False):
        """Manual compile (button / spacebar): cancels the pending idle
        auto-refresh timer instead of letting it fire again redundantly
        right after this manual build. Flushes unsaved editor changes to
        disk first (`refresh_preview` reads the file, not the editor
        buffer) and aborts without rebuilding if that save fails.
        `force_rebuild` defaults to `False` here, matching the previous
        direct `refresh_preview` binding, to keep the cache-hit benefit for
        manual compiles.
        """
        self._cancel_editor_auto_preview_refresh()

        if not self._flush_unsaved_editor_changes():
            return

        self.refresh_preview(force_rebuild=force_rebuild)

    def _on_editor_modified(self, _event=None):
        """Schedules a debounced save after user edits."""

        if self.editor_widget is None:
            return

        if self._editor_loading_content:
            self.editor_widget.edit_modified(False)
            return

        if not self.editor_widget.edit_modified():
            return

        self.editor_widget.edit_modified(False)
        became_dirty = not self._editor_has_unsaved_changes
        self._editor_has_unsaved_changes = True
        self.status_var.set("Ungespeichert")
        if became_dirty and hasattr(self, "_refresh_migration_bar"):
            self._refresh_migration_bar()
        self._queue_editor_highlighting()
        self._queue_editor_diagnostics()
        self._queue_editor_outline()

        if self._editor_save_after_id is not None:
            self.root.after_cancel(self._editor_save_after_id)

        self._editor_save_after_id = self.root.after(self._editor_save_delay_ms, self._save_editor_content)
        self._queue_editor_auto_preview_refresh()

    def _save_editor_content(self):
        """Writes the current editor content back to the selected markdown file."""

        self._editor_save_after_id = None

        if self.editor_widget is None:
            return

        input_path = self._validate_input()
        if input_path is None:
            return

        if self._requires_markdown_save_as(input_path):
            # Nie unter einer unbekannten Endung als Markdown speichern (I1): die
            # Originaldatei bleibt unverändert, gespeichert wird nur per Speichern-unter als .md.
            self._editor_has_unsaved_changes = True
            self._prompt_markdown_save_as_once(input_path)
            return

        content = self.editor_widget.get("1.0", "end-1c")
        try:
            self.status_var.set("Speichert…")
            preferences = getattr(self, "user_preferences", {})
            if bool(preferences.get("backup_on_save", False)) and input_path.exists():
                keep_versions = int(str(preferences.get("backup_versions_keep", 3) or 3))
                keep_versions = max(1, min(50, keep_versions))
                backup_dir = input_path.parent / "backup_pre_migration"
                backup_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{input_path.stem}_{timestamp}{input_path.suffix}"
                backup_path = backup_dir / backup_name
                shutil.copy2(input_path, backup_path)

                backup_files = sorted(
                    backup_dir.glob(f"{input_path.stem}_*{input_path.suffix}"),
                    key=lambda path: path.stat().st_mtime,
                    reverse=True,
                )
                for stale_file in backup_files[keep_versions:]:
                    try:
                        stale_file.unlink()
                    except Exception:
                        pass

            input_path.write_text(content, encoding="utf-8")
            self._record_editor_manual_block_type_usage(content)
            self._editor_has_unsaved_changes = False
            self._update_editor_source_snapshot(input_path)
            self.status_var.set("Gespeichert")
            if hasattr(self, "_refresh_migration_bar"):
                self._refresh_migration_bar()
            self._queue_editor_highlighting(immediate=True)
            self._queue_editor_diagnostics(immediate=True)
            self._queue_editor_outline(immediate=True)
        except Exception as error:
            self.status_var.set("Speichern fehlgeschlagen")
            messagebox.showerror("Speichern fehlgeschlagen", str(error))
