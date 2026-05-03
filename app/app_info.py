from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppInfo:
    """Canonical identity metadata for the application."""

    name: str
    version: str
    appdata_folder: str
    window_title: str


APP_INFO = AppInfo(
    name="Blattwerk",
    version="0.4.1",
    appdata_folder="blattwerk",
    window_title="Blattwerk",
)
