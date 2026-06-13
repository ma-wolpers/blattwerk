from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

CHROMIUM_COMMAND_CANDIDATES = ("msedge", "chrome", "chromium", "brave")
CHROMIUM_PATH_CANDIDATES = (
    Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
    Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
    Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
)


def find_chromium_executable() -> str | None:
    """Find a chromium-based browser for headless PDF generation."""

    for command in CHROMIUM_COMMAND_CANDIDATES:
        resolved = shutil.which(command)
        if resolved:
            return resolved
    for candidate in CHROMIUM_PATH_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    return None


def write_pdf_from_html(html: str, output_path: Path) -> Path:
    """Write HTML to PDF via headless Chromium/Edge."""

    browser = find_chromium_executable()
    if not browser:
        raise RuntimeError(
            "Kein Chromium-Browser gefunden. Bitte Edge oder Chrome installieren."
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        html_path = temp_dir / "kurzentwurf-preview.html"
        html_path.write_text(html, encoding="utf-8")

        command = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--allow-file-access-from-files",
            "--virtual-time-budget=5000",
            "--no-pdf-header-footer",
            "--print-to-pdf-no-header",
            f"--print-to-pdf={str(output_path.resolve())}",
            html_path.resolve().as_uri(),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            details = (result.stderr or result.stdout or "Unbekannter Fehler").strip()
            raise RuntimeError(f"PDF-Erstellung fehlgeschlagen: {details}")

    if not output_path.exists():
        raise RuntimeError("PDF-Datei wurde nicht erstellt.")

    return output_path
