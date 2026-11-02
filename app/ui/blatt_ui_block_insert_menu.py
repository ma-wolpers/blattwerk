"""Editor-Mixin für das Menü "Einfügen" (Titel und Alt-Buchstabe: `INSERT_MENU_LABEL`/`INSERT_MENU_ALT`)."""

from __future__ import annotations

from ..core.block_insert_menu_families import (
    BLOCK_INSERT_FAMILIES,
    BLOCK_INSERT_STANDALONE,
    IMAGE_INSERT_ENTRY,
    insert_menu_label,
)
from ..core.block_insert_snippets import BLOCK_INSERT_SNIPPETS, IMAGE_INSERT_SNIPPET
from ..core.completion_catalogs import get_completion_block_type_detail


class BlattwerkAppBlockInsertMenuMixin:
    """Baut die Menüleisten-Aktion "Einfügen" (ersetzt das alte Strg+B-Popup).

    Liefert die verschachtelte Dict-Struktur für `section_spec`/
    `_to_shared_menu_items` (`blatt_ui_base.py`/`blatt_ui_menu_items.py`): ein
    Untermenü pro Blockfamilie aus `block_insert_menu_families.py`, plus die
    strukturell einzigartigen Blöcke und die "Bild"-Aktion direkt auf oberster
    Ebene. Beschriftung und Kennbuchstabe jedes Eintrags kommen aus derselben
    Quelle (`insert_menu_label`, drittes Element der Einträge); bw-gui zeigt
    den Buchstaben in der Zeile und löst den Eintrag damit aus, auch aus einem
    geschlossenen Untermenü (Alt+I, dann Buchstabe). Jeder Blatt-Eintrag trägt
    zusätzlich eine `description` (Hover-Flyout von bw-gui).
    """

    def _menu_insert_block_items(self):
        """Baut die Top-Level-Items des Menüs "Einfügen".

        Reihenfolge: erst die Familien-Untermenüs, danach die Einzelgänger
        (`BLOCK_INSERT_STANDALONE`), zuletzt "Bild" -- dieselbe Reihenfolge wie
        `iter_insert_entries`.
        """

        items = [
            {
                "type": "submenu",
                "label": family_label,
                "items": [self._block_insert_command_item(*entry) for entry in entries],
            }
            for family_label, entries in BLOCK_INSERT_FAMILIES
        ]
        items.extend(self._block_insert_command_item(*entry) for entry in BLOCK_INSERT_STANDALONE)
        items.append(self._image_insert_command_item())
        return items

    def _block_insert_command_item(self, title: str, block_type: str, mnemonic: str | None) -> dict:
        """Baut einen einzelnen Blatt-Eintrag für einen echten `:::`-Blocktyp.

        Die `description` kommt aus `get_completion_block_type_detail()` -- derselben
        Quelle wie die `:::`-Autovervollständigung, damit keine zweite
        Blockerklärung gepflegt werden muss. Der Klick (oder der Kennbuchstabe)
        fügt die Vorlage aus `BLOCK_INSERT_SNIPPETS` über `_insert_block_from_menu` ein
        (an der Markierung bzw. am Cursor, siehe `blatt_ui_editor_block_insert.py`).
        """

        detail = get_completion_block_type_detail(block_type)
        return {
            "type": "command",
            "label": insert_menu_label(title, block_type),
            "mnemonic": mnemonic,
            "command": lambda bt=block_type: self._insert_block_from_menu(BLOCK_INSERT_SNIPPETS[bt], bt),
            "description": detail["description"] if detail is not None else None,
        }

    def _image_insert_command_item(self) -> dict:
        """Baut den "Bild"-Eintrag -- kein `:::`-Block, daher ohne `description`
        (keine `get_completion_block_type_detail`-Quelle für einen Nicht-Blocktyp)
        und mit der Vorlage `IMAGE_INSERT_SNIPPET` statt eines Eintrags aus
        `BLOCK_INSERT_SNIPPETS`."""

        title, key, mnemonic = IMAGE_INSERT_ENTRY
        return {
            "type": "command",
            "label": insert_menu_label(title, key),
            "mnemonic": mnemonic,
            "command": lambda: self._insert_block_from_menu(IMAGE_INSERT_SNIPPET, None),
        }
