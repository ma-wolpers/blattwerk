"""Hinweisleiste für alte Blattwerk-`.md`-Dateien mit 1-Klick-Migration (Plan Phase 3).

* Klassifiziert wird der **Buffer-Text** mit derselben reinen Funktion wie im
  Batch (`migration.classify`); der Editorzustand ändert die Regel nie.
* Nur bei `sicher` gibt es den 1-Klick-Button; bei `conflict`/`unklar`/
  `ungueltiger_marker` nur einen Hinweis, bei `kein_blattwerk` keine Leiste.
* **Ungespeicherter Buffer:** statt „Jetzt migrieren“ gibt es „Speichern und
  migrieren“: speichern, Plattenstand muss gleich dem Buffer sein, dann ein
  Ein-Datei-Plan über denselben Executor (mit `migration.lock`). Es wird nie
  ein anderer Plattenstand als der Buffer migriert.
* Nach Erfolg: alten Tab schließen, Zieldatei neu von der Platte öffnen;
  danach bietet die Leiste „Rückgängig“ an (dieselbe Undo-Logik).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import widgets

from ..bootstrap.process_locks import acquire_migration_lock, current_app_lock, default_lock_dir
from ..core.document_type_registry import spec_for_type
from ..core.migration.classify import STATUS_CONFLICT, STATUS_INVALID_MARKER, STATUS_SAFE, STATUS_UNCLEAR, classify
from ..core.migration.plan import plan_single_file
from ..core.migration.runner import default_runs_dir, execute_plan, new_run_dir, undo_run, write_plan
from ..storage.migration_side_state_store import LocalConfigSideStateStore
from .dialog_services import messagebox

_HINTS = {
    STATUS_CONFLICT: "Diese Datei enthält widersprüchliche Blattwerk-Hinweise und wird nicht automatisch umgestellt.",
    STATUS_UNCLEAR: "Diese Datei enthält möglicherweise Blattwerk-Syntax; der Typ ist nicht eindeutig.",
    STATUS_INVALID_MARKER: "Diese Datei hat einen ungültigen Eintrag `document_type` und wird nicht umgestellt.",
}


class GuiMigrationResolver:
    """Konflikt-Rückfragen als Dialoge (gleiche Auswahl wie in der CLI)."""

    def resolve(self, kind, item_label, choices):
        if "behalten" in choices:
            answer = messagebox.askyesnocancel(
                "Datei wurde verändert",
                f"„{item_label}“ wurde seit der Umstellung bearbeitet.\n\n"
                "Ja: bearbeitete Datei behalten\nNein: Original zusätzlich wiederherstellen\nAbbrechen: nichts tun",
            )
            return "behalten" if answer is True else ("parallel" if answer is False else "abbrechen")
        skip = messagebox.askyesno("Konflikt", f"Konflikt bei „{item_label}“ ({kind}).\n\nDatei überspringen?")
        return "ueberspringen" if skip else "abbrechen"


class BlattwerkMigrationBarMixin:
    """Baut und steuert die Migrationsleiste über der Vorschau."""

    def _build_migration_bar(self, parent, before) -> None:
        self._migration_bar = widgets.Frame(parent, padding=(8, 6))
        self._migration_bar_before = before
        self._migration_bar_label = widgets.Label(self._migration_bar, text="", anchor="w", justify="left", wraplength=640)
        self._migration_bar_label.pack(side="left", fill="x", expand=True)
        self._migration_bar_button = widgets.Button(self._migration_bar, text="", command=self._on_migration_bar_action)
        self._migration_bar_action = None
        self._migration_last_run = None

    def _show_migration_bar(self, text: str, button_text: str | None, action) -> None:
        bar = getattr(self, "_migration_bar", None)
        if bar is None:
            return
        self._migration_bar_label.configure(text=text)
        self._migration_bar_action = action
        if button_text:
            self._migration_bar_button.configure(text=button_text)
            if not self._migration_bar_button.winfo_manager():
                self._migration_bar_button.pack(side="right", padx=(8, 0))
        elif self._migration_bar_button.winfo_manager():
            self._migration_bar_button.pack_forget()
        if not bar.winfo_manager():
            bar.pack(fill="x", before=self._migration_bar_before)

    def _hide_migration_bar(self) -> None:
        bar = getattr(self, "_migration_bar", None)
        if bar is not None and bar.winfo_manager():
            bar.pack_forget()

    def _active_buffer_text(self, path: Path) -> str:
        editor = getattr(self, "editor_widget", None)
        if editor is not None:
            return editor.get("1.0", "end-1c")
        return path.read_text(encoding="utf-8")

    def _refresh_migration_bar(self) -> None:
        """Zeigt je nach Klassifikation des aktiven `.md`-Buffers Leiste, Hinweis oder nichts."""
        input_text = self._clean_path_text(self.input_var.get()) if hasattr(self, "input_var") else ""
        path = Path(input_text) if input_text else None
        last_run = getattr(self, "_migration_last_run", None)
        if path is not None and last_run is not None and path == last_run[1]:
            self._show_migration_bar("Datei wurde auf die neue Endung umgestellt.", "Rückgängig", self._undo_last_migration)
            return
        if path is None or path.suffix.lower() != ".md" or not path.exists():
            self._hide_migration_bar()
            return
        try:
            result = classify(path.name, self._active_buffer_text(path))
        except Exception:
            self._hide_migration_bar()
            return
        if result.status == STATUS_SAFE:
            label = spec_for_type(result.target_type)
            dirty = bool(getattr(self, "_editor_has_unsaved_changes", False))
            self._show_migration_bar(
                f"Diese Datei enthält Blattwerk-Syntax – als {label.extension} migrieren? "
                f"({path.name} → {path.stem.removesuffix('.kwe')}{label.extension}, {label.label})",
                "Speichern und migrieren" if dirty else "Jetzt migrieren",
                lambda: self._migrate_active_markdown(path),
            )
        elif result.status in _HINTS:
            self._show_migration_bar(f"{_HINTS[result.status]} (Signale: {', '.join(result.signals) or '-'})", None, None)
        else:
            self._hide_migration_bar()

    def _on_migration_bar_action(self) -> None:
        action = getattr(self, "_migration_bar_action", None)
        if action is not None:
            action()

    def _migrate_active_markdown(self, path: Path) -> None:
        """1-Klick-Migration der aktiven Datei (nie ein anderer Stand als der Buffer)."""
        # Speichern über den Flush-Pfad: bricht auch ein noch geplantes Autosave ab,
        # damit es später nicht in den alten Pfad schreibt.
        if hasattr(self, "_flush_unsaved_editor_changes") and not self._flush_unsaved_editor_changes():
            return
        # Der Editor speichert per `write_text` (Textmodus: unter Windows CRLF), der Tk-Buffer
        # hält LF. Verglichen wird deshalb nach universeller Zeilenend-Dekodierung.
        if path.read_text(encoding="utf-8") != self._active_buffer_text(path):
            messagebox.showwarning("Migration", "Gespeicherter Stand und Editor stimmen nicht überein. Bitte erneut speichern.")
            return
        plan = plan_single_file(path)
        if not plan.entries:
            status = plan.report[0].status if plan.report else "unbekannt"
            messagebox.showinfo("Migration", f"Diese Datei wird nicht umgestellt ({status}).")
            return
        run_dir = new_run_dir(default_runs_dir())
        write_plan(plan, run_dir)
        result = self._with_migration_lock(lambda: execute_plan(run_dir, store=LocalConfigSideStateStore(), resolver=GuiMigrationResolver()))
        if result is None or not result.committed:
            messagebox.showinfo("Migration", "Die Datei wurde nicht umgestellt.")
            return
        target = Path(plan.root) / plan.entries[0].target
        self._replace_tab_path(path, target)
        if hashlib.sha256(target.read_bytes()).hexdigest() != plan.entries[0].rewrite_sha256:
            messagebox.showwarning("Migration", f"Die neue Datei weicht vom erwarteten Stand ab: {target.name}")
        self._migration_last_run = (run_dir, target, path)
        self._refresh_migration_bar()
        self.status_var.set(f"Umgestellt: {path.name} → {target.name}")

    def _undo_last_migration(self) -> None:
        run_dir, target, original = self._migration_last_run
        result = self._with_migration_lock(
            lambda: undo_run(run_dir, store=LocalConfigSideStateStore(), resolver=GuiMigrationResolver())
        )
        if result is None:
            return
        self._migration_last_run = None
        if result.rolled_back:
            self._replace_tab_path(target, original)
        self._refresh_migration_bar()

    def _with_migration_lock(self, action):
        lock = acquire_migration_lock(default_lock_dir(), own_app_lock=current_app_lock())
        if lock is None:
            messagebox.showwarning("Migration", "Eine andere Blattwerk-Instanz oder Migration läuft gerade.")
            return None
        try:
            return action()
        finally:
            lock.release()

    def _replace_tab_path(self, old_path: Path, new_path: Path) -> None:
        """Schließt den Tab des alten Pfads und öffnet den neuen frisch von der Platte."""
        tab_id = self._find_open_tab_id_for_path(old_path)
        if tab_id is not None:
            self._editor_has_unsaved_changes = False
            self._close_document_tab(tab_id)
        self._open_input_path(new_path, add_recent=False, show_duplicate_message=False)
