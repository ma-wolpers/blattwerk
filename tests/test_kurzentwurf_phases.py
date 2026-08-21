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
