"""Schilder (`.sbw`): eine Seite pro Schild, Text so groß wie möglich und mittig.

Semantik (Dokumenttyp `schild`, Pipeline `PIPELINE_SCHILD`):

* **Trennung:** Der Rumpf nach dem Frontmatter wird an jeder Zeile getrennt,
  die (nach `strip()`) exakt `---` ist. Jedes nicht-leere Stück ist ein
  Schild. Ein Zeilenumbruch *innerhalb* eines Schilds bleibt als erzwungener
  Umbruch erhalten (`<br>`); sonst bricht der Browser nur zwischen Wörtern um.
* **Kein Markdown:** Der Schildtext wird nur HTML-escaped, nicht als Markdown
  gerendert. Ein Schild ist ein Begriff oder Satz, keine formatierte Seite.
* **Frontmatter** (Standardwert in Klammern, ungültige Werte fallen still auf
  den Standard zurück -- der Validator `schild_validator.py` meldet sie):
  `ausrichtung: hoch|quer` (hoch), `fett: ja|nein` (ja), `rand: <mm>` (15),
  `schriftgroesse: einheitlich|maximal` (einheitlich). `Titel` wird nur
  HTML-Titel und nie gedruckt.

**Warum das Auto-Fit im Browser läuft und nicht in Python:** Die größte
passende Schriftgröße hängt davon ab, wo der Browser umbricht. Eine
Python-Schätzung über Font-Metriken kann von Chromiums Umbruch abweichen und
den Text dann überlaufen lassen. Deshalb misst ein Inline-Script mit der
echten Layout-Engine (Binärsuche über ganze px). Headless Edge führt es vor
dem Drucken aus (geprüft über `write_pdf_from_html`, dasselbe Verhalten
nutzt MathJax). Ein exportiertes HTML passt sich im Browser genauso an.
`word-break: keep-all` sorgt dafür, dass ein zu langes Wort als horizontaler
Überlauf messbar wird statt getrennt zu werden.

Preview, HTML-, PDF- und PNG-Export nutzen alle `render_schild_html`, damit
Vorschau und PDF identisch bleiben.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path

import yaml

from .blatt_kern_io_pdf import write_pdf_from_html
from .export_path_guardrails import validate_export_output_path
from .frontmatter import frontmatter_bounds, load_frontmatter_yaml

ORIENTATIONS = ("hoch", "quer")
FONT_SIZE_MODES = ("einheitlich", "maximal")
BOOL_TRUE = ("ja", "true", "1", "an")
BOOL_FALSE = ("nein", "false", "0", "aus")
DEFAULT_MARGIN_MM = 15.0
MAX_MARGIN_MM = 80.0
SEPARATOR = "---"

_PAGE_MM = {"hoch": (210, 297), "quer": (297, 210)}

_STYLESHEET = """
@page {{ size: A4 {page_orientation}; margin: 0; }}
html, body {{ margin: 0; padding: 0; background: #fff; }}
.schild {{
    width: {width}mm; height: {height}mm; box-sizing: border-box; padding: {margin}mm;
    display: flex; align-items: center; justify-content: center;
    overflow: hidden; break-after: page; page-break-after: always;
}}
.schild:last-child {{ break-after: auto; page-break-after: auto; }}
.schild-text {{
    width: 100%; text-align: center; color: #000;
    font-family: Arial, "Segoe UI", sans-serif; font-weight: {weight};
    line-height: 1.2; overflow-wrap: normal; word-break: keep-all; hyphens: manual;
}}
"""

# Binärsuche je Schild; danach im Modus "einheitlich" das Minimum für alle.
# Synchron am Ende von <body>: läuft vor `load` und damit vor dem PDF-Druck.
_FIT_SCRIPT = """<script>
(function () {
  var uniform = %s;
  var texts = Array.prototype.slice.call(document.querySelectorAll('.schild-text'));
  function fits(el) {
    var box = el.parentNode;
    return el.scrollWidth <= el.clientWidth && el.scrollHeight <= box.clientHeight;
  }
  var sizes = texts.map(function (el) {
    var lo = 4, hi = 2000;
    while (lo < hi) {
      var mid = Math.ceil((lo + hi) / 2);
      el.style.fontSize = mid + 'px';
      if (fits(el)) { lo = mid; } else { hi = mid - 1; }
    }
    return lo;
  });
  var common = sizes.length ? Math.min.apply(null, sizes) : 0;
  texts.forEach(function (el, i) { el.style.fontSize = (uniform ? common : sizes[i]) + 'px'; });
})();
</script>"""


@dataclass(frozen=True)
class SchildOptions:
    """Gestaltungsoptionen eines Schilder-Dokuments (aus dem Frontmatter).

    Attributes:
        ausrichtung: `"hoch"` (A4 hochkant) oder `"quer"` (A4 quer).
        fett: Ob der Schildtext fett gesetzt wird.
        rand_mm: Seitenrand in Millimetern auf allen vier Seiten.
        schriftgroesse: `"einheitlich"` -- alle Schilder bekommen dieselbe
            Größe (die größte, bei der *jedes* Schild passt) -- oder
            `"maximal"` -- jedes Schild wird für sich so groß wie möglich.
    """

    ausrichtung: str = "hoch"
    fett: bool = True
    rand_mm: float = DEFAULT_MARGIN_MM
    schriftgroesse: str = "einheitlich"


@dataclass(frozen=True)
class Schild:
    """Ein einzelnes Schild.

    Attributes:
        text: Schildtext ohne führende/abschließende Leerzeilen; innere
            Zeilenumbrüche sind erzwungene Umbrüche.
        line_number: 1-basierte Zeile im Gesamtdokument, in der der Text
            beginnt (für Diagnosen).
    """

    text: str
    line_number: int


@dataclass(frozen=True)
class ParsedSchildDocument:
    """Ergebnis von `parse_schild`.

    Attributes:
        meta: Rohes Frontmatter-Mapping (`{}` ohne bzw. bei kaputtem YAML).
        options: Aufgelöste Optionen; ungültige Werte sind schon durch den
            Standard ersetzt.
        schilder: Alle nicht-leeren Schilder in Dokumentreihenfolge.
        empty_segment_lines: Zeilennummern der `---`-Trenner, auf die ein
            leeres Stück folgt (z. B. doppeltes `---`); für Diagnose SBW002.
    """

    meta: dict
    options: SchildOptions
    schilder: tuple[Schild, ...]
    empty_segment_lines: tuple[int, ...]


def parse_bool_option(value: object) -> bool | None:
    """Liest einen Ja/Nein-Wert; `None`, wenn er nicht eindeutig ist.

    YAML macht aus `ja` einen String, aus `true` aber schon ein `bool`;
    beides wird akzeptiert, damit Nutzer nicht über YAML-Details stolpern.
    """
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in BOOL_TRUE:
        return True
    if normalized in BOOL_FALSE:
        return False
    return None


def parse_margin_option(value: object) -> float | None:
    """Liest den Rand in mm; `None` bei Nicht-Zahl oder außerhalb 0..80 mm."""
    if isinstance(value, bool):
        return None
    try:
        margin = float(str(value).strip().replace(",", "."))
    except ValueError:
        return None
    return margin if 0 <= margin <= MAX_MARGIN_MM else None


def resolve_options(meta: dict) -> SchildOptions:
    """Baut `SchildOptions` aus dem Frontmatter; Unbekanntes wird Standard.

    Args:
        meta: Frontmatter-Mapping; fehlende Keys ergeben den Standardwert.
    """
    defaults = SchildOptions()
    orientation = str(meta.get("ausrichtung", defaults.ausrichtung)).strip().lower()
    size_mode = str(meta.get("schriftgroesse", defaults.schriftgroesse)).strip().lower()
    bold = parse_bool_option(meta.get("fett", defaults.fett))
    margin = parse_margin_option(meta.get("rand", defaults.rand_mm))
    return SchildOptions(
        ausrichtung=orientation if orientation in ORIENTATIONS else defaults.ausrichtung,
        fett=defaults.fett if bold is None else bold,
        rand_mm=defaults.rand_mm if margin is None else margin,
        schriftgroesse=size_mode if size_mode in FONT_SIZE_MODES else defaults.schriftgroesse,
    )


def split_schild_frontmatter(text: str) -> tuple[dict, str, int]:
    """Trennt Frontmatter und Rumpf nach der einen Grenzregel (`frontmatter.py`).

    Returns:
        ``(meta, body, body_start_line)``. ``body_start_line`` ist die
        1-basierte Zeilennummer der ersten Rumpfzeile, damit Diagnosen auf
        das Gesamtdokument zeigen.
    """
    source = text or ""
    bounds = frontmatter_bounds(source)
    if bounds is None:
        return {}, source.removeprefix("﻿"), 1
    try:
        meta = load_frontmatter_yaml(bounds.body(source))
    except yaml.YAMLError:
        meta = {}
    meta = meta if isinstance(meta, dict) else {}
    return meta, source[bounds.end :], bounds.content_start_line


def parse_schild(text: str) -> ParsedSchildDocument:
    """Zerlegt ein `.sbw`-Dokument in Optionen und Schilder.

    Beispiel::

        >>> doc = parse_schild("---\\nfett: nein\\n---\\nA\\n---\\nB b\\n")
        >>> [s.text for s in doc.schilder], doc.options.fett
        (['A', 'B b'], False)
    """
    meta, body, first_line = split_schild_frontmatter(text)
    schilder: list[Schild] = []
    empty_after: list[int] = []
    current: list[tuple[int, str]] = []
    separator_line: int | None = None

    def flush() -> None:
        """Schließt das laufende Stück ab und merkt leere Stücke nach `---`."""
        content = [(number, line) for number, line in current if line.strip()]
        if content:
            start, end = content[0][0], content[-1][0]
            lines = [line.strip() for number, line in current if start <= number <= end]
            schilder.append(Schild(text="\n".join(lines), line_number=start))
        elif separator_line is not None:
            empty_after.append(separator_line)

    for offset, line in enumerate(body.splitlines()):
        number = first_line + offset
        if line.strip() == SEPARATOR:
            flush()
            current, separator_line = [], number
            continue
        current.append((number, line))
    flush()
    return ParsedSchildDocument(meta, resolve_options(meta), tuple(schilder), tuple(empty_after))


def _schild_html(schild: Schild) -> str:
    """Ein Schild als `<section>`; Zeilenumbrüche werden zu `<br>`."""
    inner = "<br>".join(escape(line) for line in schild.text.split("\n"))
    return f'<section class="schild"><div class="schild-text">{inner}</div></section>'


def render_schild_html(text: str) -> str:
    """Rendert ein `.sbw`-Dokument zu einem vollständigen HTML-Dokument.

    Die Seitengeometrie steckt im CSS (eine `section` = eine A4-Seite), die
    Schriftgröße setzt erst das eingebettete Fit-Script.
    """
    parsed = parse_schild(text)
    options = parsed.options
    width, height = _PAGE_MM[options.ausrichtung]
    stylesheet = _STYLESHEET.format(
        page_orientation="portrait" if options.ausrichtung == "hoch" else "landscape",
        width=width,
        height=height,
        margin=f"{options.rand_mm:g}",
        weight="bold" if options.fett else "normal",
    )
    raw_title = parsed.meta.get("Titel")
    title = raw_title if isinstance(raw_title, str) and raw_title.strip() else "Schilder"
    sections = "\n".join(_schild_html(schild) for schild in parsed.schilder)
    script = _FIT_SCRIPT % ("true" if options.schriftgroesse == "einheitlich" else "false")
    return (
        "<!DOCTYPE html>\n<html lang=\"de\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{escape(title)}</title>\n<style>{stylesheet}</style>\n</head>\n"
        f"<body>\n{sections}\n{script}\n</body>\n</html>\n"
    )


def build_schild(input_path: str | Path, output_path: str | Path) -> Path:
    """Schreibt eine `.sbw`-Datei als HTML oder PDF (Endung von `output_path`).

    Args:
        input_path: Quelldatei (UTF-8).
        output_path: Ziel mit Endung `.html` oder `.pdf`.

    Returns:
        Den tatsächlich geschriebenen Pfad.
    """
    source_path = Path(input_path)
    html = render_schild_html(source_path.read_text(encoding="utf-8"))
    target = validate_export_output_path(output_path, allowed_suffixes={".pdf", ".html"})
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.suffix.lower() == ".html":
        target.write_text(html, encoding="utf-8")
        return target
    return Path(write_pdf_from_html(html, target))
