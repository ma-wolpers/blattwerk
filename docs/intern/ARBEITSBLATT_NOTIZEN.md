# Arbeitsblatt-Notizen (Praxis)

Diese Datei sammelt feste Standards für Arbeitsblätter, die bei der Inhaltserstellung meistens gelten sollen.

## Formatstandards

- Keine Kopfzeile für Name, Klasse, Datum: `show_student_header: false`
- Aufgaben ohne Punkte: bei `:::task` kein Parameter `points`
- Operatoren in Aufgaben fett setzen, z. B. **Beschreibt**, **Vergleicht**, **Begründet**
- Umlaute konsequent verwenden (ä, ö, ü, Ä, Ö, Ü, ß), nicht als ae/oe/ue umschreiben
- Zwischen zwei Hauptaufgaben (und generell überall, was nicht zwingend auf derselben Seite stehen muss) `--` als Trenner setzen – NICHT `---` (das fügt zusätzlich 1cm Abstand ein und ist eigentlich nur eine normale Markdown-Trennlinie, kein Blattwerk-Kontrollmarker). Ausnahmen: zwischen einer Aufgabe und ihrem direkt zugehörigen `:::material` sowie innerhalb von `:::columns`/`:::nextcol`/`:::endcolumns`-Konstrukten keinen Trenner einfügen.

## Speicherort

Alle Arbeitsblätter in `Material` speichern, am besten in einem Unterordner mit dem Titel der Unterrichtseinheit, z. B. `Material/Hardware`

## Check vor Export

1. Sind alle Operatoren fett gesetzt?
2. Sind Umlaute korrekt geschrieben?
3. Gibt es Trenner `--` (nicht `---`) zwischen den Hauptaufgaben?
4. Ist die Schülerkopfzeile aktiviert?
5. Enthalten Aufgaben Punkte?

## Aufgabendesign

- Definitions-/Begriffsübungen (Kreuzworträtsel, Zuordnungen, Lückentexte, ...) sollen verschiedene mathematische Darstellungsformen mischen (Gleichung, Graph, Zuordnung/Symbolik), nicht nur eine Perspektive (z. B. nur Alltagssprache) – sonst wird Wiedererkennen statt echtes Definitionsverständnis geprüft.
- `:::matching`-Aufgaben dürfen nie positionsoffensichtlich sein: die rechte/untere Liste so mischen, dass `matches` nicht `1-1, 2-2, 3-3, ...` ist – sonst lässt sich rein über die Position lösen, ohne den Inhalt zu verstehen.
- Bei Antwortmöglichkeiten und Beschriftungen (Labels an Graphen/Geometrien, Matching-Texten, MC-Optionen) immer prüfen, wie offensichtlich sie die Lösung verraten. Kein pauschales Label-Verbot, aber: ein Label, das den gesuchten Fachbegriff schon im Text nennt (z. B. ein markierter Punkt mit Label "Nullstelle" in einer Aufgabe, die genau das erkennen lassen soll), macht die Aufgabe trivial.
- Sachaufgaben/Modellierungskontexte wo möglich mit konkreten Zahlen/Daten ausstatten statt abstrakter Prosa ohne Werte – das macht sie weniger abstrakt und leichter zugänglich.
- Ein Codewort bei `:::crossword` (`code=`) ist meistens ein sinnvolles Extra.
- `:::selfcheck`-/Reflexionsblöcke müssen zu den tatsächlich umgesetzten Aufgaben passen, nicht zu ursprünglich geplanten Zielen – bei nachträglichen Änderungen am Blatt immer auch die Selbsteinschätzung nachziehen.
- Ab der Oberstufe: Aufgaben-Operatoren nach der offiziellen Abitur-Operatorenliste verwenden (exakt wie dort definiert), statt freier Fragen zu formulieren. *(Liste noch zu ergänzen/verlinken.)*
- Kurze, viele Teilaufgaben (z. B. kurze Rechenaufgaben) dürfen zum Platzsparen in `:::columns` gesetzt werden – aber **pro Zeile ein eigener `:::columns`/`:::endcolumns`-Block**, nicht mehrere Teilaufgaben in einer Spalte gestapelt. Grund: Stapelt man z. B. a+b in Spalte 1 und c+d in Spalte 2 innerhalb *eines* columns-Blocks, verschiebt eine unterschiedlich hohe Aufgabe a die y-Position von c in der Nachbarspalte – jede Zeile braucht also ihren eigenen, in sich abgeschlossenen columns-Block, damit sie unabhängig von der Höhe der Zeile darüber sauber ausgerichtet bleibt. Außerdem nicht zu viele Spalten auf einmal (bei kurzen Termen/Brüchen wird es schnell zu eng) – in der Praxis meist `cols=2`, selten mehr.
