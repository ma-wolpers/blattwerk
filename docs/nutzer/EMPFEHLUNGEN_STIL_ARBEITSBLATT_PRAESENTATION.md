# Stilempfehlungen: Arbeitsblatt & Präsentation

Dieses Dokument sammelt reine Autor:innen-Stilpräferenzen für den `:::`-Blockdialekt --
im Unterschied zu [`docs/nutzer/ANLEITUNG_ARBEITSBLATT_PRAESENTATION.md`](ANLEITUNG_ARBEITSBLATT_PRAESENTATION.md)
handelt es sich hier **nicht** um Regeln, die der Validator durchsetzt oder die für ein
korrekt funktionierendes Dokument nötig sind. Nichts hier ist "falsch", wenn man es
anders macht -- es ist einfach die empfohlene Schreibweise für konsistente, gut lesbare
Blattwerk-Quelltexte.

Nicht codegeneriert (rein redaktionell) und nicht Teil der `assert_prose_coverage`-Prüfung.

## Kompakte Schreibweise für inhaltslose Blöcke

Blöcke ohne Inhalt (`nextcol`, `endcolumns`, `pagebreak`-artige Marker o. ä.) auf einer
einzigen Zeile schreiben, öffnendes und schließendes `:::` zusammen:

```markdown
:::nextcol :::
```

statt der mehrzeiligen Form

```markdown
:::nextcol
:::
```

Beide Formen sind vom Parser gleichwertig akzeptiert (siehe Grundregel in der
Hauptanleitung) -- die einzeilige Form ist einfach kompakter und macht auf einen Blick
sichtbar, dass hier bewusst kein Inhalt folgt.

## Immer den passendsten Blocktyp wählen

Blattwerk hat für die meisten Aufgabentypen einen dedizierten Blocktyp -- diesen nutzen,
statt ihn mit einem generischeren Block nachzubauen. Zum Beispiel:

- Multiple-Choice-/Wahr-Falsch-Fragen → `:::mc`, nicht `:::task` mit handgeschriebener Liste.
- Zuordnungsaufgaben → `:::matching`, nicht `:::table` mit zwei Spalten.
- Lückentexte → `:::cloze`, nicht `:::task` mit Freitext-Lücken.
- Mehrteilige a)/b)/c)-Aufgaben → mehrere `:::subtask`-Blöcke direkt nach dem `:::task` (werden automatisch gelettert), nicht eine handgeschriebene Liste (`- a) ... b) ...`) innerhalb eines einzelnen `:::task`-Blocks.

Die dedizierten Blocktypen bringen automatisches Layout, konsistente Lösungsdarstellung
und (wo zutreffend) Validierung mit -- ein nachgebauter Block über einen generischeren
Typ verliert diese Vorteile, auch wenn er optisch ähnlich aussehen mag.

## `:::task` nur für echte Arbeitsaufträge

`:::task` sollte reserviert bleiben für das, was SuS tatsächlich tun sollen (lesen,
schreiben, entscheiden, ausprobieren, ...). Reine Übersichten, Ablaufzusammenfassungen
oder Zwischenansagen ohne eigene Handlung sind kein Arbeitsauftrag und gehören in
`:::info` (oder `:::material`, wenn es sich um Kontext/Beispielmaterial vor einer
Aufgabe handelt). Besonders relevant in Präsentationen: eine Folie wie "Unser Ablauf"
oder "Weiter geht's mit Arbeitsblatt 3" ist eine Übersicht, kein Auftrag -- auch wenn
sie wie ein `:::task` aussehen könnte, weil sie in einer Aufgaben-lastigen Präsentation
steht. Faustregel: Steht in der Folie ein Verb, das SuS jetzt konkret ausführen sollen
("Lest", "Notiert", "Diskutiert"), ist es `:::task`. Steht dort nur, was gerade passiert
oder was als Nächstes kommt, ist es `:::info`.

## Präsentationsfolien nur mit Inhalt, der nicht mündlich ersetzbar ist

Eine Folie sollte nur enthalten, was die Lehrkraft nicht ohnehin selbst mündlich sagen
kann/würde, oder was SuS später noch einmal nachlesen wollen (Definitionen, Graphen,
konkrete Aufgabentexte, Tabellen zum Ausfüllen). Reine Moderations-/Ablaufschritte, die
live angesagt werden ("Vergleicht jetzt in der Klasse", "Wir sichern das Ergebnis"),
gehören **nicht** als eigener Block in die Folie -- auch nicht als `:::info`. Das ist
eine Stufe strenger als die vorherige Regel: Dort geht es darum, *welcher Blocktyp*
richtig ist, wenn etwas auf der Folie steht; hier geht es darum, ob der Moderationsschritt
überhaupt als Folieninhalt nötig ist. Solche Schritte gehören höchstens in den eigenen
Kurzentwurf/Sequenzplan der Lehrkraft, nicht in die Schüler:innen-Präsentation.

## Graph + Erklärtext: 2-Spalten-Layout

Folien, die einen `:::geometry`-Graphen zusammen mit begleitendem Erklärtext
(`:::material`, `:::info`, ...) zeigen, als `:::columns cols=2 widths="1 1" :::` aufbauen:
Graph in der ersten Spalte, Text in der zweiten Spalte -- nicht Text unter dem Graphen
anordnen.

## Zusammengehörige Aufgabe und Tabelle nicht durch Folienwechsel trennen

Wenn eine `:::task`-Aufgabe und eine direkt dazugehörige Tabelle/Antwortstruktur (SuS
sollen dort unmittelbar eintragen, was die Aufgabe verlangt) inhaltlich eine Einheit
bilden, beide auf derselben Folie belassen -- keinen `--!`-Folienwechsel dazwischensetzen.
`--!` bleibt reserviert für inhaltlich neue Schritte/Phasen.

## Kein Doppelpunkt zwischen Formeln

Steht ein `:` unmittelbar neben einer `$formel$` (davor oder danach direkt angrenzend),
verschmilzt er beim Rendern optisch mit der Formel -- er sieht dann aus, als gehöre er
zur Formel selbst. Beispiel: `für $n=-4$: $3n+8=$` liest sich auf den ersten Blick wie
`$n=-4:3n+8=$`. Stattdessen umformulieren, sodass zwischen Doppelpunkt und Formel(n)
immer normaler Fließtext steht -- oder den Doppelpunkt ganz weglassen:
`für $n=-4$ den Term $3n+8=$`, `$x$ aus der Gleichung $5x=45$`.

## Operator-Passung vor dem Einsetzen prüfen

Der Pflicht-Operator (`!!Operator!!`, ab Oberstufe siehe `ARBEITSBLATT_NOTIZEN.md`)
muss zur Aufgabe auch inhaltlich passen -- die Pflicht, überhaupt einen offiziellen
Operator zu verwenden, ist kein Freibrief, einen unpassenden zu erzwingen. Beispiel:
`!!Bestimme!! $r$` bei einer Gleichung mit zwei Variablen (z. B. `$r-3=s+2$`) klingt nach
einem eindeutigen Zahlenwert, obwohl das Ergebnis ein Term in Abhängigkeit von der
zweiten Variable ist -- hier zusätzlich `in Abhängigkeit von $s$` ergänzen, damit der
Operator nicht in die Irre führt. Passt kein Operator der offiziellen Liste inhaltlich
(z. B. bei rein mechanischen Instruktionen wie "kürzen"), die Formulierung frei lassen
(ggf. **fett** statt `!!...!!`), statt einen unpassenden Operator zu erzwingen oder die
Anweisung ganz ohne Verb zu lassen.
