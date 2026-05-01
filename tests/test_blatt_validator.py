from app.core.blatt_validator import inspect_markdown_text


def _build_document(answer_block):
    return (
        "---\n"
        "Titel: T\n"
        "Fach: M\n"
        "Thema: X\n"
        "---\n"
        f"{answer_block}\n"
    )


def _build_document_with_mode(mode_value, block_content="Ein Block"):
    return (
        "---\n"
        "Titel: T\n"
        "Fach: M\n"
        "Thema: X\n"
        f"mode: {mode_value}\n"
        "---\n"
        f"{block_content}\n"
    )


def test_empty_answer_block_emits_an005_warning():
    text = _build_document(":::lines\n\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN005" in codes


def test_conflicting_line_markers_emit_an006_warning():
    text = _build_document(":::lines\n%{Start\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN006" in codes


def test_conflicting_legacy_start_and_end_markers_emit_an006_warning():
    text = _build_document(":::lines\n§ Start %\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN006" in codes


def test_non_empty_answer_without_marker_conflict_has_no_new_warnings():
    text = _build_document(":::lines\n&{Impuls}\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN005" not in codes
    assert "AN006" not in codes


def test_task_with_worksheet_marker_without_solution_emits_an010_warning():
    text = _build_document(":::task\n§ Nur Arbeitsblatt\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN010" in codes


def test_task_with_matching_solution_marker_has_no_an010_warning():
    text = _build_document(":::task\n§ Nur Arbeitsblatt\n% Musterloesung\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN010" not in codes


def test_answer_block_with_worksheet_marker_without_solution_emits_an010_warning():
    text = _build_document(":::lines\n§ Nur Arbeitsblatt\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN010" in codes


def test_answer_block_with_matching_solution_marker_has_no_an010_warning():
    text = _build_document(":::lines\n§ Nur Arbeitsblatt\n% Musterloesung\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN010" not in codes


def test_matching_new_options_are_allowed_without_op001():
    text = _build_document(
        ":::matching height_mode=uniform align=center scale=0.4cm "
        "show_guides=false lane_align=center\n"
        "left:\n"
        "  - A\n"
        "right:\n"
        "  - B\n"
        "worksheet_matches:\n"
        "  - '1-1'\n"
        "matches:\n"
        "  - '1-1'\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP001" not in codes


def test_table_alignment_option_is_allowed_without_op001():
    text = _build_document(
        ":::table rows=2 cols=2 alignment=center\n"
        "cells:\n"
        "  - ['A', 'B']\n"
        "  - ['C', 'D']\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP001" not in codes


def test_table_header_columns_option_is_allowed_without_op001():
    text = _build_document(
        ":::table rows=2 cols=2 header_columns=1\n"
        "cells:\n"
        "  - ['A', 'B']\n"
        "  - ['C', 'D']\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP001" not in codes


def test_lines_height_option_is_allowed_without_op001():
    text = _build_document(":::lines rows=2 height=2.2em\nHinweis\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP001" not in codes


def test_task_title_option_is_allowed_without_op001():
    text = _build_document(":::task title='Titel hier'\nRechne aus.\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "OP001" not in codes


def test_matching_with_single_item_side_emits_ma001_warning():
    text = _build_document(
        ":::matching\n"
        "left:\n"
        "  - Nur eins\n"
        "right:\n"
        "  - A\n"
        "  - B\n"
        "matches:\n"
        "  - '1-1'\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "MA001" in codes


def test_geometry_yaml_marker_show_values_are_accepted():
    text = _build_document(
        ":::geometry rows=4 cols=4\n"
        "points:\n"
        "  - {col: 1, row: 1, show: '§'}\n"
        "sequence:\n"
        "  - {x: 0, y: 0, show: '&'}\n"
        "functions:\n"
        "  - {expr: 'x', domain: '-1:1', show: '%'}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN007" not in codes


def test_geometry_yaml_legacy_show_values_emit_an007_error():
    text = _build_document(
        ":::geometry rows=4 cols=4\n"
        "points:\n"
        "  - {col: 1, row: 1, show: 'both'}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an007 = [d for d in inspected.diagnostics if d.code == "AN007"]
    assert an007
    assert an007[0].severity == "error"


def test_grid_plain_marker_text_does_not_emit_an004():
    text = _build_document(":::grid rows=2\n§\n% Muster\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN004" not in codes


def test_geometry_scalar_content_emits_an004():
    text = _build_document(":::geometry rows=2\nNur Text\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN004" in codes


def test_geometry_list_root_emits_an004():
    text = _build_document(":::geometry rows=2\n- 1\n- 2\n:::")
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN004" in codes


def test_numberline_yaml_marker_show_values_are_accepted():
    text = _build_document(
        ":::numberline min=-3 max=3\n"
        "labels:\n"
        "  - {value: -2, show: '§'}\n"
        "answers:\n"
        "  - {value: 0, show: '&'}\n"
        "arcs:\n"
        "  - {from: -2, to: 0, show: '%'}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    codes = {diagnostic.code for diagnostic in inspected.diagnostics}
    assert "AN007" not in codes


def test_numberline_yaml_legacy_show_values_emit_an007_error():
    text = _build_document(
        ":::numberline min=-3 max=3\n"
        "labels:\n"
        "  - {value: -1, show: 'both'}\n"
        ":::"
    )
    inspected = inspect_markdown_text(text)
    an007 = [d for d in inspected.diagnostics if d.code == "AN007"]
    assert an007
    assert an007[0].severity == "error"


def test_frontmatter_mode_ws_and_test_are_accepted():
    ws_doc = _build_document_with_mode("ws")
    test_doc = _build_document_with_mode("test")
    worksheet_doc = _build_document_with_mode("worksheet")
    solution_doc = _build_document_with_mode("solution")
    presentation_doc = _build_document_with_mode("presentation")

    ws_codes = {d.code for d in inspect_markdown_text(ws_doc).diagnostics}
    test_codes = {d.code for d in inspect_markdown_text(test_doc).diagnostics}
    worksheet_codes = {d.code for d in inspect_markdown_text(worksheet_doc).diagnostics}
    solution_codes = {d.code for d in inspect_markdown_text(solution_doc).diagnostics}
    presentation_codes = {d.code for d in inspect_markdown_text(presentation_doc).diagnostics}

    assert "FM002" not in ws_codes
    assert "FM002" not in test_codes
    assert "FM002" not in worksheet_codes
    assert "FM002" not in solution_codes
    assert "FM002" not in presentation_codes


def test_frontmatter_invalid_mode_emits_fm002():
    doc = _build_document_with_mode("foobar")
    diagnostics = inspect_markdown_text(doc).diagnostics

    fm002 = [d for d in diagnostics if d.code == "FM002"]
    assert fm002


def test_absolute_markdown_image_path_emits_pt001():
    text = _build_document(
        ":::task\n"
        "![Abb](A:/7thCloud/7thVault/ZZ Assets/plot.png)\n"
        ":::"
    )
    diagnostics = inspect_markdown_text(text).diagnostics

    pt001 = [d for d in diagnostics if d.code == "PT001"]
    assert pt001


def test_relative_markdown_image_path_has_no_pt001():
    text = _build_document(
        ":::task\n"
        "![Abb](ZZ Assets/plot.png)\n"
        ":::"
    )
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}
    assert "PT001" not in codes


def test_space_after_block_marker_emits_bl002_error():
    text = _build_document("::: lines\nInhalt\n:::")
    inspected = inspect_markdown_text(text)
    bl002 = [d for d in inspected.diagnostics if d.code == "BL002"]
    assert bl002
    assert bl002[0].severity == "error"


def test_orphan_closing_marker_emits_bl003_error():
    text = _build_document("Text vorab\n:::\nText danach")
    inspected = inspect_markdown_text(text)
    bl003 = [d for d in inspected.diagnostics if d.code == "BL003"]
    assert bl003
    assert bl003[0].severity == "error"


def test_regular_open_and_close_marker_do_not_emit_bl003():
    text = _build_document(":::task\nInhalt\n:::")
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}
    assert "BL003" not in codes


def test_orphan_closing_marker_line_number_includes_frontmatter():
    text = _build_document(":::\n")
    inspected = inspect_markdown_text(text)
    bl003 = [d for d in inspected.diagnostics if d.code == "BL003"]
    assert bl003
    assert bl003[0].line_number == 6
    assert "Zeile 6" in bl003[0].message


def test_nested_block_open_inside_open_block_emits_bl004_error():
    text = _build_document(
        ":::material\n"
        "Einleitung\n"
        ":::table rows=2 cols=2\n"
        "cells:\n"
        "  - ['A', 'B']\n"
        "  - ['C', 'D']\n"
        ":::\n"
        ":::\n"
    )
    diagnostics = inspect_markdown_text(text).diagnostics
    bl004 = [d for d in diagnostics if d.code == "BL004"]
    bl003 = [d for d in diagnostics if d.code == "BL003"]

    assert bl004
    assert bl004[0].severity == "error"
    assert bl003


def test_self_closing_block_inside_open_block_emits_bl004_error():
    text = _build_document(":::task\n:::space:::\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    bl004 = [d for d in diagnostics if d.code == "BL004"]
    assert bl004
    assert bl004[0].severity == "error"


def test_subtask_after_unclosed_task_gets_follow_block_hint():
    text = _build_document(":::task\nAufgabe\n:::subtask\nTeilaufgabe\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    bl004 = [d for d in diagnostics if d.code == "BL004"]

    assert bl004
    assert bl004[0].severity == "error"
    assert "Folgeblock" in bl004[0].message
    assert "zuerst `task` mit `:::` schliessen" in bl004[0].message


def test_section_break_triple_dash_inside_open_block_is_allowed_as_markdown_hr():
    text = _build_document(":::task\nInhalt\n---\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    bl005 = [d for d in diagnostics if d.code == "BL005"]

    assert not bl005


def test_section_break_double_dash_inside_open_block_emits_bl005_error():
    text = _build_document(":::task\nInhalt\n--\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    bl005 = [d for d in diagnostics if d.code == "BL005"]

    assert bl005
    assert bl005[0].severity == "error"


def test_legacy_answer_block_emits_an008_error():
    text = _build_document(":::answer type=lines\nText\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}
    assert "AN008" in codes


def test_type_option_is_forbidden_on_dedicated_answer_blocks():
    text = _build_document(":::grid type=grid rows=3 cols=3\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}
    assert "AN009" in codes


def test_help_key_option_is_now_rejected_with_op001():
    text = _build_document(":::help key=A1\nHinweis\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}

    assert "OP001" in codes


def test_help_tag_option_is_allowed_without_op001():
    text = _build_document(":::help tag=LOKAL\nHinweis\n:::")
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}

    assert "OP001" not in codes


def test_frontmatter_tag_accepts_simple_text_values():
    text = (
        "---\n"
        "Titel: T\n"
        "Fach: M\n"
        "Thema: X\n"
        "tag: A1\n"
        "---\n"
        ":::help\nHinweis\n:::\n"
    )
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}

    assert "FM003" not in codes


def test_frontmatter_tag_rejects_empty_value_with_fm003():
    text = (
        "---\n"
        "Titel: T\n"
        "Fach: M\n"
        "Thema: X\n"
        "tag: \"\"\n"
        "---\n"
        ":::help\nHinweis\n:::\n"
    )
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}

    assert "FM003" in codes


def test_frontmatter_tag_rejects_non_scalar_value_with_fm003():
    text = (
        "---\n"
        "Titel: T\n"
        "Fach: M\n"
        "Thema: X\n"
        "tag:\n"
        "  nested: value\n"
        "---\n"
        ":::help\nHinweis\n:::\n"
    )
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}

    assert "FM003" in codes
