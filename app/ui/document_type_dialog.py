"""Modal selection dialog for new Blattwerk document types."""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui, widgets

from ..core.document_types import (
    DOCUMENT_TYPE_KURZENTWURF,
    DOCUMENT_TYPE_PRESENTATION,
    DOCUMENT_TYPE_WORKSHEET,
    normalize_document_type,
)


def prompt_new_document_type(app, *, initial_value: str = DOCUMENT_TYPE_WORKSHEET) -> str | None:
    selected_document_type = ui.StringVar(value=normalize_document_type(initial_value))
    result: dict[str, str | None] = {"value": None}

    window = ui.Toplevel(app.root)
    window.title("Neues Dokument")
    window.transient(app.root)
    window.resizable(False, False)

    try:
        window.grab_set()
    except Exception:
        pass

    if hasattr(app, "_track_popup_window"):
        app._track_popup_window(window)

    container = widgets.Frame(window, padding=14)
    container.grid(row=0, column=0, sticky="nsew")
    container.columnconfigure(0, weight=1)

    widgets.Label(
        container,
        text="Was moechtest du erstellen?",
        font=("Segoe UI", 11, "bold"),
        anchor="w",
        justify="left",
    ).grid(row=0, column=0, sticky="ew")

    widgets.Label(
        container,
        text="Der Dokumenttyp wird ueber YAML-Daten angelegt und spaeter daran wiedererkannt.",
        anchor="w",
        justify="left",
        wraplength=360,
    ).grid(row=1, column=0, sticky="ew", pady=(6, 10))

    option_frame = widgets.Frame(container)
    option_frame.grid(row=2, column=0, sticky="ew")
    option_frame.columnconfigure(0, weight=1)

    _build_option(
        option_frame,
        row=0,
        variable=selected_document_type,
        value=DOCUMENT_TYPE_WORKSHEET,
        label="Aufgabenblatt",
        hint="Blattwerk-Standard mit Aufgaben-/Loesungspfad; Test bleibt spaeter ueber YAML umschaltbar.",
    )
    _build_option(
        option_frame,
        row=1,
        variable=selected_document_type,
        value=DOCUMENT_TYPE_PRESENTATION,
        label="Praesentation",
        hint="Blattwerk-Folienmodus mit `mode: presentation`.",
    )
    _build_option(
        option_frame,
        row=2,
        variable=selected_document_type,
        value=DOCUMENT_TYPE_KURZENTWURF,
        label="Kurzentwurf",
        hint="Kurzentwurf-DSL mit `Stundenthema`, `Lerngruppe` und `start` im YAML.",
    )

    button_row = widgets.Frame(container)
    button_row.grid(row=3, column=0, sticky="ew", pady=(12, 0))
    button_row.columnconfigure(0, weight=1)

    def _confirm(_event=None):
        result["value"] = normalize_document_type(selected_document_type.get())
        window.destroy()

    def _cancel(_event=None):
        result["value"] = None
        window.destroy()

    widgets.Button(button_row, text="Abbrechen", command=_cancel).grid(row=0, column=1, sticky="e")
    widgets.Button(button_row, text="Weiter", style="PrimaryAction.TButton", command=_confirm).grid(
        row=0,
        column=2,
        sticky="e",
        padx=(8, 0),
    )

    window.bind("<Escape>", _cancel)
    window.bind("<Return>", _confirm)

    window.update_idletasks()
    _center_modal_on_root(window, app.root)
    window.focus_force()
    window.wait_window()
    return result["value"]


def _build_option(parent, *, row: int, variable, value: str, label: str, hint: str) -> None:
    frame = widgets.Frame(parent, padding=(0, 0, 0, 8))
    frame.grid(row=row, column=0, sticky="ew")
    frame.columnconfigure(1, weight=1)

    widgets.Radiobutton(frame, variable=variable, value=value).grid(row=0, column=0, sticky="nw", pady=(2, 0))
    widgets.Label(frame, text=label, font=("Segoe UI", 10, "bold"), anchor="w", justify="left").grid(
        row=0,
        column=1,
        sticky="ew",
    )
    widgets.Label(frame, text=hint, anchor="w", justify="left", wraplength=340).grid(
        row=1,
        column=1,
        sticky="ew",
        pady=(2, 0),
    )


def _center_modal_on_root(window, root) -> None:
    try:
        root.update_idletasks()
        window_width = max(window.winfo_width(), 420)
        window_height = max(window.winfo_height(), 220)
        x = root.winfo_rootx() + max((root.winfo_width() - window_width) // 2, 24)
        y = root.winfo_rooty() + max((root.winfo_height() - window_height) // 3, 24)
        window.geometry(f"{window_width}x{window_height}+{x}+{y}")
    except Exception:
        pass