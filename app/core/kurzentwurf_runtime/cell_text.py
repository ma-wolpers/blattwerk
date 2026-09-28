"""Kurzentwurf: Zeilen-/Absatzlogik für Zelleninhalte vor dem HTML-Rendern.

Konvention (analog Arbeitsblatt/`nl2br`):

- einfacher Zeilenumbruch in der Quelle = Zeilenumbruch (`<br>`) in der Zelle,
- Leerzeile = neuer Absatz,
- abschließendes `\\` am Zeilenende = expliziter harter Umbruch. Das ist nur
  in der Spalte Lernaktivitäten (`s<`) nötig, weil dort sonst jede
  Folgezeile als eigener "S:innen"-Eintrag gilt; in allen anderen Spalten
  wird das `\\` einfach entfernt.

`render_html` ruft diese Helfer auf, die eigentliche Absatz-/Listen-
Erzeugung bleibt in `render_html._render_text`.
"""

from __future__ import annotations

HARD_BREAK_SUFFIX = "\\"


def ends_with_hard_break(line: str) -> bool:
    """Prüft, ob `line` mit genau einem `\\` endet (harter Umbruch).

    Ein doppeltes `\\\\` am Zeilenende zählt bewusst **nicht** als Umbruch,
    sondern bleibt als wörtlicher Text stehen (Escape eines Backslashs).
    """
    text = line.rstrip()
    return text.endswith(HARD_BREAK_SUFFIX) and not text.endswith(HARD_BREAK_SUFFIX * 2)


def strip_hard_break(line: str) -> str:
    """Entfernt einen einzelnen abschließenden `\\` (harter Umbruch) von `line`.

    Wird beim Rendern jeder Absatz-/Listenzeile angewandt, damit das
    Umbruchzeichen nie sichtbar in der Ausgabe landet.
    """
    text = line.rstrip()
    if ends_with_hard_break(text):
        return text[: -len(HARD_BREAK_SUFFIX)].rstrip()
    return text


def label_entries(text: str, marker_label: str) -> str:
    """Stellt jedem `s<`-Eintrag das Marker-Label (z. B. **S:innen**) voran.

    Jede Quellzeile ist ein eigener Eintrag -- außer die vorige Zeile endet
    mit `\\`, dann setzt die Zeile denselben Eintrag nach einem Umbruch
    fort (ohne erneutes Label). Leerzeilen bleiben als Absatzgrenze
    erhalten (mehrere hintereinander werden zu einer zusammengefasst).
    Ohne Label wird der Text unverändert (nur getrimmt) zurückgegeben.
    """
    content = str(text or "").strip()
    if not content:
        return ""

    label = str(marker_label or "").strip()
    if not label:
        return content

    output: list[str] = []
    continues_entry = False
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            if output and output[-1] != "":
                output.append("")
            continues_entry = False
            continue
        output.append(line if continues_entry else f"**{label}** {line}")
        continues_entry = ends_with_hard_break(line)
    return "\n".join(output).strip()


def label_block(text: str, marker_label: str) -> str:
    """Setzt das Marker-Label (z. B. **Antizipiert:**) vor einen `ant<`-Block.

    Einzeiliger Inhalt steht direkt hinter dem Label, mehrzeiliger Inhalt
    beginnt in der Zeile nach dem Label. Leerzeilen im Block bleiben als
    Absatzgrenze erhalten (mehrere hintereinander werden zusammengefasst).
    """
    content = str(text or "").strip()
    if not content:
        return ""

    label = str(marker_label or "").strip()
    if not label:
        return content

    lines: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line or (lines and lines[-1] != ""):
            lines.append(line)
    if len(lines) == 1:
        return f"**{label}** {lines[0]}"
    return f"**{label}**\n" + "\n".join(lines)
