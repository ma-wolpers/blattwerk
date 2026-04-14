# Blattwerk Grammar (Canonical)

Diese Datei definiert die kanonische Grammatik fuer Blattwerk-Markdown.
`docs/MD_FORMAT.md` bleibt die normative Fachreferenz; diese Datei fokussiert die formale Sprache.

## 1. Lexer-Ebene (vereinfacht)

- `FRONTMATTER_DELIM` := `---` am Zeilenanfang
- `BLOCK_OPEN` := `:::` gefolgt von Blockname und optionalen Optionen
- `BLOCK_CLOSE` := `:::` auf eigener Zeile
- `SECTION_BREAK` := `---` oder `--` ausserhalb des Frontmatters
- `SELF_CLOSING_BLOCK` := `:::name ... :::`

Hinweise:
- Optionen werden als `key=value` gelesen; Trennzeichen ist Leerraum.
- Alles ausserhalb erkannter Bloecke bleibt Raw-Markdown.

## 2. Dokument-Grammatik (EBNF-nahe)

```ebnf
document          = frontmatter, newline*, element* ;
element           = block | self_closing_block | section_break | raw_markdown ;

frontmatter       = delim, newline, yaml_lines, delim, newline* ;
delim             = "---" ;
section_break     = ("---" | "--"), newline ;

block             = block_open, block_content, block_close ;
block_open        = ":::", ws?, block_name, (ws, options)?, newline ;
block_close       = ":::", newline? ;
self_closing_block= ":::", ws?, block_name, (ws, options)?, ws?, ":::", newline? ;

options           = option, (ws, option)* ;
option            = key, "=", value ;
key               = identifier ;
value             = non_whitespace_token ;

block_name        = "material"
                  | "info"
                  | "task"
                  | "subtask"
                  | "lines"
                  | "grid"
                  | "dots"
                  | "space"
                  | "table"
                  | "numberline"
                  | "mc"
                  | "cloze"
                  | "matching"
                  | "wordsearch"
                  | "solution"
                  | "columns"
                  | "nextcol"
                  | "endcolumns"
                  | "help"
                  | "hilfe" ;
```

## 3. Strukturelle Regeln

- Frontmatter ist verpflichtend.
- Pflichtfelder im Frontmatter: `Titel`, `Fach`, `Thema`.
- `subtask` ist nur als Folgeblock zu einem vorherigen `task` gueltig (nicht geschachtelt).
- Sichtbarkeit ist nur ueber `show=worksheet|solution|both` definiert.
- Legacy-Syntax `:::answer type=...` ist ungueltig; Antwortflaechen werden nur noch ueber dedizierte Blocktypen beschrieben.
- YAML-basierte Antwort-Blocktypen (`grid`, `numberline`, `table`, `matching`) erwarten Mapping-YAML als Inhalt.
- In Grid-YAML (`points`, `pairs`, `functions`) ist Element-Sichtbarkeit nur als `show: "§"|"%"|"&"` erlaubt.
- In Numberline-YAML (`labels`, `answers`, `arcs`) ist Element-Sichtbarkeit nur als `show: "§"|"%"|"&"` erlaubt.
- In textbasierten Antwort-Blockinhalten sind zwei Marker-Varianten erlaubt:
    - Legacy-Zeilenmarker als eigenes Token am Zeilenanfang/-ende:
        - `§` -> worksheet
        - `%` -> solution
        - `&` -> both
    - Inline-Token fuer Teilbereiche einer Zeile:
        - `§{...}` -> nur Arbeitsblatt
        - `%{...}` -> nur Loesung
        - `&{...}` -> Arbeitsblatt und Loesung
- Text ohne Token ist standardmaessig in beiden Modi sichtbar.
- Escape-Sequenzen fuer Literale: `\%\{`, `\§\{`, `\&`, `\}`.
- Syntaxkonflikte (`AN006`) entstehen bei ungeschlossenen Inline-Tokens (z. B. `%{Text`) oder bei Legacy-Markern gleichzeitig am Zeilenanfang und -ende.

## 4. Kanonische Werte (Auszug)

- `work`: `single|partner|group` (+ dokumentierte Aliase)
- `action`: `exchange|decide|experiment|reflect|read|calculate|match|write|draw` (+ dokumentierte Aliase)
- `hint`: `tip|definition|remember|term|expert` (+ dokumentierte Aliase)
- `show` (Blockoption): `worksheet|solution|both`
- Grid-/Numberline-Elemente in YAML: `show: "§"|"%"|"&"`

Die vollstaendige Optionsmatrix und Aliasliste steht in `docs/MD_FORMAT.md`.

## 5. Diagnose-Codes und Stabilitaet

Der Validator liefert stabile, oeffentliche Codes (z. B. `FM001`, `BL001`, `OP001`, `OP002`, `AN003`, `AN004`, `AN008`, `AN009`).
Neue Codes duerfen nur additiv eingefuehrt werden; bestehende Codes bleiben stabil.
