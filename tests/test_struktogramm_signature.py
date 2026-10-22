"""Tests für den GO-Signaturparser (`app/core/struktogramm_signature.py`)."""

import pytest

from app.core.struktogramm_signature import (
    SignatureError,
    format_signature_html,
    format_signature_text,
    parse_signature,
)
from struktogramm_go_examples import GO_SIGNATURES


@pytest.mark.parametrize("text", GO_SIGNATURES)
def test_all_go_signatures_parse_and_round_trip(text):
    """Jede Signatur der GO ist gültig und bleibt in Normalform unverändert."""
    assert format_signature_text(parse_signature(text)) == text


def test_grouped_parameters_share_the_following_type():
    """`a, b: Fließkommazahl` ist eine Gruppe mit zwei Namen."""
    signature = parse_signature("minimum(a, b: Fließkommazahl): Fließkommazahl")
    assert signature.parameter_names == ("a", "b")
    assert len(signature.groups) == 1
    assert signature.groups[0].type_name == "Fließkommazahl"


def test_without_return_type_and_without_parameters():
    """Rückgabetyp und Parameter sind beide optional."""
    assert parse_signature("sortiere(a: Reihung)").return_type is None
    assert parse_signature("erzeugePixel(): Pixel").groups == ()


def test_whitespace_is_normalized():
    """Kompakte Schreibweise wird in die GO-Normalform gebracht."""
    assert format_signature_text(parse_signature("minimum(a,b:Zahl):Zahl")) == "minimum(a, b: Zahl): Zahl"


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("istGerade x: Ganzzahl", "SG010"),
        ("f(a: Zahl) Zahl", "SG010"),
        ("f((a: Zahl))", "SG010"),
        ("(a: Zahl): Zahl", "SG011"),
        ("f(1a: Zahl)", "SG011"),
        ("f(a, : Zahl)", "SG011"),
        ("f(a, b)", "SG012"),
        ("f(a: Zahl, b)", "SG012"),
        ("f(a: ): Zahl", "SG013"),
        ("f(a: Zahl):", "SG013"),
    ],
)
def test_invalid_signatures_raise_with_code(text, code):
    """Jede Abweichung von der GO-Form liefert den passenden `SG`-Code."""
    with pytest.raises(SignatureError) as info:
        parse_signature(text)
    assert info.value.code == code
    assert "GO-Form" in str(info.value)


def test_html_breaks_only_between_parameters_and_before_return_type():
    """Klammern kleben an Name bzw. letztem Parameter; Rückgabetyp ist ein eigenes Stück."""
    html = format_signature_html(parse_signature("minimum(a, b: Zahl, c: Text): Zahl"))
    parts = html.count("class='stg-sig-part'")
    assert parts == 3
    assert ">minimum(a, b: Zahl,</span>" in html
    assert ">c: Text):</span>" in html
    assert ">Zahl</span>" in html


def test_html_escapes_text():
    """Typen mit Sonderzeichen werden HTML-escaped."""
    html = format_signature_html(parse_signature("f(a: A&B)"))
    assert "A&amp;B" in html
