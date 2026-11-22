"""Tests für die Silbentrennung im Druck (`print_hyphenation`, `hyphenation_adapter`)."""

from __future__ import annotations

import re

import pytest

from app.core.hyphenation_adapter import PYPHEN_AVAILABLE, SOFT_HYPHEN, hyphenator_for
from app.core.print_hyphenation import MARK_ATTRIBUTE, MARK_CLASS, hyphenate_html

pytestmark = pytest.mark.skipif(not PYPHEN_AVAILABLE, reason="pyphen nicht installiert")

_MARK_RE = re.compile(rf'<span class="{MARK_CLASS}" {MARK_ATTRIBUTE}="([^"]*)">([^<]*)</span>')


def _page(body: str, lang: str = "de", head: str = "") -> str:
    """Baut eine minimale Seite wie die HTML-Erzeuger."""
    return f'<!DOCTYPE html><html lang="{lang}"><head>{head}</head><body>{body}</body></html>'


def _marks(html: str) -> dict[str, str]:
    """Vorgemerkte Wörter: sichtbares Wort -> Fassung mit Trennstellen."""
    return {word: hyphenated for hyphenated, word in _MARK_RE.findall(html)}


def _without_marks(html: str) -> str:
    """Seite ohne Vormerkungen und Skript (so sieht man, dass sonst nichts geändert ist)."""
    html = _MARK_RE.sub(lambda match: match.group(2), html)
    return re.sub(r"<script>.*?</script>", "", html, flags=re.S)


def test_long_word_is_marked_with_hyphen_points_but_text_stays_clean():
    """Das Wort bleibt im Text sauber; die Trennstellen stehen nur im Attribut."""
    page = _page("<td>Stellenwerttafel mit Heft</td>")
    result = hyphenate_html(page)
    assert _marks(result) == {"Stellenwerttafel": SOFT_HYPHEN.join(["Stel", "len", "wert", "ta", "fel"])}
    assert SOFT_HYPHEN not in _MARK_RE.sub("", result)
    assert _without_marks(result) == page


def test_script_is_appended_before_body_end_only_when_something_is_marked():
    """Das Trennskript steht vor `</body>`, ohne trennbares Wort fehlt es."""
    result = hyphenate_html(_page("<p>Stellenwerttafel</p>"))
    assert result.index("<script>") < result.rindex("</body>")
    short = _page("<p>Tafel und Heft</p>")
    assert hyphenate_html(short) == short


def test_head_attributes_and_comments_stay_untouched():
    """Titel, Attribute und Kommentare ändern sich nie."""
    page = _page(
        '<p title="Stellenwerttafel"><!-- Stellenwerttafel -->Text</p>',
        head="<title>Stellenwerttafel</title>",
    )
    assert hyphenate_html(page) == page


@pytest.mark.parametrize(
    "body",
    [
        "<code>Stellenwerttafel</code>",
        "<pre>Stellenwerttafel</pre>",
        "<script>var Stellenwerttafel = 1;</script>",
        "<svg><foreignObject><div>Stellenwerttafel</div></foreignObject></svg>",
        r"<p>$\text{Stellenwerttafel}$ und $$\mathrm{Hundertstel}$$</p>",
    ],
)
def test_code_scripts_diagrams_and_formulas_stay_untouched(body):
    """Code, Skripte, SVG-Diagramme und Formeln werden nie vorgemerkt."""
    page = _page(body)
    assert hyphenate_html(page) == page


def test_entities_and_addresses_stay_untouched():
    """Entitäten und Internet-/Mailadressen werden nicht vorgemerkt."""
    page = _page("<p>&hellip;&laquo; https://beispielschule.de/stellenwerttafel lehrkraft@beispielschule.de</p>")
    assert hyphenate_html(page) == page


def test_portuguese_page_uses_portuguese_dictionary():
    """`pt-BR` trennt nach dem portugiesischen Wörterbuch."""
    marks = _marks(hyphenate_html(_page("<p>representação</p>", lang="pt-BR")))
    assert marks == {"representação": SOFT_HYPHEN.join(["re", "pre", "sen", "ta", "ção"])}


def test_unknown_language_or_missing_lang_stays_untouched():
    """Ohne Wörterbuch oder ohne `lang` bleibt die Seite gleich."""
    unknown = _page("<p>Stellenwerttafel</p>", lang="xx")
    assert hyphenate_html(unknown) == unknown
    no_lang = "<html><body><p>Stellenwerttafel</p></body></html>"
    assert hyphenate_html(no_lang) == no_lang


def test_second_pass_changes_nothing():
    """Zweimal angewandt ergibt dasselbe wie einmal (keine doppelte Vormerkung, ein Skript)."""
    once = hyphenate_html(_page("<p>Stellenwerttafel Unterstützung Zahlenstrahle</p>"))
    assert hyphenate_html(once) == once
    assert once.count("<script>") == 1


def test_hyphenator_for_unknown_language_is_none():
    """Der Adapter liefert für unbekannte Sprachen keinen Trenner."""
    assert hyphenator_for("xx") is None
    assert hyphenator_for("de") is not None


def test_pdf_hyphenates_only_words_that_do_not_fit(tmp_path):
    """Ende-zu-Ende: Nur das Wort in der schmalen Spalte wird getrennt, die Textebene bleibt sonst sauber."""
    fitz = pytest.importorskip("fitz")
    from app.core.blatt_kern_io_pdf import find_chromium_executable, write_pdf_from_html

    if find_chromium_executable() is None:
        pytest.skip("kein Chromium-Browser fuer den PDF-Druck")
    page = _page(
        '<table style="width:12cm;table-layout:fixed;border-collapse:collapse;font:12pt Arial">'
        '<col style="width:1.6cm"><col>'
        '<tr><td style="overflow-wrap:anywhere">Stellenwerttafel</td>'
        "<td>Zahlenstrahle passen hier bequem in eine Zeile</td></tr></table>"
    )
    out = tmp_path / "trennung.pdf"
    write_pdf_from_html(page, out)
    with fitz.open(out) as doc:
        text = "".join(pdf_page.get_text() for pdf_page in doc)
        found = sum(len(pdf_page.search_for("Zahlenstrahle")) for pdf_page in doc)
    assert found == 1, "breite Spalte: Wort muss ungetrennt und suchbar bleiben"
    narrow = text.split("Zahlenstrahle")[0]
    assert "Stellenwerttafel" not in narrow, "schmale Spalte: Wort muss getrennt sein"
    assert narrow.replace(SOFT_HYPHEN, "").replace("-", "").replace("\n", "").strip() == "Stellenwerttafel"
