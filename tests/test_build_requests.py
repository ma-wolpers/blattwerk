from pathlib import Path

from app.core.build_requests import (
    HelpCardsBuildRequest,
    WorksheetBuildRequest,
    WorksheetDesignOptions,
)


def test_design_options_as_kwargs_has_expected_keys():
    design = WorksheetDesignOptions(
        color_profile="bw",
        font_profile="segoe",
        font_size_profile="normal",
    )

    assert design.as_kwargs() == {
        "color_profile": "bw",
        "font_profile": "segoe",
        "font_size_profile": "normal",
    }


def test_worksheet_build_request_stores_typed_paths_and_design():
    request = WorksheetBuildRequest(
        input_path=Path("input.md"),
        output_path=Path("out.pdf"),
        include_solutions=True,
        page_format="a5_landscape",
        print_profile="strong",
        design=WorksheetDesignOptions("bw", "segoe", "normal"),
    )

    assert request.input_path.suffix == ".md"
    assert request.output_path.suffix == ".pdf"
    assert request.include_solutions is True
    assert request.design.color_profile == "bw"


def test_help_cards_build_request_defaults_are_stable():
    request = HelpCardsBuildRequest(
        input_path=Path("input.md"),
        output_path=Path("help.pdf"),
    )

    assert request.include_solutions is False
    assert request.page_format == "a4_portrait"
    assert request.print_profile == "standard"
    assert request.design.font_profile == "segoe"
