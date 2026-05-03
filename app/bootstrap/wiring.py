from __future__ import annotations

from dataclasses import dataclass

from bw_libs.app_shell import AppShellConfig


@dataclass(frozen=True)
class AppDependencies:
    """Composition-root payload for Blattwerk GUI startup."""

    shell_config: AppShellConfig


def build_gui_dependencies() -> AppDependencies:
    """Build GUI startup dependencies in one explicit composition step."""

    return AppDependencies(
        shell_config=AppShellConfig(
            title="Blattwerk",
            geometry="980x860",
            min_width=760,
            min_height=640,
        )
    )
