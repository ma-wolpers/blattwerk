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

## Headless-Nutzung (ohne GUI)

Für Skripte, CI oder Agents, die eine `.md`-Datei pruefen oder exportieren wollen, ohne die
Qt-App zu starten:

```bash
# Nur validieren, Diagnosen als JSON auf stdout
python -m app.cli.blatt_diagnostics_cli --file datei.md --pretty --mode standard
# --fail-on-blocking gibt Exit-Code 3 zurueck, wenn `mode` blockierende Diagnosen enthaelt
```

```python
# Programmatisch validieren
from pathlib import Path
from app.core.blatt_validator import inspect_markdown_document, has_blocking_diagnostics

result = inspect_markdown_document(Path("datei.md"))
for d in result.diagnostics:
    print(d.code, d.severity, d.message)
print("blocking:", has_blocking_diagnostics(result.diagnostics))
```

```python
# Headless nach PDF exportieren (nutzt intern per subprocess einen lokal installierten
# Chromium/Edge/Chrome/Brave im --headless=new-Modus, kein Qt/GUI noetig; endet der
# out_path auf .html statt .pdf, wird gar kein Browser gebraucht)
from app.core.blatt_kern_io_build import build_worksheet

diagnostics = []
build_worksheet(
    "datei.md", "ausgabe.pdf",
    include_solutions=False,   # True fuer die Loesungsansicht
    diagnostics_out=diagnostics,
    block_on_critical=True,     # wirft bei blockierenden Diagnosen eine Exception
)
```

Analog existiert `build_help_cards(...)` fuer den Hilfekarten-Export. Aufrufmuster ohne
Subprozess siehe `tests/test_blatt_diagnostics_cli.py` (Validator) sowie
`tests/test_operator_legend.py`/`tests/test_core_wiring.py` (`build_worksheet`).

## Stabiler Diagnosekatalog

