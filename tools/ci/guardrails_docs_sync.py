"""Doku-Synchronitaets-Guardrails: generierte Autoren-Anleitungen, KZF-Diagnose-Doku und
der integrierte Kurzentwurf-Runtime-Pfad.
"""

from __future__ import annotations

import re
import sys

from guardrails_config import (
    INTEGRATED_KURZENTWURF_RUNTIME_ROOT,
    ROOT,
)
from guardrails_common import (
    _read,
    _require_substring,
)


def _check_authoring_guides_sync(errors: list[str]) -> None:
    """Rendert die Autoren-Anleitungen frisch und vergleicht sie mit den committeten Dateien.

    Wird in `main()` **unconditionally** aufgerufen (vor der Staged-File-
    Gate-Liste), nicht hinter `GUARDRAIL_RELEVANT_PATHS` -- eine Aenderung
    an den zugrundeliegenden Code-Katalogen (Validator-/Parser-/
    Kurzentwurf-Konstanten in `app/core/markdown_conventions.py`) darf
    diese Pruefung nie unbemerkt umgehen, selbst wenn die betroffene Datei
    aus der Pfadliste vergessen wurde. `_staged_files()` liest ohnehin nur
    lokal gestagte Aenderungen; in CI (frischer Checkout, kein Staged-
    State) greift die Gate-Liste sowieso nie.
    """
    tools_docs_dir = ROOT / "tools" / "docs"
    if str(tools_docs_dir) not in sys.path:
        sys.path.insert(0, str(tools_docs_dir))

    try:
        import generate_authoring_guides as guide_generator
    except Exception as exc:  # pragma: no cover - defensive guardrail fallback
        errors.append(f"tools/docs/generate_authoring_guides.py: Import fehlgeschlagen ({exc})")
        return

    try:
        fresh_guides = guide_generator.generate_guides()
    except guide_generator.ProseCoverageError as exc:
        errors.append(f"tools/docs/generate_authoring_guides.py: {exc}")
        return
    except Exception as exc:  # pragma: no cover - defensive guardrail fallback
        errors.append(f"tools/docs/generate_authoring_guides.py: Generierung fehlgeschlagen ({exc})")
        return

    for path, content in fresh_guides.items():
        rel_path = path.relative_to(ROOT).as_posix()
        if not path.exists():
            errors.append(
                f"{rel_path}: fehlt -- mit `python tools/docs/generate_authoring_guides.py` erzeugen"
            )
            continue
        existing = path.read_text(encoding="utf-8")
        if existing != content:
            errors.append(
                f"{rel_path}: veraltet gegenueber aktuellem Code-Katalog -- neu erzeugen mit "
                "`python tools/docs/generate_authoring_guides.py`"
            )


_KZF_CODE_SEVERITY_RE = re.compile(r'code="(KZF\d+)",\s+severity="(\w+)"')
_KZF_DOC_ENTRY_RE = re.compile(r'`(KZF\d+)`\s*\((\w+)\)')


def _extract_kzf_codes_from_runtime_source(errors: list[str]) -> dict[str, str]:
    """Extract every `(code, severity)` pair from `Diagnostic(code="KZF...", severity="...")` calls.

    Rein textuell (kein Import von `kurzentwurf_runtime`), analog zu allen
    anderen Checks in dieser Datei. Meldet einen Fehler, wenn derselbe Code
    an verschiedenen Fundstellen mit unterschiedlichem Schweregrad auftaucht
    (aktuell nicht der Fall, aber wuerde eine Ein-Zeile-pro-Code-Doku im
    Kurzentwurf-Abschnitt von docs/nutzer/VALIDATOR.md unmoeglich machen).
    """
    codes: dict[str, str] = {}
    root_dir = ROOT / INTEGRATED_KURZENTWURF_RUNTIME_ROOT
    if not root_dir.exists():
        return codes
    for file_path in sorted(root_dir.glob("*.py")):
        rel_path = file_path.relative_to(ROOT).as_posix()
        text = _read(rel_path)
        for match in _KZF_CODE_SEVERITY_RE.finditer(text):
            code, severity = match.group(1), match.group(2)
            existing = codes.get(code)
            if existing is not None and existing != severity:
                errors.append(
                    f"{rel_path}: KZF-Code {code} hat widerspruechliche Schweregrade "
                    f"({existing} vs. {severity}) an verschiedenen Fundstellen -- "
                    "Ein-Zeile-pro-Code-Dokumentation in docs/nutzer/VALIDATOR.md nicht mehr moeglich"
                )
            codes[code] = severity
    return codes


