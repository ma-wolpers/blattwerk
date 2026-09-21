"""Seitengeometrie der Randspalten (Gutter) für Arbeitsblätter.

Chromium-Headless-Print kann keinen Inhalt in den echten `@page`-Rand
rendern. Randinhalte (Aufgabensymbole links, Worterklärungen rechts) leben
deshalb in einer *Leerspalte innerhalb* des bedruckbaren Bereichs: `body`
bekommt zusätzliches Padding, der Randinhalt ragt per `float` + negativem
Margin in dieses Padding hinein.

Dieses Modul ist die EINE Quelle für die Gutter-Breiten. Sowohl das erzeugte
CSS (`build_gutter_css`) als auch die Inhaltsbreite für den Layout-Schätzer
(`resolve_gutter_widths_cm`) lesen von hier -- so können geschätzte und
tatsächlich gerenderte Inhaltsbreite nicht stillschweigend auseinanderlaufen.

Übergangszustand (bewusst, siehe `docs/intern/ARCHITEKTUR.md`): Ob eine
rechte Worterklärungs-Spalte gebraucht wird, steht erst nach dem Rendern des
Bodys fest, der Layout-Schätzer läuft aber davor. Er kennt deshalb nur die
linke Gutter; die rechte wird beim Schätzen noch nicht abgezogen. Langfristig
gehört eine gemeinsame Seitengeometrie (`@page` -> Gutter -> Inhaltsbreite)
in den Schätzer.
"""

from __future__ import annotations

TASK_MARGIN_GUTTER_CM = 1.3
"""Breite der linken Randspalte für Aufgabensymbole.

Layout-Parameter, keine fachliche Konstante: reicht für Icons in 1em-Größe
(11pt ~ 0.4cm) plus Luft; bei drei Symbolen umbrechen sie in eine zweite
Zeile. Visuell kalibriert."""

WORD_NOTE_GUTTER_CM = 2.6
"""Breite der rechten Randspalte für Worterklärungen.

Layout-Parameter, keine fachliche Konstante: ausgelegt für kurze deutsche
Erklärungen in 0.7em-Schrift (~4-6 Wörter pro Zeile bei 2.4cm Textbreite).
Visuell kalibriert."""


def resolve_gutter_widths_cm(reserve_gutters: bool, has_word_notes: bool = False):
    """Liefert `(links_cm, rechts_cm)` der tatsächlich reservierten Randspalten."""
    if not reserve_gutters:
        return 0.0, 0.0
    return TASK_MARGIN_GUTTER_CM, (WORD_NOTE_GUTTER_CM if has_word_notes else 0.0)


def build_gutter_css(reserve_gutters: bool, has_word_notes: bool = False) -> str:
    """Erzeugt das CSS, das die Randspalten reserviert und Randinhalt hineinlegt.

    Ohne `reserve_gutters` (Präsentation, Hilfekarten) bleibt nur der
    statische Inline-Fallback aus `worksheet.css` aktiv. Innerhalb von
    `:::columns` (`.column`) wird bewusst NICHT in den Rand geschoben, weil
    der Randinhalt dort in die Nachbarspalte ragen würde: Symbole stehen dort
    inline über dem Label, Notizen bleiben als schmaler Float in der Spalte.
    """
    if not reserve_gutters:
        return ""

    css = f"""
:root {{
    --task-margin-gutter: {TASK_MARGIN_GUTTER_CM}cm;
}}

body {{
    padding-left: var(--task-margin-gutter);
}}

.task-margin-icons {{
    float: left;
    margin-left: calc(-1 * var(--task-margin-gutter));
    width: var(--task-margin-gutter);
    box-sizing: border-box;
    padding-right: 0.25cm;
    justify-content: flex-end;
}}

.column .task-margin-icons {{
    float: none;
    margin-left: 0;
    width: auto;
    padding-right: 0;
    justify-content: flex-start;
}}
"""
    if has_word_notes:
        css += f"""
:root {{
    --word-note-gutter: {WORD_NOTE_GUTTER_CM}cm;
}}

body {{
    padding-right: var(--word-note-gutter);
}}

.word-note-text {{
    display: block;
    float: right;
    clear: right;
    margin-right: calc(-1 * var(--word-note-gutter));
    width: calc(var(--word-note-gutter) - 0.35cm);
}}

.column .word-note-text {{
    margin-right: 0;
}}
"""
    return css
