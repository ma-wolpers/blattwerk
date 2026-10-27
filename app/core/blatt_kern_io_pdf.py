"""Browser PDF generation (Chromium print-to-PDF) and HEIC image fallbacks.

The running-elements stamping lives in `pdf_running_elements.py` and is re-exported
here, so existing imports keep working.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from .pdf_running_elements import (  # noqa: F401 -- re-exportiert (wiring.py)
    annotate_pdf_running_elements,
)


CHROMIUM_COMMAND_CANDIDATES = ["msedge", "chrome", "chromium", "brave"]
CHROMIUM_PATH_CANDIDATES = [
    Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
    Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
    Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
    Path("C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"),
]
_HEIC_EXTENSIONS = {".heic", ".heif"}
_IMG_SRC_PATTERN = re.compile(
    r'(<img\b[^>]*\bsrc\s*=\s*)(["\'])(.*?)(\2)',
    flags=re.IGNORECASE,
)


def _file_uri_to_local_path(uri_text):
    parsed = urlparse(str(uri_text or "").strip())
    if parsed.scheme.lower() != "file":
        return None

    raw_path = unquote(parsed.path or "")
    if parsed.netloc and parsed.netloc not in {"", "localhost"}:
        raw_path = f"//{parsed.netloc}{raw_path}"

    local_text = url2pathname(raw_path)
    if (
        len(local_text) >= 3
        and local_text[0] in {"/", "\\"}
        and local_text[2] == ":"
    ):
        local_text = local_text[1:]

    return Path(local_text)


def _open_image_with_heic_support(image_path):
    try:
        from PIL import Image
    except Exception:
        return None

    def _open_copy():
        with Image.open(image_path) as opened:
            opened.load()
            image = opened.copy()
        if image.mode not in {"1", "L", "LA", "P", "RGB", "RGBA"}:
            image = image.convert("RGB")
        return image

    try:
        return _open_copy()
    except Exception:
        pass

    try:
        from pillow_heif import register_heif_opener

        register_heif_opener()
    except Exception:
        return None

    try:
        return _open_copy()
    except Exception:
        return None


def _rewrite_heic_sources_for_browser_pdf(html, temp_dir):
    source_map = {}
    next_index = 1

    def _replace(match):
        nonlocal next_index
        source_uri = match.group(3).strip()
        local_path = _file_uri_to_local_path(source_uri)
        if local_path is None or local_path.suffix.lower() not in _HEIC_EXTENSIONS:
            return match.group(0)
        if not local_path.exists():
            return match.group(0)

        converted_uri = source_map.get(source_uri)
        if converted_uri is None:
            image = _open_image_with_heic_support(local_path)
            if image is None:
                return match.group(0)

            converted_path = Path(temp_dir) / f"heic_fallback_{next_index:03d}.png"
            next_index += 1
            image.save(converted_path, format="PNG")
            converted_uri = converted_path.resolve().as_uri()
            source_map[source_uri] = converted_uri

        return f"{match.group(1)}{match.group(2)}{converted_uri}{match.group(4)}"

    return _IMG_SRC_PATTERN.sub(_replace, html)


def find_chromium_executable():
    """Sucht einen installierten Chromium-basierten Browser für Headless-PDF."""
    for command in CHROMIUM_COMMAND_CANDIDATES:
        resolved = shutil.which(command)
        if resolved:
            return resolved

    for candidate in CHROMIUM_PATH_CANDIDATES:
        if candidate.exists():
            return str(candidate)

    return None


def write_pdf_from_html(html, out_pdf_path):
    """Schreibt HTML über einen Headless-Browser als PDF-Datei."""
    browser = find_chromium_executable()
    if not browser:
        raise RuntimeError(
            "Kein Chromium-Browser gefunden. Bitte Microsoft Edge oder Google Chrome installieren."
        )

    out_pdf_path = Path(out_pdf_path)
    out_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        html_with_fallbacks = _rewrite_heic_sources_for_browser_pdf(html, temp_dir)
        temp_html_path = temp_dir / "blattwerk-render.html"
        temp_html_path.write_text(html_with_fallbacks, encoding="utf-8")

        # Headless-Druck via Chromium/Edge; erzeugt reproduzierbare PDFs ohne GUI-Interaktion.
        html_uri = temp_html_path.resolve().as_uri()
        command = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--allow-file-access-from-files",
            "--virtual-time-budget=5000",
            "--no-pdf-header-footer",
            "--print-to-pdf-no-header",
            f"--print-to-pdf={str(out_pdf_path.resolve())}",
            html_uri,
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

        # Chromium ist beendet; die Datei ist vollstaendig. Ein vorhandenes Ziel kann aber
        # eine *alte* Datei sein, falls Chromium nicht schreiben durfte - deshalb drucken
        # Exporte immer auf eine frische Arbeitsdatei (`export_staging`).
        if not out_pdf_path.exists():
            raise RuntimeError("PDF-Datei wurde nicht erstellt.")

        return out_pdf_path