def _check_kurzentwurf_diagnostics_sync(errors: list[str]) -> None:
    """Ensure every KZF diagnostic code+severity in the runtime matches docs/nutzer/VALIDATOR.md.

    Hybridmodell wie beim Blattwerk-Validator: Code ist die Wahrheit,
    `docs/nutzer/VALIDATOR.md` bleibt redaktionell formuliert (die Erklaerung je
    Code muss nicht wortgleich mit der Fehlermeldung im Code sein) --
    geprueft wird nur, dass jeder Code samt Schweregrad in beide Richtungen
    exakt uebereinstimmt (kein fehlender, kein veralteter, kein Code mit
    abweichendem Schweregrad). Laeuft unconditionally in `main()` (siehe
    `_check_authoring_guides_sync`-Docstring fuer die Begruendung).
    """
    code_severity_in_source = _extract_kzf_codes_from_runtime_source(errors)
    if not code_severity_in_source:
        return

    validator_doc = _read("docs/nutzer/VALIDATOR.md")
    section_marker = "## Kurzentwurf-DSL (KZF)"
    if section_marker not in validator_doc:
        errors.append(f"docs/nutzer/VALIDATOR.md: fehlender Abschnitt '{section_marker}'")
        return
    section_text = validator_doc.split(section_marker, 1)[1].split("\n## ", 1)[0]

    code_severity_in_doc: dict[str, str] = {}
    for match in _KZF_DOC_ENTRY_RE.finditer(section_text):
        code_severity_in_doc[match.group(1)] = match.group(2)

    missing_in_doc = sorted(set(code_severity_in_source) - set(code_severity_in_doc))
    if missing_in_doc:
        errors.append(
            "docs/nutzer/VALIDATOR.md: KZF-Codes im Code, aber nicht im Kurzentwurf-Abschnitt "
            f"dokumentiert -> {missing_in_doc}"
        )

    stale_in_doc = sorted(set(code_severity_in_doc) - set(code_severity_in_source))
    if stale_in_doc:
        errors.append(
            "docs/nutzer/VALIDATOR.md: KZF-Codes im Kurzentwurf-Abschnitt dokumentiert, aber nicht "
            f"(mehr) im Code -> {stale_in_doc}"
        )

    for code in sorted(set(code_severity_in_source) & set(code_severity_in_doc)):
        code_severity_source = code_severity_in_source[code]
        code_severity_doc = code_severity_in_doc[code]
        if code_severity_source != code_severity_doc:
            errors.append(
                f"docs/nutzer/VALIDATOR.md: {code} hat Schweregrad '{code_severity_doc}' in der Doku, "
                f"aber '{code_severity_source}' im Code"
            )


def _check_integrated_kurzentwurf_runtime(errors: list[str]) -> None:
    """Validate the embedded Kurzentwurf runtime used by Blattwerk."""

    required_runtime_files = (
        f"{INTEGRATED_KURZENTWURF_RUNTIME_ROOT}/__init__.py",
        f"{INTEGRATED_KURZENTWURF_RUNTIME_ROOT}/build.py",
        f"{INTEGRATED_KURZENTWURF_RUNTIME_ROOT}/column_widths.py",
        f"{INTEGRATED_KURZENTWURF_RUNTIME_ROOT}/dsl.py",
        f"{INTEGRATED_KURZENTWURF_RUNTIME_ROOT}/model.py",
        f"{INTEGRATED_KURZENTWURF_RUNTIME_ROOT}/pdf_export.py",
        f"{INTEGRATED_KURZENTWURF_RUNTIME_ROOT}/render_html.py",
        f"{INTEGRATED_KURZENTWURF_RUNTIME_ROOT}/validator.py",
    )

    for rel_path in required_runtime_files:
        if not (ROOT / rel_path).exists():
            errors.append(f"{rel_path}: missing required integrated Kurzentwurf runtime file")

    model_rel = f"{INTEGRATED_KURZENTWURF_RUNTIME_ROOT}/model.py"
    if (ROOT / model_rel).exists():
        _require_substring(_read(model_rel), "FORBIDDEN_BLATTWERK_MARKERS", model_rel, errors)

    validator_rel = f"{INTEGRATED_KURZENTWURF_RUNTIME_ROOT}/validator.py"
    if (ROOT / validator_rel).exists():
        validator_source = _read(validator_rel)
        _require_substring(validator_source, "KZF010", validator_rel, errors)
        _require_substring(validator_source, "KZF101", validator_rel, errors)

    build_rel = f"{INTEGRATED_KURZENTWURF_RUNTIME_ROOT}/build.py"
    if (ROOT / build_rel).exists():
        _require_substring(_read(build_rel), "build_preview_images", build_rel, errors)


