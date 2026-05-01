from app.core.blatt_kern_shared import build_block_index_line_map, parse_blocks


def test_block_index_line_map_matches_parse_blocks_order_for_mixed_content():
    text = (
        "Einleitung\n"
        "\n"
        ":::task points=2\n"
        "A\n"
        ":::\n"
        "\n"
        ":::space::: \n"
        "Zwischentext\n"
        ":::solution\n"
        "L\n"
        ":::\n"
    )

    blocks = parse_blocks(text)
    index_to_line = build_block_index_line_map(text)

    assert len(index_to_line) == len(blocks)
    assert [block[0] for block in blocks] == [
        "raw",
        "task",
        "raw",
        "space",
        "raw",
        "solution",
    ]

    assert index_to_line[0] == 1
    assert index_to_line[1] == 3
    assert index_to_line[2] == 6
    assert index_to_line[3] == 7
    assert index_to_line[4] == 8
    assert index_to_line[5] == 9


def test_block_index_line_map_tracks_inline_control_markers():
    text = (
        "Einleitung\n"
        "--# Start\n"
        "-+\n"
        "--!\n"
        "-=2.4cm\n"
        "Text\n"
    )

    blocks = parse_blocks(text)
    index_to_line = build_block_index_line_map(text)

    assert [block[0] for block in blocks] == [
        "raw",
        "sectionmark",
        "framebreak",
        "pagebreak",
        "vspacer",
        "raw",
    ]
    assert index_to_line[0] == 1
    assert index_to_line[1] == 2
    assert index_to_line[2] == 3
    assert index_to_line[3] == 4
    assert index_to_line[4] == 5
    assert index_to_line[5] == 6
