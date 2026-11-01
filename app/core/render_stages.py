"""Die Stufen eines Render-Laufs. Der Core meldet sie über `render_job.stage`, das Messskript
`tools/measure_render.py` wertet sie aus."""

from __future__ import annotations

STAGE_VALIDATE = "validate"
STAGE_HTML = "html"
STAGE_PRINT = "print"
STAGE_STAMP = "stamp"
STAGE_WORD_NOTES = "word_notes"
STAGE_APPENDIX = "appendix"
STAGE_RASTER = "raster"

RENDER_STAGES = frozenset(
    {STAGE_VALIDATE, STAGE_HTML, STAGE_PRINT, STAGE_STAMP, STAGE_WORD_NOTES, STAGE_APPENDIX, STAGE_RASTER}
)
