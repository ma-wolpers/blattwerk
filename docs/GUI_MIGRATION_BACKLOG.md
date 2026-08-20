# GUI Migration Backlog

## Active Exemptions
- app/ui/blatt_ui.py
  remove_by: 2026-12-31
  reason: >
    Reine Fassade (bündelt nur Mixins zu `class BlattwerkApp(...)`), kein
    eigener GUI-Bootstrap. Der tatsächliche Shared-Contract (Vererbung von
    `bw_gui.runtime.BwBaseWindow`, `build_menu()` über `bw_gui.menu.section_spec`)
    lebt bereits korrekt in `app/ui/blatt_ui_base.py` und wird dort von
    `_check_shared_ui_contract_hardening` geprüft. Eine zusätzliche Prüfung der
    Facade-Datei würde nur die dortigen Re-Exporte duplizieren, ohne neue
    Information zu liefern. Baseline entfällt, sobald `blatt_ui.py` entweder
    entfernt oder aus `FUTURE_GUI_ENTRY_FILE_NAMES` gestrichen wird.

## Notes
- This backlog tracks all currently allowed baseline/exemption entries referenced by guardrails.
- No legacy ui/widgets/tui class exemptions are active at the moment.
