"""Tests für den Kurzentwurf-Phasen-/Zeilenmarker-Katalog (`PHASE_SPECS`/`LINE_MARKER_SPECS`).

End-to-end über `inspect_kurzentwerfer_text`, nicht nur gegen Regex/Struktur --
siehe Review-Feedback: "Regex akzeptiert es" ist nicht dasselbe wie "die
komplette DSL erkennt es korrekt" (das deckte den `ant>`-Irrtum der ersten
Planfassung auf).
"""

from app.core.kurzentwurf_runtime.model import LINE_MARKER_SPECS, PHASE_SPECS
from app.core.kurzentwurf_runtime.validator import inspect_kurzentwerfer_text


def _document_with_phase(phase_header: str, body: str = "S> x\nA>\ns< y\nant< z\nU> u") -> str:
    return (
        "---\n"
        "Stundenthema: T\n"
        "Lerngruppe: X\n"
        "start: 08:00\n"
        "---\n"
        f"{phase_header}\n"
        f"{body}\n"
    )


def test_every_phase_spec_hashtag_resolves_to_its_display_name():
    for spec in PHASE_SPECS:
        header = f"#{spec.hashtag}" if spec.requires_explicit_time is False else f"#{spec.hashtag} t=10"
        result = inspect_kurzentwerfer_text(_document_with_phase(header))
        error_codes = [d.code for d in result.diagnostics if d.severity == "error"]
        assert not error_codes, f"#{spec.hashtag} sollte fehlerfrei parsen, bekam {error_codes}"
        assert result.document is not None
        assert result.document.phases[0].display_phase == spec.display_name


def test_ergebnissicherung_hashtag_is_sicherung_not_ergebnissicherung():
    """Regressionstest für den behobenen Bug: kein Bindestrich/Leerzeichen mehr im Anzeigenamen."""
    result = inspect_kurzentwerfer_text(_document_with_phase("#sicherung t=10"))
    assert result.document is not None
    assert result.document.phases[0].display_phase == "Ergebnissicherung"
    assert "Ergebnis- sicherung" not in result.document.phases[0].display_phase


def test_display_names_are_not_valid_hashtags():
    """Die alte Doku empfahl fälschlich, den Anzeigenamen selbst als Hashtag zu tippen -- muss weiterhin KZF011 auslösen."""
    for invalid_header in ("#Ergebnissicherung", "#Didaktische Reserve", "#ergebnissicherung"):
        result = inspect_kurzentwerfer_text(_document_with_phase(invalid_header))
        codes = [d.code for d in result.diagnostics]
        assert "KZF011" in codes, f"{invalid_header!r} sollte KZF011 auslösen, bekam {codes}"
        assert result.document is None


def test_optional_time_phases_do_not_require_t_attribute():
    optional_specs = [spec for spec in PHASE_SPECS if not spec.requires_explicit_time]
    assert optional_specs, "Erwartet mindestens eine zeitlose Phase"
    for spec in optional_specs:
        result = inspect_kurzentwerfer_text(_document_with_phase(f"#{spec.hashtag}"))
        codes = [d.code for d in result.diagnostics]
        assert "KZF132" not in codes
        assert "KZF130" not in codes


def _document_with_body(body: str) -> str:
    return (
        "---\n"
        "Stundenthema: T\n"
        "Lerngruppe: X\n"
        "start: 08:00\n"
        "---\n"
        "#einstieg t=10\n"
        f"{body}\n"
    )


