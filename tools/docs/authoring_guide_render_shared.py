"""Kleine, von beiden Anleitungs-Renderern (Arbeitsblatt/Präsentation, Kurzentwurf)
gemeinsam genutzte Bausteine: der Autogen-Header, das Nachschlagen einzelner
Prosa-Abschnitte und das Fencen von Markdown-Beispielen.

`_prose()` greift bewusst über `import authoring_guide_prose` qualifiziert auf
`authoring_guide_prose.PROSE_SECTIONS` zu (nicht `from ... import PROSE_SECTIONS`)
-- nur so liest jeder Aufruf den aktuellen Stand des Moduls, auch wenn Tests
`authoring_guide_prose.PROSE_SECTIONS` per `monkeypatch` ersetzen.
"""

from __future__ import annotations

import authoring_guide_prose

_AUTOGEN_HEADER = (
    "<!--\n"
    "Automatisch generiert aus app/core/markdown_conventions.py.\n"
    "NICHT VON HAND BEARBEITEN.\n"
    "Neu erzeugen: python tools/docs/generate_authoring_guides.py\n"
    "-->\n\n"
)


def _prose(key: str) -> str:
    return authoring_guide_prose.PROSE_SECTIONS[key]


def _fenced(content: str) -> str:
    return f"```markdown\n{content.strip()}\n```"
