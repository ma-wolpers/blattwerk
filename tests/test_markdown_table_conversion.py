from app.core.answer_table_content import parse_table_content_payload
from app.core.markdown_table_conversion import convert_markdown_tables_to_blocks


def _cells_as_text(cells):
    return [[cell["text"] for cell in row] for row in cells]


def _extract_block_body(new_text):
    """Extracts the YAML body between the `:::table ...` fence and `:::`."""
    fence_end = new_text.index("\n")
    closing_index = new_text.rindex(":::")
    return new_text[fence_end + 1 : closing_index]


def test_simple_table_converts_to_table_block_with_round_trippable_cells():
    doc = "| Name | Alter |\n| --- | --- |\n| Anna | 12 |\n| Ben | 13 |\n"
    result = convert_markdown_tables_to_blocks(doc)

    assert result.converted_count == 1
    assert result.skipped == []
    assert ":::table rows=2 cols=2 headers=\"Name|Alter\"" in result.new_text

    body = _extract_block_body(result.new_text)
    cells, _ = parse_table_content_payload(body)
    assert _cells_as_text(cells) == [["Anna", "12"], ["Ben", "13"]]


def test_multiple_tables_separated_by_prose_and_blocks_are_all_converted():
    doc = (
        "Text davor.\n\n"
        "| A | B |\n| --- | --- |\n| 1 | 2 |\n\n"
        ":::info\nEgal\n:::\n\n"
        "| C | D |\n| --- | --- |\n| 3 | 4 |\n"
    )
    result = convert_markdown_tables_to_blocks(doc)

    assert result.converted_count == 2
    assert result.skipped == []
    assert result.new_text.count(":::table") == 2
    assert ":::info" in result.new_text


def test_table_inside_task_block_is_left_untouched():
    doc = (
        ":::task points=2\n"
        "Hier steht auch sowas:\n"
        "| a | b |\n| --- | --- |\n| 1 | 2 |\n"
        ":::\n"
    )
    result = convert_markdown_tables_to_blocks(doc)

    assert result.converted_count == 0
    assert result.new_text == doc


def test_escaped_pipe_in_data_cell_is_unescaped_in_yaml_output():
    doc = "| A | B |\n| --- | --- |\n| x\\|y | z |\n"
    result = convert_markdown_tables_to_blocks(doc)

    body = _extract_block_body(result.new_text)
    cells, _ = parse_table_content_payload(body)
    assert _cells_as_text(cells) == [["x|y", "z"]]


def test_alignment_variants_map_to_expected_tokens_or_are_omitted():
    left_center_right = "| A | B | C |\n| --- | :---: | ---: |\n| 1 | 2 | 3 |\n"
    result = convert_markdown_tables_to_blocks(left_center_right)
    assert 'alignment="left center right"' in result.new_text

    all_default = "| A | B |\n| --- | --- |\n| 1 | 2 |\n"
    result_default = convert_markdown_tables_to_blocks(all_default)
    assert "alignment=" not in result_default.new_text


def test_header_with_pipe_comma_or_quote_is_skipped_not_corrupted():
    for doc in (
        "| A, B | C |\n| --- | --- |\n| x | y |\n",
        '| A" | C |\n| --- | --- |\n| x | y |\n',
        "| A\\|B | C |\n| --- | --- |\n| x | y |\n",
    ):
        result = convert_markdown_tables_to_blocks(doc)
        assert result.converted_count == 0
        assert result.new_text == doc
        assert len(result.skipped) == 1
        assert "headers=" in result.skipped[0]


def test_table_without_data_rows_is_skipped_not_synthesized():
    doc = "| A | B |\n| --- | --- |\n"
    result = convert_markdown_tables_to_blocks(doc)

    assert result.converted_count == 0
    assert result.new_text == doc
    assert len(result.skipped) == 1
    assert "keine Datenzeile" in result.skipped[0]


def test_document_without_any_pipe_is_returned_unchanged():
    doc = "Ganz normaler Text.\nOhne jede Tabelle.\n"
    result = convert_markdown_tables_to_blocks(doc)

    assert result.converted_count == 0
    assert result.skipped == []
    assert result.new_text == doc


def test_column_count_mismatch_is_normalized_to_delimiter_column_count():
    # Header claims 2 columns, one data row has 3 (extra dropped), another has 1 (padded).
    doc = "| A | B |\n| --- | --- |\n| 1 | 2 | 3 |\n| 4 |\n"
    result = convert_markdown_tables_to_blocks(doc)

    body = _extract_block_body(result.new_text)
    cells, _ = parse_table_content_payload(body)
    assert _cells_as_text(cells) == [["1", "2"], ["4", ""]]


def test_yaml_front_matter_is_left_untouched():
    doc = "---\nTitel: Test\n---\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n"
    result = convert_markdown_tables_to_blocks(doc)

    assert result.new_text.startswith("---\nTitel: Test\n---\n\n")
    assert result.converted_count == 1


def test_document_without_any_markdown_table_is_byte_identical():
    doc = (
        "# Ueberschrift\n\n"
        "Ein Absatz mit **fett** und *kursiv*.\n\n"
        ":::task points=1\nMach etwas.\n:::\n"
    )
    result = convert_markdown_tables_to_blocks(doc)

    assert result.new_text == doc
    assert result.converted_count == 0
    assert result.skipped == []