def test_non_rejected_line_marker_specs_populate_expected_field_end_to_end():
    marker_bodies = {
        "S>": "S> schritt-inhalt\nA>\ns< aktivitaet\nant< anti\nU> umgebung",
        "A>": "S> schritt-inhalt\nA>\ns< aktivitaet\nant< anti\nU> umgebung",
        "s<": "S> schritt-inhalt\nA>\ns< aktivitaet\nant< anti\nU> umgebung",
        "U>": "S> schritt-inhalt\nA>\ns< aktivitaet\nant< anti\nU> umgebung",
        "ant<": "S> schritt-inhalt\nA>\ns< aktivitaet\nant< anti\nU> umgebung",
    }
    expected_values = {
        "schritte": "schritt-inhalt",
        "aktivitaeten": "aktivitaet",
        "umgebung": "umgebung",
        "antizipiert": "anti",
    }

    for spec in LINE_MARKER_SPECS:
        if spec.rejected:
            continue
        result = inspect_kurzentwerfer_text(_document_with_body(marker_bodies[spec.token]))
        assert result.document is not None, f"Dokument mit {spec.token} sollte fehlerfrei parsen"
        segment = result.document.phases[0].segments[0]
        actual_value = getattr(segment, spec.target_field)
        assert actual_value == expected_values[spec.target_field], (
            f"{spec.token} sollte in {spec.target_field} landen, bekam {actual_value!r}"
        )


def test_a_marker_with_inline_content_triggers_kzf150():
    result = inspect_kurzentwerfer_text(
        _document_with_body("S> x\nA> inline-inhalt-ist-ungueltig\ns< y\nant< z\nU> u")
    )
    codes = [d.code for d in result.diagnostics]
    assert "KZF150" in codes


def test_ant_gt_is_rejected_not_a_silent_alias_of_ant_lt():
    """`ant>` matcht das Marker-Regex, ist aber kein gültiger Alias -- immer KZF153."""
    rejected_specs = [spec for spec in LINE_MARKER_SPECS if spec.rejected]
    assert [spec.token for spec in rejected_specs] == ["ant>"]

    result = inspect_kurzentwerfer_text(
        _document_with_body("S> x\nA>\ns< y\nant> z\nU> u")
    )
    codes = [d.code for d in result.diagnostics]
    assert "KZF153" in codes
    assert result.document is None


def _kzf154_lines(body: str) -> list[int]:
    result = inspect_kurzentwerfer_text(_document_with_body(body))
    return [d.line for d in result.diagnostics if d.code == "KZF154"]


def test_ant_directly_after_s_in_a_block_is_not_flagged():
    assert _kzf154_lines("S> x\nA>\ns< y\nant< z\nU> u") == []
    assert _kzf154_lines("S> x\nA>\ns< y\nant< - z1\n      - z2\ns< y2\nant< z3\nU> u") == []


def test_ant_after_s_or_u_column_triggers_kzf154():
    """`ant<` gehört ausschließlich in den A>-Block, nicht hinter `S>`- oder `U>`-Inhalt."""
    assert _kzf154_lines("S> x\nA>\ns< y\nU> u\nant< z")
    assert _kzf154_lines("S> x\nA>\ns< y\n|\nant< z")
    assert _kzf154_lines("S> x\nant< z\nA>\ns< y\nU> u")


def test_ant_before_any_s_marker_triggers_kzf154():
    assert _kzf154_lines("S> x\nA>\nant< z\ns< y\nU> u")


def test_ant_after_returning_to_a_block_is_not_flagged():
    """Ein erneutes `A>` nach `U>` macht die Lernaktivitäten wieder zur aktiven Spalte."""
    assert _kzf154_lines("S> x\nA>\ns< y\nU> u\nA>\nant< z") == []


def test_kzf154_is_an_ackable_warning():
    result = inspect_kurzentwerfer_text(_document_with_body("S> x\nA>\ns< y\nU> u\nant< z"))
    diagnostics = [d for d in result.diagnostics if d.code == "KZF154"]
    assert len(diagnostics) == 1
    assert diagnostics[0].severity == "warning"
    assert diagnostics[0].region_id
    assert diagnostics[0].anchor == "ant< z"
    assert result.document is not None


def _kzf152_count(body: str) -> int:
    result = inspect_kurzentwerfer_text(_document_with_body(body))
    return len([d for d in result.diagnostics if d.code == "KZF152"])


