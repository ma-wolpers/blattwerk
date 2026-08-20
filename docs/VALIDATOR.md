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
  - Exportziel-Guardrails: `app/core/export_path_guardrails.py`
- CLI Bridge (JSON): `python -m app.cli.blatt_diagnostics_cli --file <datei.md>`

## Stabiler Diagnosekatalog

- `FM001`: Pflichtfeld im Frontmatter fehlt oder ist leer (`Titel`/`Fach`/`Thema`).
- `FM002`: Ungueltiger Frontmatter-Wert fuer `mode` (erlaubt: `worksheet`, `solution`, `presentation`, `ws`, `test`).
- `FM003`: Ungueltiger Frontmatter-Wert fuer `tag` (kein einfacher, nicht-leerer Textwert).
- `FM004`: Ungueltiger Frontmatter-Wert fuer `presentation_layout`.
- `FM005`: Ungueltiger boolescher Frontmatter-Wert fuer `presentation_show_mini_header`/`presentation_show_section_footer`.
- `FM006`: Ungueltiger boolescher Frontmatter-Wert fuer `show_student_header`/`show_document_header`. Eigenes Boolean-Vokabular (`_meta_bool_ja_nein`/`JA_NEIN_BOOLEAN_TOKENS`), getrennt von `FM005` (`_is_truthy_meta_bool`/`TRUTHY_META_BOOLEAN_TOKENS`) -- beide akzeptieren nicht exakt dieselben Schreibweisen.
- `BL001`: Unbekannter Blocktyp.
- `BL002`: Leerzeichen direkt nach `:::` im Marker (`::: block`) ist ungueltig.
- `BL003`: Schliessender Marker `:::` ohne passenden offenen Block.
- `BL004`: Ungueltiger Blockwechsel: Ein neuer `:::`-Block startet, bevor der aktuell offene Block geschlossen wurde; Marker muessen strikt als Oeffnen/Schliessen abwechseln.
- `BL005`: Abschnittstrenner `---` oder `--` innerhalb eines offenen `:::`-Blocks sind ungueltig; sie sind nur auf Top-Level erlaubt.
- `BL006`: Ungueltiger Abschnitts- (`--#`), Vertikalabstands- (`-=`) oder Folien-Chrome-Marker (`--hf`) -- Syntax entspricht nicht der erwarteten Form.
- `OP001`: Unbekannte Option fuer einen bekannten Block.
- `OP002`: Ungueltiger Wert einer bekannten Option.
- `OP003`: Option `show` in einem Block ist veraltet; `mode=worksheet|solution` verwenden.
- `AN003`: YAML-Fehler in YAML-basiertem `answer`.
- `AN004`: YAML-Root hat falschen Typ (kein Mapping).
- `AN005`: `answer`-Block ist leer (Best-Practice-Warnung).
- `AN006`: Marker-Syntaxfehler in textbasierten `answer`-Inhalten (ungeschlossene Inline-Tokens wie `%{...`).
- `AN007`: Ungueltiger YAML-`show`-Sichtbarkeitswert (erlaubt: `&`, `§`, `%`).
- `AN008`: Legacy-Syntax `:::answer type=...` ist nicht mehr erlaubt; dedizierten Blocktyp nutzen (z. B. `:::grid`, `:::lines`).
- `AN009`: Option `type` ist bei dedizierten Antwort-Blocktypen unzulaessig (der Blocktyp selbst definiert bereits den Antworttyp).
- `AN010`: Ein `task`-/`subtask`- oder textbasierter `answer`-Block nutzt explizite `§`-Marker ohne sichtbares Loesungs-Gegenstueck; pruefe die Paarung von Arbeitsblatt- und Loesungsinhalt.
- `AN011`: Unbekannter YAML-Key in einem `geometry`-Objekt-Eintrag (`points`/`sequence`/`pairs`/`functions`), z. B. ein Tippfehler wie `lable` statt `label`.
- `AN012`: Ungueltiger `line`-Wert in einem `pairs`-Eintrag (erlaubt: `solid`, `dashed`). Objekt-Feld-Ebene, getrennt von der gleichnamigen Block-Option `line=solid|dashed` bei `:::grid`/`:::geometry` (dort `OP002`).
- `AN013`: Ungueltiger `color`-Wert in einem `geometry`-Objekt-Eintrag (kein von `parse_svg_color` akzeptiertes CSS-Farbformat).
- `AN014`: Ungueltiger `thickness`-Wert in einem `geometry`-Objekt-Eintrag (keine positive Zahl).
- `MA001`: `matching`-Block mit nur einem Element auf einer Seite (1↔N) -- didaktisch nicht sinnvoll (Warnung).
- `PT001`: Absolute lokale Bildpfade in Markdown/HTML-Bildquellen gefunden (Portabilitätswarnung).
- `PT002`: Gerenderte PDF-Seitenzahl groesser als erwartete Folienzahl -- Hinweis auf vertikalen Folien-Overflow (Warnung).
- `QR001`: `qrcode`-Block ohne Pflichtoption `url`.
- `QR002`: `qrcode`-Block mit ungueltiger `url` (erlaubt: http/https oder relativer Pfad ohne Leerzeichen).

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
