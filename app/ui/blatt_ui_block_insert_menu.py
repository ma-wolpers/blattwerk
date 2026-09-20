"""Editor-Mixin für den Menüpunkt "Einfügen" (Alt+I)."""

from __future__ import annotations

from ..core.block_insert_menu_families import BLOCK_INSERT_FAMILIES, BLOCK_INSERT_STANDALONE
from ..core.block_insert_snippets import BLOCK_INSERT_SNIPPETS
from ..core.completion_catalogs import get_completion_block_type_detail

_IMAGE_MENU_LABEL = "Bild (image)"
_IMAGE_INSERT_SNIPPET = '![Bildbeschreibung](bild.png "w=80% align=center")\n\x01'


class BlattwerkAppBlockInsertMenuMixin:
    """Baut die Menüleisten-Aktion "Einfügen" (ersetzt das alte Strg+B-Popup).

    Liefert die verschachtelte Dict-Struktur für `section_spec`/
    `_to_shared_menu_items` (`blatt_ui_base.py`/`blatt_ui_style.py`): ein Untermenü
    pro Blockfamilie aus `block_insert_menu_families.py`, plus die strukturell
    einzigartigen Blöcke und die "Bild"-Aktion direkt auf oberster Ebene. Bewusst
    "Einfügen" statt "Block hinzufügen" als Menütitel -- breiter angelegt, damit
    künftig auch Nicht-Block-Aktionen (z. B. ein Seitenumbruch-Eintrag) direkt
    neben den Blockfamilien Platz finden, ohne eine weitere Verschachtelungsebene
    zu brauchen. Jeder Blatt-Eintrag trägt zusätzlich eine `description`, die
    `bw_gui`s `MenuItem.description`-Mechanismus (Hover-Flyout, siehe
    `bw_gui.menu`) beim Hovern anzeigt.
    """

    def _menu_insert_block_items(self):
        """Baut die Top-Level-Items des Menüs "Einfügen".

        Reihenfolge: erst die Familien-Untermenüs, danach die Einzelgänger
        (`BLOCK_INSERT_STANDALONE`), zuletzt "Bild" -- konsistent mit der
        bisherigen Reihenfolge im alten Strg+B-Popup.
        """

        items = [
            {
                "type": "submenu",
                "label": family_label,
                "items": [self._block_insert_command_item(label, block_type) for label, block_type in entries],
            }
            for family_label, entries in BLOCK_INSERT_FAMILIES
        ]
        items.extend(
            self._block_insert_command_item(label, block_type) for label, block_type in BLOCK_INSERT_STANDALONE
        )
        items.append(self._image_insert_command_item())
        return items

    def _block_insert_command_item(self, label: str, block_type: str) -> dict:
        """Baut einen einzelnen Blatt-Eintrag für einen echten `:::`-Blocktyp.

        Die `description` kommt aus `get_completion_block_type_detail()` -- derselben
        Quelle wie die `:::`-Autovervollständigung, damit keine zweite
        Blockerklärung gepflegt werden muss. Der Klick fügt die Vorlage aus
        `BLOCK_INSERT_SNIPPETS` unverändert über die bestehende
        `_insert_editor_snippet` (aus `BlattwerkAppEditorMixin`) ein.
        """

        detail = get_completion_block_type_detail(block_type)
        return {
            "type": "command",
            "label": label,
            "command": lambda bt=block_type: self._insert_editor_snippet(BLOCK_INSERT_SNIPPETS[bt]),
            "description": detail["description"] if detail is not None else None,
        }

    def _image_insert_command_item(self) -> dict:
        """Baut den "Bild"-Eintrag -- kein `:::`-Block, daher ohne `description`
        (keine `get_completion_block_type_detail`-Quelle für einen Nicht-Blocktyp)
        und mit eigener, fest hinterlegter Markdown-Bildsyntax statt eines Eintrags
        aus `BLOCK_INSERT_SNIPPETS`."""

        return {
            "type": "command",
            "label": _IMAGE_MENU_LABEL,
            "command": lambda: self._insert_editor_snippet(_IMAGE_INSERT_SNIPPET),
        }
