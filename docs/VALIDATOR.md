# Blattwerk Validator

Der Validator prueft Blattwerk-Markdown vor dem Build und liefert stabile Diagnosecodes.

## Ziel

- einheitliche Diagnosen fuer UI, CLI und VS Code Extension
- klarer Schweregrad pro Diagnose (`warning` oder `error`)
- teilweise blockierender Build bei kritischen Fehlern

## Einstiegspunkte

- Python API: `app/core/blatt_validator.py`
  - `inspect_markdown_text(...)`
  - `inspect_markdown_document(...)`
  - `has_blocking_diagnostics(...)`
  - `summarize_blocking_diagnostics(...)`
- Build-Orchestrierung: `app/core/blatt_kern_io_build.py`
  - `build_worksheet(..., block_on_critical=True)`
  - `build_help_cards(..., block_on_critical=True)`
- CLI Bridge (JSON): `python -m app.cli.blatt_diagnostics_cli --file <datei.md>`

## Stabiler Diagnosekatalog

- `FM001`: Pflichtfeld im Frontmatter fehlt oder ist leer.
- `BL001`: Unbekannter Blocktyp.
- `OP001`: Unbekannte Option fuer einen bekannten Block.
- `OP002`: Ungueltiger Wert einer bekannten Option.
- `AN001`: `answer` ohne Pflichtoption `type`.
- `AN002`: Unbekannter `answer`-Typ.
- `AN003`: YAML-Fehler in YAML-basiertem `answer`.
- `AN004`: YAML-Root hat falschen Typ (kein Mapping).
- `AN005`: `answer`-Block ist leer (Best-Practice-Warnung).
- `AN006`: Marker-Konflikt/Syntaxfehler in textbasierten `answer`-Inhalten (Legacy-Marker am Zeilenanfang und -ende gleichzeitig oder ungeschlossene Inline-Tokens wie `%{...`).

## Blocking-Regel

Der Build wird blockiert, wenn mindestens eine Diagnose die Schwere `error` hat.
Aktuell ist insbesondere `AN003` als kritisch zu behandeln.

## JSON-Bridge Format

Beispielausgabe:

```json
{
  "source": "blattwerk-validator",
  "file": "A:/.../beispiel.md",
  "diagnostics": [
    {
      "code": "AN001",
      "message": "Answer-Block ohne Pflichtoption `type` wird nicht gerendert.",
      "severity": "warning",
      "blockIndex": 3,
      "blockType": "answer",
      "range": {
        "start": { "line": 10, "character": 0 },
        "end": { "line": 10, "character": 18 }
      }
    }
  ]
}
```

Hinweis: Ranges sind fuer Editor-Markierung gedacht und koennen bei unvollstaendigen Blöcken angenaehert sein.
