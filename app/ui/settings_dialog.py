"""Tabbed settings dialog wired to the shared bw_gui settings renderer."""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

from ..storage.user_preferences_adapter import get_tab_specs, normalize_user_preferences

ensure_bw_gui_on_path()
from bw_gui.dialogs import SettingsDialogSpec, SettingsFieldSpec, SettingsSectionSpec, TabbedSettingsDialog
from bw_gui.runtime import ui, widgets


def _resolve_field_type(raw_type: object) -> str:
    """Normalize local preference types to shared settings field types."""

    text = str(raw_type or "string").strip().lower()
    if text == "str":
        return "string"
    if text in {"string", "bool", "int", "float", "enum"}:
        return text
    return "string"


def _build_dialog_spec() -> SettingsDialogSpec:
    """Build shared dialog spec from Blattwerk preference tab metadata."""

    sections: list[SettingsSectionSpec] = []
    for tab_key, tab_label, tab_items in get_tab_specs():
        fields: list[SettingsFieldSpec] = []
        for pref_key, spec in tab_items:
            field_type = _resolve_field_type(spec.get("type"))
            enum_values = tuple(str(value) for value in list(spec.get("values", []))) if field_type == "enum" else tuple()
            hint_parts: list[str] = []
            if field_type == "int":
                hint_parts.append("Ganzzahl")
            if field_type == "float":
                hint_parts.append("Dezimalzahl")
            if spec.get("min") is not None or spec.get("max") is not None:
                hint_parts.append(f"min={spec.get('min')} max={spec.get('max')}")

            fields.append(
                SettingsFieldSpec(
                    key=pref_key,
                    label=str(spec.get("label", pref_key)),
                    field_type=field_type,
                    default=spec.get("default", ""),
                    enum_values=enum_values,
                    min_value=spec.get("min"),
                    max_value=spec.get("max"),
                    hint=" | ".join(hint_parts),
                    live_apply=bool(spec.get("live_apply", False)),
                )
            )

        sections.append(
            SettingsSectionSpec(
                key=tab_key,
                label=tab_label,
                fields=tuple(fields),
            )
        )

    return SettingsDialogSpec(sections=tuple(sections))


class _BlattwerkTabbedSettingsDialog(TabbedSettingsDialog):
    """Shared dialog wrapper with Blattwerk-specific reset and cancel behavior."""

    def __init__(self, *args, last_committed: dict[str, object], **kwargs):
        self._last_committed = normalize_user_preferences(last_committed)
        super().__init__(*args, **kwargs)

    def _build_buttons(self, root) -> None:
        buttons = widgets.Frame(root)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        buttons.columnconfigure(0, weight=1)

        widgets.Button(buttons, text="Tab-Standard", command=self._reset_active_section_defaults).grid(row=0, column=0, sticky="w")
        widgets.Button(buttons, text="Alle Standard", command=self._reset_all_defaults).grid(row=0, column=1, sticky="w", padx=(8, 0))
        widgets.Button(buttons, text="Abbrechen", command=self._on_cancel).grid(row=0, column=2, sticky="e")
        widgets.Button(buttons, text="Anwenden", command=self._on_apply).grid(row=0, column=3, sticky="e", padx=(8, 0))
        widgets.Button(buttons, text="Speichern", style="PrimaryAction.TButton", command=self._on_save).grid(
            row=0,
            column=4,
            sticky="e",
            padx=(8, 0),
        )

    def _reset_active_section_defaults(self) -> None:
        defaults = normalize_user_preferences({})
        active_section = next((item for item in self.spec.sections if item.key == self._active_section_key), None)
        if active_section is None:
            return

        for field in active_section.fields:
            var = self._field_vars.get(field.key)
            if var is None:
                continue
            value = defaults.get(field.key, field.default)
            if isinstance(var, ui.BooleanVar):
                var.set(bool(value))
            else:
                var.set(str(value))

    def _reset_all_defaults(self) -> None:
        defaults = normalize_user_preferences({})
        for key, var in self._field_vars.items():
            value = defaults.get(key, "")
            if isinstance(var, ui.BooleanVar):
                var.set(bool(value))
            else:
                var.set(str(value))

    def _on_apply(self) -> None:
        super()._on_apply()
        if self.result is not None:
            self._last_committed = normalize_user_preferences(self.result)

    def _on_cancel(self) -> None:
        if self._on_live_apply is not None:
            self._on_live_apply(dict(self._last_committed))
        super()._on_cancel()


class SettingsDialog:
    """Compatibility wrapper preserving existing Blattwerk settings callsite API."""

    def __init__(
        self,
        parent,
        *,
        theme_key: str,
        preferences: dict[str, object],
        initial_tab: str | None = None,
        on_live_apply=None,
        on_commit=None,
    ):
        normalized_preferences = normalize_user_preferences(preferences)
        dialog = _BlattwerkTabbedSettingsDialog(
            parent,
            title="Einstellungen",
            theme_key=theme_key,
            spec=_build_dialog_spec(),
            initial_values=normalized_preferences,
            initial_section=initial_tab,
            on_live_apply=on_live_apply,
            on_commit=on_commit,
            last_committed=normalized_preferences,
        )
        self.parent = parent
        self.result = dialog.result

