# Blattwerk Validator

Der Validator prueft Blattwerk-Markdown vor dem Build und liefert stabile Diagnosecodes.

Dieses Dokument deckt zwei unabhaengige Diagnosesysteme ab: den Blattwerk-Markdown-Validator
(`FM`/`BL`/`OP`/`AN`/`MA`/`PT`/`QR`-Codes, siehe unten) und die separate Kurzentwurf-DSL
(`KZF`-Codes, siehe [Kurzentwurf-DSL (KZF)](#kurzentwurf-dsl-kzf)) -- beide haben eigene
Einstiegspunkte und eigene Coderaeume, teilen sich aber dieses Referenzdokument.

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
- `BL007`: `nextcol` ausserhalb eines offenen `columns`-Blocks.
- `BL008`: `endcolumns` ohne passenden offenen `columns`-Block.
- `BL009`: `columns`-Block wird bis Dokument- bzw. Folienende nicht mit `endcolumns` geschlossen.
- `BL010`: Verschachtelter `columns`-Block (ein neuer `columns` startet, bevor der vorherige mit `endcolumns` geschlossen wurde).
- `BL011`: Anzahl `nextcol`-Marker zwischen `columns` und `endcolumns` weicht von `cols - 1` ab (Warnung).
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
- `CW001`: `crossword`-Block konnte mit den gegebenen Woertern nicht innerhalb der `maxw`x`maxh`-Rastergroesse platziert werden.
- `CW002`: `crossword`-Block: das `code=`-Loesungswort kann aus den Buchstaben der platzierten Woerter nicht gebildet werden.
- `CW003`: `crossword`-Block: `code_row=true` ohne `code=`-Angabe, oder das Codewort ist kuerzer als die Anzahl der Raetselwoerter.
- `MA001`: `matching`-Block mit nur einem Element auf einer Seite (1↔N) -- didaktisch nicht sinnvoll (Warnung).
- `MJ001`: Block-Inhalt enthaelt `$...$`/`$$...$$`-Formel-Syntax -- die Darstellung laedt MathJax von einem CDN und benoetigt daher beim Export eine Internetverbindung; ohne Internet bleibt die rohe Formel-Quelle als Text sichtbar, wird aber nicht gerendert (Warnung, blocktyp-unabhaengig).
- `PT001`: Absolute lokale Bildpfade in Markdown/HTML-Bildquellen gefunden (Portabilitätswarnung).
- `PT002`: Gerenderte PDF-Seitenzahl groesser als erwartete Folienzahl -- Hinweis auf vertikalen Folien-Overflow (Warnung).
- `QR001`: `qrcode`-Block ohne Pflichtoption `url`.
- `QR002`: `qrcode`-Block mit ungueltiger `url` (erlaubt: http/https oder relativer Pfad ohne Leerzeichen).

## Kurzentwurf-DSL (KZF)

Eigenes Diagnosesystem fuer den Kurzentwurf-Dokumenttyp (`app/core/kurzentwurf_runtime/`,
nicht der Blattwerk-`:::`-Blockdialekt). Einstiegspunkt: `inspect_kurzentwerfer_text(...)`
in `app/core/kurzentwurf_runtime/validator.py`. Ein Dokument mit mindestens einer
`error`-Diagnose liefert kein validiertes `KurzentwurfDocument` (siehe
`InspectionResult.has_errors`).

- `KZF010` (error): Ein Blattwerk-`:::`-Blockdialekt-Marker (`:::`, `§{`, `%{`, `&{`) wurde im Kurzentwurf-Dokument gefunden -- diese gehoeren nicht zur Kurzentwurf-DSL.
- `KZF011` (error): Ungueltiger `#phase`-Hashtag -- entspricht keinem der sechs erlaubten Phasen-Hashtags (siehe `docs/ANLEITUNG_KURZENTWURF.md`, Abschnitt "Phasen").
- `KZF041` (error): Leerer Segmenttrenner `---` ohne Inhalt.
- `KZF042` (error): Ungueltige Inline-Pipe-Syntax -- nur ein alleinstehendes `|` auf einer eigenen Zeile markiert einen Spaltenwechsel.
- `KZF045` (error): YAML-Frontmatter wurde nicht mit einem schliessenden `---` beendet.
- `KZF046` (error): `#phase`-Zeile ohne Phasenname nach dem `#`.
- `KZF047` (error): `t=...` ist keine positive Ganzzahl (Minuten).
- `KZF048` (error): `#phase`-Abschnitt enthaelt keine Segmente.
- `KZF100` (error): Legacy-`[row]`-Blocksyntax ist in der aktuellen DSL (V2) nicht mehr erlaubt.
- `KZF101` (error): Marker mit Doppelpunkt (z. B. `S:`) sind ungueltig -- `S>`/`A>`/`U>`/`s<`/`ant<` verwenden.
- `KZF102` (error): `#phase`-Abschnitt enthaelt kein einziges Segment.
- `KZF115` (error): Erstes Segment einer Phase ist eine reine Vollbreitenzeile ohne Spaltenmarker (`S>`/`A>`/`U>`/`s<`/`ant<`) -- unzulaessig, da es die Phasenzelle der Tabelle verankert.
- `KZF130` (error): Dauer-Modus (`t=...`) erfordert eine globale Startzeit im Frontmatter (`start: HH:MM`).
- `KZF131` (error): Globale Startzeit im Frontmatter ist kein gueltiges `HH:MM`-Format.
- `KZF132` (error): Im Dauer-Modus muss jede zeitpflichtige Phase `t=...` setzen (`Hausaufgabe`/`Didaktische Reserve` ausgenommen).
- `KZF134` (error): `start=...` im `#phase`-Header ist kein gueltiges `HH:MM`-Format.
- `KZF136` (warning): `start=...` weicht von der aus `t=...` fortlaufend berechneten Startzeit ab und wird ignoriert.
- `KZF150` (error): `A>` mit Inhalt auf derselben Zeile -- `A>` markiert nur die Spalte Lernaktivitaeten, Inhalt gehoert auf eine folgende `s<`-Zeile.
- `KZF151` (error): Inhalt in der Spalte Lernaktivitaeten vor dem ersten `s<`.
- `KZF152` (warning): `s<` ohne ein folgendes `ant<` -- Antizipation fehlt.
- `KZF153` (error): `ant>` ist kein gueltiger Marker (kein Alias von `ant<`) -- `ant<` verwenden.
- `KZF200` (error): PyMuPDF ist nicht verfuegbar -- PDF-Vorschau kann nicht gerendert werden.
- `KZF220` (error): Dokument enthaelt keine renderbaren Phasen/Zeilen.

## Blocking-Regel

Der Build wird blockiert, wenn mindestens eine Diagnose die Schwere `error` hat.
Aktuell ist insbesondere `AN003` als kritisch zu behandeln. Fuer Kurzentwurf gilt generell:
jede `error`-Diagnose (siehe Liste oben) blockiert die Dokumentvalidierung.

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
