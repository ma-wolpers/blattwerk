from __future__ import annotations

from dataclasses import dataclass

from app.app_info import APP_INFO, AppInfo
from bw_libs.app_shell import AppShellConfig


@dataclass(frozen=True)
class AppDependencies:
    """Composition-root payload for Blattwerk GUI startup."""

    app_info: AppInfo
    shell_config: AppShellConfig


def build_gui_dependencies() -> AppDependencies:
    """Build GUI startup dependencies in one explicit composition step."""

    return AppDependencies(
        app_info=APP_INFO,
        shell_config=AppShellConfig(
            title=APP_INFO.window_title,
            geometry="980x860",
            min_width=760,
            min_height=640,
        )
    )