def test_kzf152_skipped_when_u_names_only_work_forms():
    """Antizipationen sind mündliche Äußerungen im Unterrichtsgespräch -- reine Arbeitsphasen brauchen keine."""
    assert _kzf152_count("S> x\nA>\ns< y\nU> EA; Arbeitsheft S. 11") == 0
    assert _kzf152_count("S> x\nA>\ns< y\nU> arbeitsteilige PA; TI-Nspire") == 0
    assert _kzf152_count("S> x\nA>\ns< y\nU> GA, Kartensätze") == 0


def test_kzf152_kept_for_conversation_mixed_or_unknown_social_form():
    assert _kzf152_count("S> x\nA>\ns< y\nU> LSG; Tafel") == 1
    assert _kzf152_count("S> x\nA>\ns< y\nU> EA → LSG; Tafel") == 1
    assert _kzf152_count("S> x\nA>\ns< y\nU> Tafel") == 1
    assert _kzf152_count("S> x\nA>\ns< y") == 1


def test_kzf152_matches_whole_words_only():
    """"Papier" enthält "pa", ist aber keine Partnerarbeit -- die Warnung bleibt."""
    assert _kzf152_count("S> x\nA>\ns< y\nU> Papier") == 1


def test_every_social_form_spelling_is_recognized_case_insensitively():
    from app.core.kurzentwurf_runtime.dsl_segments import expects_anticipation
    from app.core.kurzentwurf_runtime.model import SOCIAL_FORM_SPECS

    for spec in SOCIAL_FORM_SPECS:
        for spelling in (spec.abbreviation, *spec.aliases):
            for variant in (spelling, spelling.upper(), spelling.lower()):
                assert expects_anticipation(f"{variant}; Tafel") is spec.conversation, (spec, variant)


def test_conversation_and_work_tokens_are_disjoint():
    from app.core.kurzentwurf_runtime.model import CONVERSATION_SOCIAL_FORM_TOKENS, WORK_SOCIAL_FORM_TOKENS

    assert CONVERSATION_SOCIAL_FORM_TOKENS
    assert WORK_SOCIAL_FORM_TOKENS
    assert not CONVERSATION_SOCIAL_FORM_TOKENS & WORK_SOCIAL_FORM_TOKENS


_SEGMENT = "S> x\nA>\ns< y\nant< z\nU> u"


def _kzf049(*phase_headers: str) -> list:
    body = "\n".join(f"{header}\n{_SEGMENT}\n" for header in phase_headers)
    result = inspect_kurzentwerfer_text(f"---\nStundenthema: T\nLerngruppe: X\nstart: 08:00\n---\n{body}")
    return [d for d in result.diagnostics if d.code == "KZF049"]


def test_reserve_as_last_phase_triggers_ackable_kzf049():
    """Die Reserve gehört chronologisch in den Verlauf, nicht pauschal ans Ende."""
    diagnostics = _kzf049("#einstieg t=10", "#vertiefung t=10", "#reserve")
    assert len(diagnostics) == 1
    assert diagnostics[0].severity == "warning"
    assert diagnostics[0].region_id
    assert diagnostics[0].anchor == "Didaktische Reserve"


def test_reserve_followed_only_by_homework_still_triggers_kzf049():
    assert len(_kzf049("#einstieg t=10", "#reserve", "#hausaufgabe")) == 1


def test_reserve_inside_the_lesson_or_absent_is_not_flagged():
    assert _kzf049("#einstieg t=10", "#reserve", "#vertiefung t=10") == []
    assert _kzf049("#einstieg t=10", "#vertiefung t=10", "#hausaufgabe") == []


def test_every_phase_placement_is_a_known_value():
    from app.core.kurzentwurf_runtime.model import (
        PHASE_PLACEMENT_AFTER_LESSON,
        PHASE_PLACEMENT_BUFFER,
        PHASE_PLACEMENT_REGULAR,
    )

    known = {PHASE_PLACEMENT_REGULAR, PHASE_PLACEMENT_BUFFER, PHASE_PLACEMENT_AFTER_LESSON}
    assert {spec.placement for spec in PHASE_SPECS} <= known
