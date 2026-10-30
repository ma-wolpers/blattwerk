"""Holt das mitgelieferte MathJax-Paket nach `assets/mathjax/`.

Starten mit:  .venv/Scripts/python.exe tools/vendor_mathjax.py

Lädt die Version aus `mathjax_support.MATHJAX_VERSION` von npm, prüft die Prüfsumme und
übernimmt nur, was der Druck braucht: `tex-svg.js`, die TeX-Erweiterungen, die SVG-Schrift
und die Lizenzen (beide Pakete Apache-2.0). Aus 66 MB werden so rund 13 MB. Der Rest
(CHTML, Sprachausgabe, Quellen) wird beim Druck nie geladen.

Nach einem Versionswechsel die Vergleichstests in `tests/test_mathjax_support.py` laufen
lassen: Formeln müssen ohne Internet gesetzt werden.
"""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.mathjax_support import ASSET_DIR, MATHJAX_VERSION  # noqa: E402

PACKAGES = {
    "mathjax": ("tex-svg.js", "input/", "LICENSE", "package.json"),
    "@mathjax/mathjax-newcm-font": ("svg.js", "svg/", "LICENSE", "package.json"),
}


def _download(name: str, version: str, archive: Path) -> None:
    """Lädt das npm-Archiv und prüft es gegen die Prüfsumme aus dem Register.

    Raises:
        ValueError: Die Prüfsumme stimmt nicht.
    """
    quoted = urllib.parse.quote(name, safe="@")
    with urllib.request.urlopen(f"https://registry.npmjs.org/{quoted}/{version}", timeout=60) as response:
        dist = json.load(response)["dist"]
    with urllib.request.urlopen(dist["tarball"], timeout=300) as response:
        data = response.read()
    algorithm, _, expected = dist["integrity"].partition("-")
    if base64.b64encode(hashlib.new(algorithm, data).digest()).decode() != expected:
        raise ValueError(f"Prüfsumme von {name}@{version} stimmt nicht")
    archive.write_bytes(data)


def _extract(archive: Path, target: Path, keep: tuple[str, ...]) -> None:
    """Entpackt nur die erlaubten Pfade; `data_filter` wehrt Pfadtricks im Archiv ab."""
    prefix = "package/"

    def keep_member(member, path):
        if not member.name.startswith(prefix) or not member.name[len(prefix):].startswith(keep):
            return None
        return tarfile.data_filter(member, path)

    with tempfile.TemporaryDirectory(prefix="blattwerk-vendor-x-") as unpack:
        with tarfile.open(archive) as tar:
            tar.extractall(unpack, filter=keep_member)
        shutil.copytree(Path(unpack) / "package", target)


def main() -> None:
    """Ersetzt `assets/mathjax/` durch die Dateien der festgelegten Version."""
    with tempfile.TemporaryDirectory(prefix="blattwerk-vendor-") as temp_dir:
        fresh = Path(temp_dir) / "fresh"
        for name, keep in PACKAGES.items():
            archive = Path(temp_dir) / (name.replace("/", "_") + ".tgz")
            _download(name, MATHJAX_VERSION, archive)
            _extract(archive, fresh / name, keep)
        # Das Schrift-Paket bringt keine eigene Lizenzdatei mit, steht aber unter derselben Apache-2.0.
        shutil.copyfile(fresh / "mathjax" / "LICENSE", fresh / "@mathjax" / "mathjax-newcm-font" / "LICENSE")
        (fresh / "VERSION.txt").write_text(f"{MATHJAX_VERSION}\n", encoding="utf-8")
        if ASSET_DIR.exists():
            shutil.rmtree(ASSET_DIR)
        shutil.copytree(fresh, ASSET_DIR)
    files = [path for path in ASSET_DIR.rglob("*") if path.is_file()]
    print(f"{len(files)} Dateien, {sum(path.stat().st_size for path in files) / 1024 / 1024:.1f} MB in {ASSET_DIR.name}")


if __name__ == "__main__":
    main()
