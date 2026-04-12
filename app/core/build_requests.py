"""Typed request objects for worksheet/help-card build flows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .blatt_kern_io_build import build_help_cards, build_worksheet


@dataclass(frozen=True)
class WorksheetDesignOptions:
    """Normalized design profile set passed from UI to build flows."""

    color_profile: str
    font_profile: str
    font_size_profile: str

    def as_kwargs(self):
        return {
            "color_profile": self.color_profile,
            "font_profile": self.font_profile,
            "font_size_profile": self.font_size_profile,
        }


@dataclass(frozen=True)
class WorksheetBuildRequest:
    """Typed request for worksheet build/export operations."""

    input_path: Path
    output_path: Path
    include_solutions: bool = False
    page_format: str = "a4_portrait"
    print_profile: str = "standard"
    design: WorksheetDesignOptions = WorksheetDesignOptions(
        color_profile="indigo",
        font_profile="segoe",
        font_size_profile="normal",
    )


@dataclass(frozen=True)
class HelpCardsBuildRequest:
    """Typed request for help-cards build/export operations."""

    input_path: Path
    output_path: Path
    include_solutions: bool = False
    page_format: str = "a4_portrait"
    print_profile: str = "standard"
    design: WorksheetDesignOptions = WorksheetDesignOptions(
        color_profile="indigo",
        font_profile="segoe",
        font_size_profile="normal",
    )


def build_worksheet_from_request(request: WorksheetBuildRequest):
    """Execute worksheet build from a typed request object."""

    return build_worksheet(
        str(request.input_path),
        str(request.output_path),
        include_solutions=request.include_solutions,
        page_format=request.page_format,
        print_profile=request.print_profile,
        **request.design.as_kwargs(),
    )


def build_help_cards_from_request(request: HelpCardsBuildRequest):
    """Execute help-cards build from a typed request object."""

    return build_help_cards(
        str(request.input_path),
        str(request.output_path),
        include_solutions=request.include_solutions,
        page_format=request.page_format,
        print_profile=request.print_profile,
        **request.design.as_kwargs(),
    )
