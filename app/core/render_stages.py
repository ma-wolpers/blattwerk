"""Die Stufen eines Render-Laufs: eine Tabelle für Zeitmessung und Fortschrittsanzeige.

Der Core meldet Stufen nur über diese Schlüssel (`render_job.stage`). Was daraus wird,
entscheidet der jeweilige Empfänger: das Messskript sammelt Zeiten, die GUI zeigt den
Text. So gibt es genau eine Liste der Stufen statt je einer pro Verwendung.
"""

from __future__ import annotations

from dataclasses import dataclass

STAGE_VALIDATE = "validate"
STAGE_HTML = "html"
STAGE_PRINT = "print"
STAGE_STAMP = "stamp"
STAGE_WORD_NOTES = "word_notes"
STAGE_APPENDIX = "appendix"
STAGE_RASTER = "raster"


@dataclass(frozen=True)
class RenderStage:
    """Eine Stufe mit ihrem Anzeigetext.

    Attributes:
        key: Stabiler Schlüssel (`STAGE_*`), steht auch in den Messergebnissen.
        label: Sichtbarer GUI-Text.
    """

    key: str
    label: str


RENDER_STAGES: tuple[RenderStage, ...] = (
    RenderStage(STAGE_VALIDATE, "Prüfe Dokument"),
    RenderStage(STAGE_HTML, "Erzeuge Layout"),
    RenderStage(STAGE_PRINT, "Erzeuge PDF"),
    RenderStage(STAGE_STAMP, "Setze Kopf- und Fußzeile"),
    RenderStage(STAGE_WORD_NOTES, "Prüfe Wortnotizen"),
    RenderStage(STAGE_APPENDIX, "Hänge Lernhilfen an"),
    RenderStage(STAGE_RASTER, "Erzeuge Seitenbilder"),
)

_LABELS = {stage.key: stage.label for stage in RENDER_STAGES}


def stage_label(key: str) -> str:
    """Liefert den Anzeigetext einer Stufe.

    Raises:
        KeyError: Der Schlüssel steht nicht in `RENDER_STAGES`. Ein Tippfehler im Core
            soll auffallen, statt eine namenlose Stufe zu erzeugen.

    Example:
        >>> stage_label(STAGE_PRINT)
        'Erzeuge PDF'
    """
    return _LABELS[key]
