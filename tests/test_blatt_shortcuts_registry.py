from app.ui.blatt_shortcuts import build_preview_keybinding_registry
from bw_gui.contracts.key_spec import KeySpec


class _AnyMethodStubApp:
    """Liefert für jeden Attributzugriff einen No-Op-Callable.

    `build_preview_keybinding_registry` referenziert Dutzende `app.*`-Methoden
    direkt beim Aufbau der Definitionen (nicht nur in Lambdas) -- ein echtes
    `BlattwerkApp` mit vollem Tk-Fenster ist fuer einen reinen
    Registry-Strukturtest nicht noetig.
    """

    def __getattr__(self, _name):
        def _noop(*_args, **_kwargs):
            return None

        return _noop


def test_preview_keybinding_registry_has_no_sequence_conflicts():
    registry = build_preview_keybinding_registry(_AnyMethodStubApp())

    assert registry.find_conflicts() == []


def test_search_shortcuts_are_freed_up_from_previous_global_bindings():
    registry = build_preview_keybinding_registry(_AnyMethodStubApp())
    keys = {definition.binding_id: definition.keys for definition in registry.all()}
    all_specs = {spec for specs in keys.values() for spec in specs}

    # Strg+F/Strg+H sind fuer Suchen/Ersetzen im Schreibbereich reserviert
    # (editor-lokal gebunden, nicht Teil dieser globalen Registry) --
    # Schriftprofil/Lernhilfenansicht muessen daher auf andere Tasten
    # verlegt worden sein.
    assert keys["global.cycle_font"] == (KeySpec.parse("Ctrl+Shift+F"),)
    assert keys["global.help_preview"] == (KeySpec.parse("Ctrl+Shift+H"),)
    assert KeySpec.parse("Ctrl+F") not in all_specs
    assert KeySpec.parse("Ctrl+H") not in all_specs
