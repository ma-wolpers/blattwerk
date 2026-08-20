from app.ui.blatt_shortcuts import build_preview_keybinding_registry


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

    assert registry.conflicts() == {}


def test_search_shortcuts_are_freed_up_from_previous_global_bindings():
    registry = build_preview_keybinding_registry(_AnyMethodStubApp())
    sequences = {definition.binding_id: definition.sequence for definition in registry.all()}

    # Strg+F/Strg+H sind fuer Suchen/Ersetzen im Schreibbereich reserviert
    # (editor-lokal gebunden, nicht Teil dieser globalen Registry) --
    # Schriftprofil/Lernhilfenansicht muessen daher auf andere Sequenzen
    # verlegt worden sein.
    assert sequences["global.cycle_font"] == "<Control-Shift-f>"
    assert sequences["global.help_preview"] == "<Control-Shift-h>"
    assert "<Control-f>" not in sequences.values()
    assert "<Control-h>" not in sequences.values()
