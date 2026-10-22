from app.ui.blatt_shortcuts import build_preview_keybinding_registry
from bw_gui.contracts.key_spec import KeySpec
from bw_gui.contracts.keybinding import UI_MODE_PREVIEW


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


def test_q_sets_a4_landscape_only_in_preview_and_never_while_typing():
    calls = []

    class _RecordingApp(_AnyMethodStubApp):
        def _set_page_format(self, page_format):
            calls.append(page_format)

    registry = build_preview_keybinding_registry(_RecordingApp())
    definition = next(d for d in registry.all() if d.keys == (KeySpec.parse("Q"),))

    assert definition.binding_id == "preview.page_a4_landscape"
    assert definition.modes == (UI_MODE_PREVIEW,)
    assert definition.allow_when_text_input is False
    definition.handler()
    assert calls == ["a4_landscape"]
