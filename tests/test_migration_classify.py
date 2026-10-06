"""Klassifikationsmatrix der Migration (nur synthetische Inhalte)."""

import pytest

from app.core.migration.classify import classify

WS_HEAD = "---\nTitel: T\nFach: M\nThema: X\n"


def _c(text, name="datei.md"):
    return classify(name, text)


@pytest.mark.parametrize(
    ("text", "status", "target"),
    [
        (WS_HEAD + "---\n:::task\nA\n:::\n", "sicher", "worksheet"),
        (WS_HEAD + "mode: presentation\n---\n:::task\nA\n:::\n", "sicher", "presentation"),
        (WS_HEAD + "mode: test\n---\n:::task\nA\n:::\n", "sicher", "exam"),
        (WS_HEAD + "mode: Test\n---\n", "sicher", "exam"),
        ("---\ndocument_type: exam\n---\nText\n", "sicher", "exam"),
        ("---\ndocument_type: slide_deck\n---\n", "sicher", "presentation"),
        ("---\nStundenthema: A\nLerngruppe: 6a\n---\n", "sicher", "kurzentwurf"),
        ("---\nStundenthema: A\nDauer: 1\nMaterial: x\n---\n", "sicher", "kurzentwurf"),
        ("---\nStundenthema: A\n---\n#einstieg t=5\nS> Impuls\n", "sicher", "kurzentwurf"),
        (WS_HEAD + "mode: worksheet\n---\n:::task\nA\n:::\n", "sicher", "worksheet"),
    ],
)
def test_safe_cases(text, status, target):
    result = _c(text)
    assert (result.status, result.target_type) == (status, target)


def test_kwe_suffix_uses_whole_name():
    assert _c("Text", "stunde.kwe.md").target_type == "kurzentwurf"
    assert _c("Text", "STUNDE.KWE.MD").target_type == "kurzentwurf"
    assert _c("Text", "x.kwe.backup.md").status == "kein_blattwerk"
    assert _c("Text", "kwe.md").status == "kein_blattwerk"


@pytest.mark.parametrize(
    "text",
    [
        "---\nmode: test\nStundenthema: A\nLerngruppe: 6a\n---\n",  # test + Kurzentwurf
        "---\ndocument_type: worksheet\nmode: presentation\n---\n",  # Marker gegen mode
        "---\nStundenthema: A\nLerngruppe: 6a\nTitel: T\nFach: M\nThema: X\n---\n:::task\nA\n:::\n",  # KZ + S_WS
        "---\ndocument_type: kurzentwurf\nmode: test\n---\n",
    ],
)
def test_conflicting_strong_signals(text):
    assert _c(text).status == "conflict"


@pytest.mark.parametrize(
    ("text", "status"),
    [
        ("---\ndocument_type: markdown\n---\nText\n", "kein_blattwerk"),
        ("---\ndocument_type: markdown\n---\n:::task\nA\n:::\n", "kein_blattwerk"),
        ("---\ndocument_type: markdown\n" + WS_HEAD[4:] + "---\n:::task\nA\n:::\n", "conflict"),
        ("---\ndocument_type: markdown\nmode: test\n---\n", "conflict"),
        ("---\ndocument_type: markdown\nStundenthema: A\nLerngruppe: 6a\n---\n", "conflict"),
    ],
)
def test_markdown_declaration_matrix(text, status):
    result = _c(text)
    assert result.status == status
    assert result.target_type is None


@pytest.mark.parametrize("raw", ["banana", "3", "true", "[a]", "{a: 1}"])
def test_invalid_marker_is_never_rescued(raw):
    text = f"---\ndocument_type: {raw}\nmode: presentation\n" + WS_HEAD[4:] + "---\n:::task\nA\n:::\n"
    assert _c(text).status == "ungueltiger_marker"


@pytest.mark.parametrize(
    ("text", "status"),
    [
        ("", "kein_blattwerk"),
        ("# Nur Markdown\n\n---\n\nText -- mit Strichen\n", "kein_blattwerk"),  # kein Marker
        ("# Notizen\n\nTeil 1\n\n--\n\nTeil 2\n", "unklar"),  # eigene `--`-Zeile: schwaches Signal
        ("---\nTitel: T\n---\n", "kein_blattwerk"),
        (":::task\nA\n:::\n", "unklar"),
        ("---\nTitel: T\nFach: M\nThema: X\n---\n:::info\nA\n:::\n", "unklar"),  # mehrdeutiger Block
        ("---\ntitle: Doku\n---\n:::tip\nHinweis\n:::\n", "kein_blattwerk"),  # Docusaurus
        ("---\nkaputt: [1\n---\n:::task\n", "unklar"),
    ],
)
def test_unclear_and_plain_cases(text, status):
    assert _c(text).status == status


def test_s_ws_false_positive_guards():
    docusaurus = "---\nTitel: T\nFach: M\nThema: X\n---\n:::info\nHinweis\n:::\n"
    pandoc = "---\nTitel: T\nFach: M\nThema: X\n---\n::: columns\nA\n:::\n"
    missing_field = "---\nTitel: T\nFach: M\nThema: ''\n---\n:::task\nA\n:::\n"
    real = "---\nTitel: T\nFach: M\nThema: X\n---\n:::task\nA\n:::\n"

    assert _c(docusaurus).status != "sicher"
    assert _c(pandoc).status != "sicher"
    assert _c(missing_field).status != "sicher"
    assert _c(real).status == "sicher" and "S_WS" in _c(real).signals


def test_signals_in_code_fences_and_indented_code_do_not_count():
    fenced = "---\nStundenthema: A\n---\n```\n#einstieg t=5\nS> X\n```\n"
    indented = "---\nStundenthema: A\n---\nText\n\n    #einstieg t=5\n    S> X\n"
    tilde = "---\nTitel: T\nFach: M\nThema: X\n---\n~~~\n:::task\n~~~\n"

    assert _c(fenced).status != "sicher"
    assert _c(indented).status != "sicher"
    assert _c(tilde).status != "sicher"


def test_mode_in_body_is_not_a_signal():
    assert _c(WS_HEAD + "---\nmode: presentation\n:::task\nA\n:::\n").target_type == "worksheet"


def test_bom_and_crlf_are_supported():
    text = "﻿---\r\nTitel: T\r\nFach: M\r\nThema: X\r\nmode: presentation\r\n---\r\n:::task\r\nA\r\n:::\r\n"
    assert _c(text).target_type == "presentation"
