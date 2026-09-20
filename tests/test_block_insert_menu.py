"""Tests für `BlattwerkAppBlockInsertMenuMixin` -- das Menü "Einfügen".

`BLOCK_INSERT_SNIPPETS` ist hier explizit die Quelle der Wahrheit für die
einfügbaren Blocktypen (nicht `BLOCK_INSERT_FAMILIES`/`BLOCK_INSERT_STANDALONE`
selbst -- sonst würde ein Test die Menüdefinition nur gegen sich selbst
validieren). Die Familien selbst (Anzahl, Namen, Zuschnitt) sind eine
veränderbare redaktionelle Gruppierung (siehe `block_insert_menu_families.py`)
und deshalb bewusst *nicht* Gegenstand dieser Tests.
"""

from app.core.block_insert_menu_families import BLOCK_INSERT_FAMILIES, BLOCK_INSERT_STANDALONE
from app.core.block_insert_snippets import BLOCK_INSERT_SNIPPETS
from app.ui.blatt_ui_block_insert_menu import BlattwerkAppBlockInsertMenuMixin, _IMAGE_INSERT_SNIPPET


class _FakeApp(BlattwerkAppBlockInsertMenuMixin):
    """Minimaler Host für den Mixin -- steht für `BlattwerkAppEditorMixin`'s
    `_insert_editor_snippet`, ohne echten Tk-Editor aufzubauen."""

    def __init__(self):
        self.inserted: list[str] = []

    def _insert_editor_snippet(self, template: str):
        self.inserted.append(template)


def _iter_leaf_commands(items: list[dict]):
    """Flacht die verschachtelte Menüstruktur zu allen Blatt-Command-Einträgen ab."""

    for entry in items:
        if entry["type"] == "submenu":
            yield from entry["items"]
        else:
            yield entry


def _referenced_block_types() -> list[str]:
    referenced = [block_type for _label, entries in BLOCK_INSERT_FAMILIES for _leaf_label, block_type in entries]
    referenced.extend(block_type for _label, block_type in BLOCK_INSERT_STANDALONE)
    return referenced


def test_every_block_insert_snippet_type_appears_exactly_once_in_menu():
    referenced = _referenced_block_types()
    assert len(referenced) == len(set(referenced)), "Ein Blocktyp kommt mehrfach im Einfügemenü vor"
    assert set(referenced) == set(BLOCK_INSERT_SNIPPETS), (
        "BLOCK_INSERT_FAMILIES/BLOCK_INSERT_STANDALONE deckt nicht exakt die Blocktypen "
        "aus BLOCK_INSERT_SNIPPETS ab (Quelle der Wahrheit für einfügbare Blocktypen)"
    )


def test_no_menu_entry_references_an_unknown_snippet_key():
    for block_type in _referenced_block_types():
        assert block_type in BLOCK_INSERT_SNIPPETS, f"Unbekannter Snippet-Schlüssel im Einfügemenü: {block_type!r}"


def test_menu_structure_is_syntactically_well_formed():
    items = _FakeApp()._menu_insert_block_items()
    assert isinstance(items, list) and items

    for entry in items:
        assert entry["type"] in {"submenu", "command"}
        assert entry.get("label")
        if entry["type"] == "submenu":
            assert isinstance(entry["items"], list) and entry["items"]
            for leaf in entry["items"]:
                assert leaf["type"] == "command"
                assert leaf.get("label")
                assert callable(leaf["command"])
        else:
            assert callable(entry["command"])


def test_every_real_block_entry_has_a_non_empty_description():
    """Für das Blattwerk-Blockmenü gilt ein strengerer Vertrag als in der
    generischen bw_gui-API: jeder echte Blockeintrag (alles außer "Bild", kein
    `:::`-Block) muss eine nicht-leere `description` aus
    `get_completion_block_type_detail()` besitzen."""

    items = _FakeApp()._menu_insert_block_items()
    for entry in _iter_leaf_commands(items):
        if entry["label"] == "Bild (image)":
            continue
        assert entry.get("description"), f"{entry['label']!r} hat keine Blockerklärung (description)"


def test_image_entry_has_no_description_and_is_not_backed_by_a_block_snippet():
    items = _FakeApp()._menu_insert_block_items()
    image_entry = next(entry for entry in _iter_leaf_commands(items) if entry["label"] == "Bild (image)")
    assert image_entry.get("description") is None


def test_clicking_a_family_entry_inserts_its_block_insert_snippet():
    app = _FakeApp()
    items = app._menu_insert_block_items()
    boxen = next(entry for entry in items if entry["label"] == "Boxen/Hinweise")
    info_item = next(leaf for leaf in boxen["items"] if leaf["label"].startswith("Infobox"))

    info_item["command"]()

    assert app.inserted == [BLOCK_INSERT_SNIPPETS["info"]]


def test_clicking_a_standalone_entry_inserts_its_block_insert_snippet():
    app = _FakeApp()
    items = app._menu_insert_block_items()
    columns_item = next(entry for entry in _iter_leaf_commands(items) if entry["label"].startswith("Spalten-Layout"))

    columns_item["command"]()

    assert app.inserted == [BLOCK_INSERT_SNIPPETS["columns"]]


def test_clicking_the_image_entry_inserts_the_fixed_image_snippet():
    app = _FakeApp()
    items = app._menu_insert_block_items()
    image_item = next(entry for entry in _iter_leaf_commands(items) if entry["label"] == "Bild (image)")

    image_item["command"]()

    assert app.inserted == [_IMAGE_INSERT_SNIPPET]