- `FM001`: Pflichtfeld im Frontmatter fehlt oder ist leer (`Titel`/`Fach`/`Thema`).
- `FM002`: **entfallen.** Pruefte frueher Werte des Frontmatter-Felds `mode`, das es nicht mehr gibt (der Dokumenttyp kommt aus der Dateiendung). Eine stehengebliebene `mode`-Zeile wird wie jeder unbekannte Key still ignoriert.
- `FM003`: Ungueltiger Frontmatter-Wert fuer `tag` (kein einfacher, nicht-leerer Textwert).
- `FM004`: Ungueltiger Frontmatter-Wert fuer `presentation_layout`.
- `FM005`: Ungueltiger boolescher Frontmatter-Wert fuer `presentation_show_mini_header`/`presentation_show_section_footer`.
- `FM006`: Ungueltiger boolescher Frontmatter-Wert fuer `show_student_header`/`show_document_header`. Eigenes Boolean-Vokabular (`_meta_bool_ja_nein`/`JA_NEIN_BOOLEAN_TOKENS`), getrennt von `FM005` (`_is_truthy_meta_bool`/`TRUTHY_META_BOOLEAN_TOKENS`) -- beide akzeptieren nicht exakt dieselben Schreibweisen.
- `FM007`: Ungueltiger Frontmatter-Wert fuer `Stufe` (erlaubt, gross-/kleinschreibungsunabhaengig: `5`-`13`, `E`, `Q1`, `Q2`, `Sek1`, `Sek2`). Nicht gesetzt bleibt gueltig (Warnung, kein Pflichtfeld).
- `FM008`: `document_type` passt nicht zur Dateiendung (gueltiger Wert, anderer Typ). Warnung; es gilt immer die Endung. Gilt fuer alle Endungen, auch `.md` (z. B. nach Speichern-unter nach `.md`, das den Marker bewusst unveraendert laesst).
- `FM009`: `document_type` fehlt in einer Blattwerk-Datei (`.abw`, `.pbw`, `.kbw`, `.ebw`, `.sbw`). Warnung. In `.md` ist der Marker optional, dort gibt es kein `FM009`.
- `FM010`: Ungueltiger Wert fuer `document_type` (kein bekannter Typ oder Alias, oder kein Text). Warnung.
- `FM012`: Unbekanntes Schriftprofil in `font_profile` (die Meldung nennt alle erlaubten Werte). Warnung; gerendert wird mit der Schrift der App-Einstellung.
- `FM011`: `Lerngruppe`/`Datum` hat einen YAML-Typ, der nicht in die Schuelerkopfzeile uebernommen wird (z. B. `Lerngruppe: 11.6` wird als Zahl gelesen -- in Anfuehrungszeichen setzen). Warnung; das Feld bleibt leer. `Datum` darf Text oder ein ISO-Datum sein.
- `EV001`: Bewertungstabelle `:::evaluation` vorhanden, aber Aufgaben ohne Punkte (Zelle `–`). Warnung.
- `EV002`: Bewertungstabelle in einem Dokumenttyp ohne diese Funktion (z. B. Praesentation); sie wird nicht angezeigt. Warnung.
- `KL001`: `--hm` kommt in einer Klausur mehr als zweimal vor (erlaubt: einmal fuer Teil A | Teil B, zweimal fuer Deckblatt | Teil A | Teil B). Fehler.
- `KL002`: `--hm` ausserhalb einer Klausur (`.kbw`); ohne Wirkung. Warnung.
- `KL003`: Bepunktete Aufgabe bzw. Teilaufgabe einer Klausur ohne Anforderungsbereich (`afb=1|2|3`); die AFB-Auswertung ist dann unvollstaendig. Warnung.
- `KL004`: Ein Teil-Trenner steht falsch: `--hm` nicht zwischen zwei Aufgaben auf oberster Ebene, oder ein Wahlteil (`--w`) enthaelt keine Aufgabe, oder der Trenner steht innerhalb von `:::columns`. Fuer `--hm`: `--hm` steht nicht zwischen zwei Aufgaben auf oberster Ebene (keine Aufgabe davor oder danach, oder innerhalb von `:::columns`). Bei zwei Markern muss zwischen ihnen (Teil A) mindestens eine Aufgabe (`:::task`) stehen -- eine Teilaufgabe allein zaehlt nicht. Fehler.
- `KL005`: Nach `--hm` bzw. `--w` folgt keine neue Aufgabe, sondern eine Teilaufgabe oder Loesung (sie wuerde von ihrer Aufgabe getrennt). Fehler.
- `KL007`: Vor dem ersten von zwei `--hm` (Deckblatt) steht eine Aufgabe, Teilaufgabe oder Loesung. Das Deckblatt darf alles andere enthalten (Hinweise, `:::info`, `:::evaluation` ...), aber keine Aufgaben. Fehler.
- `KL006`: `afb` an einer Teilaufgabe wirkt nicht, weil die Teilaufgaben keine eigenen Punkte haben. Warnung.
- `KL008`: `--w` ohne offenen Wahlbereich -- der erste Wahlteil eines Bereichs braucht die Anzahl (`--w[1] Titel`). Fehler.
- `KL009`: `--w[k]` in einem bereits offenen Wahlbereich; weitere Wahlteile ohne `[k]`, ein neuer Bereich erst nach `--hm`. Fehler.
- `KL010`: Ungueltiges k in `--w[k]` (keine ganze Zahl oder nicht 1 <= k < Anzahl der Wahlteile). Fehler.
- `KL011`: Die Wahlteile eines Bereichs haben unterschiedlich viele Punkte (geprueft, wenn alle Punkte gueltig sind). Fehler.
- `KL012`: `--w` ausserhalb einer Klausur (`.kbw`). Fehler.
- `KL013`: Eine (Teil-)Aufgabe hat eine Lernhilfe, aber weder ihre Loesung noch die der zugehoerigen Aufgabe enthaelt einen Lernhilfe-Abzug, z. B. `1. Lernhilfe genutzt (−1P Lh)`. Nur in Klausuren. Warnung.
- `PK001`: Aufgabe hat `points`, die nicht der Summe ihrer (vollstaendig bepunkteten) Teilaufgaben entsprechen. Fehler (blockiert den Export).
- `PK002`: Summe der Teilpunkte `(xP)` in den Loesungen einer (Teil-)Aufgabe weicht von deren Punktzahl ab (nur wenn alle Loesungspunkte annotiert sind). Bei alternativen Wegen (`(0,5aP)`/`(1bP)`) zaehlt gemeinsam (ohne Buchstabe) + bester Weg, bei summativen Optionen (`(1/2P)`) zusaetzlich deren Summe bis zum Hoechstwert; Abzuege je Fehler (`(−0,5P)`) zaehlen nie mit; der Vergleich ist exakt. Fehler.
- `PK003`: Punktangabe ist keine Zahl (erlaubt: `2`, `2,5`, `2.5`). Warnung; der Text wird trotzdem angezeigt.
- `PK004`: Nur ein Teil der Teilaufgaben einer Aufgabe ist bepunktet. Fehler.
- `PK005`: Teilpunkte `(xP)` auf Aufgabenebene (auch per `target=task`), obwohl die Teilaufgaben bepunktet sind. Fehler.
- `PK006`: Teilpunkte `(xP)` vergeben, aber die (Teil-)Aufgabe hat keine eigene Punktzahl. Warnung.
- `SL001`: `:::solution` ohne vorangehende Aufgabe (bzw. erste Loesung hinter `--hm`); wird keiner Aufgabe zugeordnet. Warnung.
- `SL004`: `(xP)` an einer Listen- oder Aufzaehlungszeile, die nicht die erste Zeile eines Loesungspunkts `1. …` ist (Unterpunkt, `- …`, `1) …`); zaehlt nicht. Warnung.
- `SL005`: Erwartungshorizont: Eine (Teil-)Aufgabe hat Erwartungen, aber keine einzige Teilpunkt-Angabe `(xP)`; die Punktspalte bleibt leer. Warnung beim Export des Erwartungshorizonts.
- `SL006`: Nur ein Teil der Erwartungspunkte einer (Teil-)Aufgabe hat `(xP)`; keine Summenpruefung. Warnung.
- `SL007`: Erwartungshorizont: Eine (Teil-)Aufgabe hat keine nummerierte Erwartung; es erscheint "keine Erwartung hinterlegt". Warnung beim Export des Erwartungshorizonts.
- `SL008`: Ungueltiges `target=` an `:::solution` (kein Subtask mit diesem Bezeichner in derselben Aufgabe bzw. keine Aufgabe davor). Fehler.
- `SL009`-`SL014`: **entfallen.** Prueften frueher die nicht summative Teilpunkt-Schreibweise `(x/nP)`. Alternative Wege tragen heute einen Buchstaben (`(0,5aP)`); `(x/kP)` bedeutet jetzt eine summative Option (siehe `SL019`-`SL022`).
- `SL015`: In einer (Teil-)Aufgabe ist nur ein Weg-Buchstabe vergeben (angezeigt als „Weg A“) -- ohne zweiten Weg gibt es keine Alternative. Warnung. Die Buchstaben gelten je (Teil-)Aufgabe (auch ueber mehrere `:::solution`-Bloecke derselben Teilaufgabe); eine (Teil-)Aufgabe hat genau eine Wahlentscheidung -- zwei unabhaengige Entscheidungen auf zwei Teilaufgaben verteilen.
- `SL016`: Abzug je Fehler mit Weg-Buchstabe (z. B. `(−0,5aP)`). Warnung; Abzuege gelten fuer die ganze (Teil-)Aufgabe, der Buchstabe wird ignoriert.
- `SL017`: Unbekannter Erwartungstyp im Punkt-Suffix (z. B. `(1P Xy)`). Warnung mit Liste der gueltigen Typen (Name oder Kuerzel); Punktwert und Weg zaehlen trotzdem, nur Symbol und Legende entfallen fuer diesen Punkt.
- `SL018`: Punktangabe am Ende eines Loesungspunkts ist nicht lesbar (beginnt mit einer Zahl und enthaelt `P`, passt aber zu keiner erlaubten Form, z. B. `(0,5abP)`). Fehler; fuer diese (Teil-)Aufgabe entfallen `SL006`, `SL015` und `PK002`.
- `SL019`: Summative Optionen `(x/kP)` mit verschiedenen Hoechstwerten k in derselben (Teil-)Aufgabe. Fehler; alle Optionen eines Ziels brauchen dasselbe k (eine Optionsgruppe je (Teil-)Aufgabe).
- `SL020`: Eine einzelne Option `(x/kP)` bringt mehr als den Hoechstwert (x > k). Fehler.
- `SL021`: Die Optionen einer (Teil-)Aufgabe ergeben zusammen weniger als den Hoechstwert k -- er ist nicht erreichbar. Fehler.
- `SL022`: Die Optionen ergeben genau den Hoechstwert -- jede wird gebraucht, `(xP)` genuegt statt `(x/kP)`. Warnung.
- `SL023`: Ein Erwartungstyp, der nur als Abzug gilt (Lernhilfe `Lh`), steht ohne Minuszeichen, z. B. `(1P Lh)` statt `(−1P Lh)`. Warnung.
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
- `BL012`: `:::help`/`:::hilfe` in einer Praesentation (`.pbw`) -- Lernhilfen sind dort veraltet und gibt es nur noch in Arbeitsblaettern und Klausuren. Der Block wird noch dargestellt. Warnung.
- `OPR001`: Ein `!!...!!`-Operator-Marker passt zu keinem bekannten Operator des Fachs. Warnung.
- `OPR002`: **entfallen** (frueher Laufzeitpruefung der Operatoren-Daten; jetzt Test der Daten-Dateien).
- `OPR003`: Operator-Marker verwendet, aber keine Operatoren-Datei fuer `Fach` in `data/operatoren/`. Warnung.
- `OPR004`: Operatoren verwendet, aber keine Operatorentabelle `:::operators:::` im Dokument (sie wird nicht mehr automatisch angehaengt). Warnung.
- `OPR005`: Operatoren, die keine Operatorentabelle abdeckt (z. B. nach der letzten Tabelle mit `scope=previous`). Warnung; eine Fundstelle ist abgedeckt, sobald mindestens eine Tabelle sie einschliesst.
- `OPR006`: Operatorentabelle ohne einen einzigen Operator-Marker in ihrem Bereich -- sie bliebe leer. Fehler.
- `OPR007`: Operatorentabelle in einem Dokumenttyp ohne diese Funktion (z. B. Praesentation); sie wird nicht angezeigt. Warnung.
- `OPR008`: Die Bereiche zweier Operatorentabellen ueberschneiden sich (dieselben Operatoren stehen in mehreren Tabellen). Warnung, einmal je beteiligter Tabelle.
- `OP001`: Unbekannte Option fuer einen bekannten Block.
- `OP002`: Ungueltiger Wert einer bekannten Option.
- `OP003`: Option `show` in einem Block ist veraltet; `mode=worksheet|solution` verwenden.
- `OP004`: Option `mode` bzw. `show` bei `:::solution` ist veraltet und wird ignoriert -- Loesungen erscheinen nur in der Loesungsfassung. Warnung.
- `OP005`: `:::geometry axis=true` ohne gueltiges `origin` (Format `"col,row"`). Fehler -- der gesamte Geometry-Payload des Blocks (alle Sektionen) wird dadurch nicht gerendert, kein stiller Ruecksfall auf Rasterkoordinaten.
- `AN003`: YAML-Fehler in YAML-basiertem `answer`.
- `AN004`: YAML-Root hat falschen Typ (kein Mapping).
- `AN005`: `answer`-Block ist leer (Best-Practice-Warnung). Nicht in Klausuren (`.kbw`): dort sind Antwortfelder absichtlich leer, die Loesung steht in `:::solution` (Registry-Capability `empty_answer_hint`).
- `AN006`: Marker-Syntaxfehler in textbasierten `answer`-Inhalten (ungeschlossene Inline-Tokens wie `%{...`).
- `AN007`: Ungueltiger YAML-`show`-Sichtbarkeitswert (erlaubt: `&`, `§`, `%`).
- `AN008`: Legacy-Syntax `:::answer type=...` ist nicht mehr erlaubt; dedizierten Blocktyp nutzen (z. B. `:::grid`, `:::lines`).
- `AN009`: Option `type` ist bei dedizierten Antwort-Blocktypen unzulaessig (der Blocktyp selbst definiert bereits den Antworttyp).
- `AN010`: Ein `task`-/`subtask`- oder textbasierter `answer`-Block nutzt explizite `§`-Marker ohne sichtbares Loesungs-Gegenstueck; pruefe die Paarung von Arbeitsblatt- und Loesungsinhalt.
- `AN011`: Unbekannter YAML-Key in einem `geometry`-Objekt-Eintrag (`points`/`sequence`/`pairs`/`polygons`/`circles`/`functions`), z. B. ein Tippfehler wie `lable` statt `label`.
- `AN012`: Ungueltiger `line`-Wert in einem `pairs`-Eintrag (erlaubt: `solid`, `dashed`). Objekt-Feld-Ebene, getrennt von der gleichnamigen Block-Option `line=solid|dashed` bei `:::grid`/`:::geometry` (dort `OP002`).
- `AN013`: Ungueltiger `color`- oder `fill`-Wert in einem `geometry`-Objekt-Eintrag (kein von `parse_svg_color` akzeptiertes CSS-Farbformat).
- `AN014`: Ungueltiger `thickness`-Wert in einem `geometry`-Objekt-Eintrag (keine positive Zahl).
- `AN015`: `functions`-Eintraege ohne aktiven Achsenmodus (`axis=true` mit gueltigem `origin`) -- rendern nie etwas, da Funktionsgraphen ohne mathematisches Koordinatensystem nicht definiert sind.
- `AN019`: Eine `geometry`-Beschriftung findet bei `labels=auto` keinen Platz, an dem sie kein Punktkreuz und keine andere Beschriftung ueberdeckt (auch nicht nach erweiterter Suche). Warnung; die Beschriftung steht dann an der am wenigsten stoerenden Stelle. Abhilfe: Zeichnung groesser, Punkte weiter auseinander, Text kuerzer -- oder bewusst `labels=fixed`.
- `AN020`: `widths=` einer `table` hat die falsche Anzahl Werte. Erlaubt sind so viele Werte wie Datenspalten (`cols`, mindestens die Anzahl `column_headers` bzw. der laengsten `cells:`-Zeile) und -- mit `row_headers` -- ein Wert mehr, dessen erster fuer die Kopfspalte gilt. Warnung; ueberzaehlige Werte werden ignoriert, zu wenige heben `widths` ganz auf.
- `AN017`: Ungueltiges Polygon in einem `polygons`-Eintrag (`vertices` mit weniger als 3 Eintraegen, oder mindestens ein Eckpunkt ohne numerisches `x`/`y`) -- das gesamte Polygon wird nicht gerendert, keine Teil-Reparatur einzelner Eckpunkte.
- `AN018`: Ungueltiger Kreis/Bogen in einem `circles`-Eintrag (`cx`/`cy`/`r` fehlt/nicht positiv, ODER genau einer von `start_angle`/`end_angle` gesetzt, ODER beide gesetzt aber mindestens einer nicht numerisch parsebar) -- der gesamte Eintrag wird nicht gerendert.
- `CW001`: `crossword`-Block konnte mit den gegebenen Woertern nicht innerhalb der `maxw`x`maxh`-Rastergroesse platziert werden.
- `CW002`: `crossword`-Block: das `code=`-Loesungswort kann aus den Buchstaben der platzierten Woerter nicht gebildet werden.
- `CW003`: `crossword`-Block: `code_row=true` ohne `code=`-Angabe, oder das Codewort ist kuerzer als die Anzahl der Raetselwoerter.
- `CW004`: `crossword`-Block enthaelt dasselbe Wort mehrfach (nach Normalisierung) -- wird weiterhin platziert (kein Verwerfen), reiner Hinweis, falls das ein Versehen ist (Warnung).
- `CW005`: `crossword`-Block: `numbering=symbols`/`code_numbering=symbols` braucht mehr Positionen (Hinweis-Nummern bzw. Codewort-Stellen), als das gewaehlte `symbol_set`/`code_symbol_set` Symbole enthaelt. Kein Fallback auf Zahlen, kein Wiederverwenden von Symbolen -- anderes Set waehlen oder `numeric`/`letters` verwenden.
- `IM002`: Fehlerhafte Worterklaerung `??Begriff|Erklaerung??` -- fehlendes oder mehrfaches `|` oder leerer Begriff/leere Erklaerung (Fehler, blockiert den Export). Ein woertliches `|` schreibt man `\|`, ein woertliches `??` schreibt man `\??`. Der fehlerhafte Text bleibt unveraendert als Text stehen.
- `IM004`: Fehlerhafter Inline-Stil `-<…>`: unbekannte Schrift oder Farbe, doppelte Angabe, Groesse ausserhalb 4-120 pt, `-<>` ohne offenen Bereich oder ein Bereich, der vor einer Leerzeile, einem Listenpunkt, einer Tabellenzelle oder am Blockende nicht geschlossen ist (Fehler, blockiert den Export).
- `PPTX003`: Die editierbare PPTX nutzt mitgelieferte Schriften, die PowerPoint nur anzeigt, wenn sie installiert sind; die Meldung nennt die Ersatzschrift (Warnung).
- `IM003`: Worterklaerung steht im gerenderten PDF nicht (vollstaendig) in der rechten Randspalte -- entweder weil sie in einer Tabellenzelle oder in einer nicht-letzten Spalte steht, oder weil sie nicht mehr auf die Seite ihres Absatzes passt und im Rand der Folgeseite weiterlaeuft (Warnung, nur nach dem PDF-Export messbar; Best-Effort-Pruefung).
- `MA001`: `matching`-Block mit nur einem Element auf einer Seite (1↔N) -- didaktisch nicht sinnvoll (Warnung).
- `MJ001`: Block-Inhalt enthaelt `$...$`/`$$...$$`-Formel-Syntax -- die Darstellung laedt MathJax von einem CDN und benoetigt daher beim Export eine Internetverbindung; ohne Internet bleibt die rohe Formel-Quelle als Text sichtbar, wird aber nicht gerendert (Warnung, blocktyp-unabhaengig).
- `PT001`: Absolute lokale Bildpfade in Markdown/HTML-Bildquellen gefunden (Portabilitätswarnung).
- `PT002`: Gerenderte PDF-Seitenzahl groesser als erwartete Folienzahl -- Hinweis auf vertikalen Folien-Overflow (Warnung).
- `QR001`: `qrcode`-Block ohne Pflichtoption `url`.
- `QR002`: `qrcode`-Block mit ungueltiger `url` (erlaubt: http/https oder relativer Pfad ohne Leerzeichen).
- `SG001`-`SG008` (`struktogramm`-Block, Fehler; Meldung nennt die Zeile im Block): `SG001` Einrueckung passt nicht zur Einheit der ersten eingerueckten Zeile, `SG002` eingerueckte Zeile ohne Kopf (z. B. unter einer Anweisung), `SG003` `sonst`/`fall`/`bis` ohne passenden Kopf, `SG004` `wiederhole` ohne abschliessendes `bis …`, `SG005` Schleife ohne Rumpf bzw. `auswahl` ohne `fall`, `SG006` Schluesselwort ohne Text dahinter (z. B. `wenn` ohne Bedingung, `rückgabe` ohne Ausdruck), `SG008` in `auswahl` steht etwas anderes als `fall …`/ein abschliessendes `sonst`. `SG007`: Block ist leer (Warnung).
- `SG010`-`SG013` (`struktogramm`, Fehler): `signature=` folgt nicht der GO-Form `Bezeichnung(Parameter: Typ, ...): Rückgabetyp` -- `SG010` Klammerung/Rest nach `)`, `SG011` ungueltiger oder leerer Bezeichner, `SG012` Parameter ohne Typ, `SG013` leerer oder ungueltiger (Rueckgabe-)Typ.
- `SG020`: `struktogramm` ohne `signature=` (Warnung; GO-Struktogramme haben immer einen Methodenkopf).
- `SG021`: `rückgabe` im Struktogramm, aber die Signatur hat keinen Rueckgabetyp (Fehler).
- `SG022`: Signatur mit Rueckgabetyp, aber nicht jeder Ablauf endet mit `rückgabe` (Warnung). Verzweigung zaehlt nur mit Rueckgabe in beiden Zweigen, Auswahl nur mit `sonst`, kopfgesteuerte Schleifen nie (koennen 0-mal laufen), fussgesteuerte ueber ihren Rumpf. Steht `gib … zurück` woertlich als Anweisung da, nennt die Meldung `rückgabe …` als Schreibweise.
- `SG023`: Ein Parameter der Signatur kommt im Struktogramm nicht als Wort vor (Warnung).
- `SC001`: `selfcheck`-Block: `steps=` liegt ausserhalb des gueltigen Bereichs (2-7) oder ausserhalb der fuer die gewaehlte `scale=` kuratierten Werte (z. B. `smiley` nur bei `steps=3`/`5`) -- wird begrenzt bzw. faellt auf nummerierte Kreise zurueck, reiner Hinweis (Warnung).

