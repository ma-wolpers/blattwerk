"""Misst den Vorschau-Build je Stufe mit generierten Dokumenten.

Starten mit:  .venv/Scripts/python.exe tools/measure_render.py --runs 7

Alle Dokumente entstehen hier im Skript; echte Dokumente werden nie gelesen. Standard ist
ein Temp-Ordner. Mit ``--doc-dir`` lässt sich der Speicherort variieren, etwa ein
synchronisierter Ordner, weil der Rechen-Cache neben das Dokument schreibt.

Je Szenario und Variante gibt es den ersten Lauf separat sowie Median und p90 der übrigen,
je Stufe die exklusive Zeit (ohne geschachtelte Stufen) und die längste GIL-Sperre. Die
Sperre misst ein Heartbeat-Thread: Wacht er verspätet auf, konnte auch der Tk-Thread in
dieser Zeit nicht laufen.
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
import tempfile
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from app.core import blatt_kern_io_pdf, pdf_printers, print_service  # noqa: E402
from app.core.build_requests import WorksheetDesignOptions  # noqa: E402
from app.core.document_preview_build import build_preview_images_for_document  # noqa: E402
from app.core.document_semantics import type_for_path  # noqa: E402
from app.core.help_cards_appendix import HELP_APPENDIX_NONE, HELP_APPENDIX_SHEET  # noqa: E402
from app.core.render_job import RenderObserver, run_observed  # noqa: E402

HEAD = "---\nTitel: Messung\nFach: Mathematik\nThema: Synthetisch\n---\n"
HEARTBEAT_SECONDS = 0.005
_PRE_STAGE = "(ausserhalb)"


def _tasks(count: int, body: str, *, page_breaks: bool = True) -> str:
    """Erzeugt ``count`` Aufgabenblöcke, auf Wunsch je Block eine eigene Seite."""
    separator = "--!\n" if page_breaks else ""
    return separator.join(f":::task\n{body}\n:::\n" for _ in range(count))


CROSSWORD = (
    ":::crossword maxw=15 maxh=15\nwords:\n"
    '  - word: "SONNE"\n    clue: "Scheint tagsueber"\n'
    '  - word: "MOND"\n    clue: "Scheint nachts"\n'
    '  - word: "STERN"\n    clue: "Funkelt nachts"\n'
    '  - word: "TAFEL"\n    clue: "Haengt an der Wand"\n:::\n'
)
KURZENTWURF = (
    "---\nStundenthema: Messung\nLerngruppe: X\nstart: 08:00\n---\n"
    "#einstieg t=10\nS> x\nA>\ns< y\nant< z\nU> u\n"
)


@dataclass(frozen=True)
class Scenario:
    """Ein generiertes Messdokument.

    Attributes:
        name: Name in der Ergebnistabelle.
        suffix: Dateiendung, bestimmt den Dokumenttyp.
        text: Dokumenttext.
        font_profile: Schriftprofil des Laufs.
        help_appendix: Lernhilfen-Anhang des Laufs.
        with_image: Legt `bild.png` neben dem Dokument an.
        page_format: Seitenformat des Laufs.
    """

    name: str
    suffix: str
    text: str
    font_profile: str = "segoe"
    help_appendix: str = HELP_APPENDIX_NONE
    with_image: bool = False
    page_format: str = "a4_portrait"


SCENARIOS = (
    Scenario("ohne_mathe_1s", ".abw", HEAD + _tasks(1, "Nenne zwei Beispiele.")),
    Scenario("ohne_mathe_5s", ".abw", HEAD + _tasks(5, "Nenne zwei Beispiele.")),
    Scenario("ohne_mathe_20s", ".abw", HEAD + _tasks(20, "Nenne zwei Beispiele.")),
    Scenario("mathe_1s", ".abw", HEAD + _tasks(1, "Berechne $x^2 + \\frac{1}{2}$.")),
    Scenario("mathe_5s", ".abw", HEAD + _tasks(5, "Berechne $x^2 + \\frac{1}{2}$.")),
    Scenario("operatoren", ".abw", HEAD + ":::task\n!!Nenne!! zwei Beispiele.\n:::\n:::operators:::\n"),
    Scenario("andika_5s", ".abw", HEAD + _tasks(5, "Nenne zwei Beispiele."), font_profile="andika"),
    Scenario("praesentation_5f", ".pbw", HEAD + _tasks(5, "Ein Punkt."), page_format="presentation_16_9"),
    Scenario("kreuzwort", ".abw", HEAD + CROSSWORD),
    Scenario("kurzentwurf", ".ebw", KURZENTWURF),
    Scenario("bild", ".abw", HEAD + ":::task\n![Bild](bild.png)\n:::\n", with_image=True),
    Scenario(
        "anhang",
        ".abw",
        HEAD + ':::task\nAufgabe\n:::\n:::help title="Tipp"\nDenk nach.\n:::\n',
        help_appendix=HELP_APPENDIX_SHEET,
    ),
)


@dataclass(frozen=True)
class Variant:
    """Abwandlung des Chromium-Aufrufs.

    Attributes:
        name: Name in der Ergebnistabelle.
        budget_ms: Wert für ``--virtual-time-budget``; None lässt ihn unverändert.
        offline: Sperrt die Namensauflösung, der CDN-Abruf scheitert also.
        command_line: Druckt über `CommandLinePrinter` statt über den Dauerbrowser.
    """

    name: str
    budget_ms: int | None = None
    offline: bool = False
    command_line: bool = False


@dataclass
class StageTimer(RenderObserver):
    """Beobachter: sammelt exklusive Zeiten und die längste GIL-Sperre je Stufe."""

    times: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    max_gap: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    _stack: list[str] = field(default_factory=list)
    _last: float = 0.0

    def _account(self) -> None:
        """Schreibt die seit der letzten Meldung vergangene Zeit der innersten Stufe zu."""
        now = time.perf_counter()
        if self._stack:
            self.times[self._stack[-1]] += now - self._last
        self._last = now

    def stage_entered(self, key: str) -> None:
        """Beginnt eine Stufe; die äußere pausiert."""
        self._account()
        self._stack.append(key)

    def stage_left(self, key: str) -> None:
        """Beendet die Stufe; die äußere läuft weiter."""
        self._account()
        self._stack.pop()

    def current(self) -> str:
        """Die gerade aktive Stufe, für den Heartbeat."""
        return self._stack[-1] if self._stack else _PRE_STAGE


class Heartbeat:
    """Thread, der die längste Lücke zwischen seinen Wachzeiten je Stufe festhält."""

    def __init__(self, timer: StageTimer) -> None:
        self._timer = timer
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="measure-heartbeat")

    def _run(self) -> None:
        last = time.perf_counter()
        while not self._stop.is_set():
            time.sleep(HEARTBEAT_SECONDS)
            now = time.perf_counter()
            key = self._timer.current()
            self._timer.max_gap[key] = max(self._timer.max_gap[key], now - last - HEARTBEAT_SECONDS)
            last = now

    def __enter__(self) -> "Heartbeat":
        self._thread.start()
        return self

    def __exit__(self, *_exc) -> None:
        self._stop.set()
        self._thread.join()


def _patch_chromium(variant: Variant):
    """Wandelt Startschalter, Budget und Druckweg ab und liefert die Funktion zum Zurücksetzen.

    Jede Variante bekommt einen eigenen Druckdienst, denn ein laufender Dauerbrowser behält
    die Schalter, mit denen er gestartet wurde.
    """
    original_flags = pdf_printers.browser_flags
    original_budget = pdf_printers.VIRTUAL_TIME_BUDGET_MS

    def flags(profile_dir):
        parts = original_flags(profile_dir)
        return [*parts, "--host-resolver-rules=MAP * ~NOTFOUND"] if variant.offline else parts

    pdf_printers.browser_flags = flags
    if variant.budget_ms is not None:
        pdf_printers.VIRTUAL_TIME_BUDGET_MS = variant.budget_ms
    browser = blatt_kern_io_pdf.find_chromium_executable()
    previous = print_service.replace_default_print_service(
        print_service.PrintService(browser, fast_available=False if variant.command_line else None)
    )

    def restore():
        print_service.shutdown_default_print_service()
        print_service.replace_default_print_service(previous)
        pdf_printers.browser_flags = original_flags
        pdf_printers.VIRTUAL_TIME_BUDGET_MS = original_budget

    return restore


def _build_once(path: Path, scenario: Scenario) -> tuple[float, StageTimer, list[Image.Image]]:
    """Baut ein Dokument einmal und liefert Gesamtzeit, Stufenzeiten und Seiten."""
    timer = StageTimer()
    design = WorksheetDesignOptions("indigo", scenario.font_profile, "normal")

    def work():
        return build_preview_images_for_document(
            path,
            document_type=type_for_path(path),
            include_solutions=False,
            page_format=scenario.page_format,
            contrast_profile="standard",
            worksheet_design=design,
            help_appendix=scenario.help_appendix,
        )

    timer.stage_entered(_PRE_STAGE)
    started = time.perf_counter()
    with Heartbeat(timer):
        pages, _diagnostics = run_observed(work, timer)
    total = time.perf_counter() - started
    timer.stage_left(_PRE_STAGE)
    return total, timer, pages


def _percentile(values: list[float], fraction: float) -> float:
    """Einfaches Perzentil durch Rangwahl; bei wenigen Läufen genügt das."""
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))]


def _measure_blank_print(variant: Variant, runs: int) -> list[float]:
    """Misst den reinen Prozessstart: Druck einer leeren Seite ohne Skripte."""
    durations = []
    with tempfile.TemporaryDirectory(prefix="blattwerk-measure-blank-") as temp_dir:
        for index in range(runs):
            started = time.perf_counter()
            blatt_kern_io_pdf.write_pdf_from_html("<!doctype html><p>x</p>", Path(temp_dir) / f"{index}.pdf")
            durations.append(time.perf_counter() - started)
    return durations


def _measure_scaling(pages: list[Image.Image]) -> float:
    """Misst das Skalieren der ersten Seite wie in der Anzeige (LANCZOS auf 900 px Breite)."""
    if not pages:
        return 0.0
    first = pages[0]
    started = time.perf_counter()
    first.resize((900, max(1, int(first.height * 900 / first.width))), Image.LANCZOS)
    return time.perf_counter() - started


def _measure_variant(variant: Variant, scenarios, runs: int, doc_dir: Path) -> None:
    """Misst alle Szenarien einer Variante in gemischter Reihenfolge und druckt die Tabellen."""
    restore = _patch_chromium(variant)
    try:
        blank = _measure_blank_print(variant, runs)
        print(f"\n## Variante: {variant.name}\n")
        print(f"Leere Seite (erster Lauf mit Browserstart: {blank[0]:.2f} s): Median {statistics.median(blank):.2f} s, p90 {_percentile(blank, 0.9):.2f} s\n")

        results: dict[str, list] = defaultdict(list)
        schedule = [scenario for scenario in scenarios for _ in range(runs)]
        random.shuffle(schedule)
        for scenario in schedule:
            path = doc_dir / f"mess_{scenario.name}{scenario.suffix}"
            path.write_text(scenario.text, encoding="utf-8")
            if scenario.with_image:
                Image.new("RGB", (1200, 900), "steelblue").save(doc_dir / "bild.png")
            results[scenario.name].append(_build_once(path, scenario))

        print("| Szenario | Seiten | erster Lauf | Median | p90 | Skalieren | Stufen (Median, s) | längste GIL-Sperre |")
        print("|---|---|---|---|---|---|---|---|")
        for scenario in scenarios:
            _print_row(scenario, results[scenario.name])
    finally:
        restore()


def _print_row(scenario: Scenario, runs) -> None:
    """Druckt eine Tabellenzeile für ein Szenario."""
    first_total, _first_timer, pages = runs[0]
    rest = runs[1:] or runs
    totals = [run[0] for run in rest]
    keys = sorted({key for run in rest for key in run[1].times})
    stages = ", ".join(f"{key} {statistics.median(run[1].times.get(key, 0.0) for run in rest):.2f}" for key in keys)
    gaps = {key: max(run[1].max_gap.get(key, 0.0) for run in rest) for key in keys}
    worst = max(gaps, key=gaps.get) if gaps else "-"
    worst_text = f"{gaps[worst] * 1000:.0f} ms ({worst})" if gaps else "-"
    print(
        f"| {scenario.name} | {len(pages)} | {first_total:.2f} | {statistics.median(totals):.2f} "
        f"| {_percentile(totals, 0.9):.2f} | {_measure_scaling(pages) * 1000:.0f} ms | {stages} | {worst_text} |"
    )


def main() -> None:
    """Liest die Argumente und führt die Messung aus."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=7, help="Läufe je Szenario und Variante")
    parser.add_argument("--doc-dir", type=Path, default=None, help="Ordner für die generierten Dokumente")
    parser.add_argument("--only", nargs="*", default=None, help="Nur diese Szenarien")
    parser.add_argument("--matrix", action="store_true", help="Auch Budget-, Offline- und Profil-Varianten")
    args = parser.parse_args()

    scenarios = [s for s in SCENARIOS if not args.only or s.name in args.only]
    with tempfile.TemporaryDirectory(prefix="blattwerk-measure-") as temp_dir:
        doc_dir = args.doc_dir or Path(temp_dir) / "docs"
        doc_dir.mkdir(parents=True, exist_ok=True)
        variants = [Variant("heute")]
        if args.matrix:
            variants += [
                # Budget 0 ist keine Variante: Chromium hängt damit bis in den Timeout.
                Variant("budget_1000", budget_ms=1000),
                Variant("offline", offline=True),
                Variant("kommandozeile", command_line=True),
            ]
        for variant in variants:
            _measure_variant(variant, scenarios, args.runs, doc_dir)


if __name__ == "__main__":
    main()