## Kurzentwurf-DSL (KZF)

Eigenes Diagnosesystem fuer den Kurzentwurf-Dokumenttyp (`app/core/kurzentwurf_runtime/`,
nicht der Blattwerk-`:::`-Blockdialekt). Einstiegspunkt: `inspect_kurzentwerfer_text(...)`
in `app/core/kurzentwurf_runtime/validator.py`. Ein Dokument mit mindestens einer
`error`-Diagnose liefert kein validiertes `KurzentwurfDocument` (siehe
`InspectionResult.has_errors`).

- `KZF010` (error): Ein Blattwerk-`:::`-Blockdialekt-Marker (`:::`, `§{`, `%{`, `&{`) wurde im Kurzentwurf-Dokument gefunden -- diese gehoeren nicht zur Kurzentwurf-DSL.
- `KZF011` (error): Ungueltiger `#phase`-Hashtag -- entspricht keinem der sechs erlaubten Phasen-Hashtags (siehe `docs/nutzer/ANLEITUNG_KURZENTWURF.md`, Abschnitt "Phasen").
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
- `KZF154` (warning): `ant<` steht ausserhalb eines `A>`-Blocks -- vor dem ersten `s<` des Segments oder hinter `S>`-/`U>`-Inhalt bzw. einem `|`-Spaltenwechsel. Antizipationen gehoeren direkt hinter das zugehoerige `s<`; ein erneutes `A>` macht die Lernaktivitaeten wieder zur aktiven Spalte. Gerendert wird die Antizipation trotzdem (unter den Lernaktivitaeten).
- `KZF160` (warning): Dokument enthaelt `$...$`/`$$...$$`-Formel-Syntax -- die Darstellung laedt MathJax von einem CDN und benoetigt daher bei Vorschau/PDF-Export eine Internetverbindung; ohne Internet bleibt die rohe Formel-Quelle als Text sichtbar (einmal pro Dokument, an der ersten Fundstelle; Gegenstueck zu `MJ001`).
- `KZF161` (warning): Hinweis pro `$$...$$`-Formel -- sie wird korrekt gesetzt, im Kurzentwurf aber im Fliesstext (wie `$...$`) statt als eigene, zentrierte Formelzeile.
- `KZF200` (error): PyMuPDF ist nicht verfuegbar -- PDF-Vorschau kann nicht gerendert werden.
- `KZF220` (error): Dokument enthaelt keine renderbaren Phasen/Zeilen.

## Schilder (SBW)

Diagnosen des Schilder-Dokumenttyps (`.sbw`, `app/core/schild_validator.py`,
Einstiegspunkt `inspect_schild_text(...)`). Der Renderer ist tolerant; der Validator macht
sichtbar, was er stillschweigend ueberspringt oder ersetzt.

- `SBW001` (error): Das Dokument enthaelt kein einziges Schild.
- `SBW002` (warning): Auf einen `---`-Trenner folgt ein leeres Schild (doppelter oder abschliessender Trenner); mit Zeilennummer des Trenners.
- `SBW003` (warning): Ungueltiger Wert fuer `ausrichtung`, `fett`, `schriftgroesse` oder `rand` (0-80 mm) -- es gilt der Standardwert.

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
