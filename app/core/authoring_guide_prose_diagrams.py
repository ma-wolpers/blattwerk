"""Redaktionelle Prosa der Diagrammblöcke, gemergt in `authoring_guide_prose.PROSE_SECTIONS`."""

# line-limit: data-only
from __future__ import annotations

DIAGRAM_PROSE_SECTIONS: dict[str, str] = {
    "block:probabilitytree": (
        "Baumdiagramm für Wahrscheinlichkeiten: Ergebnisse eingerückt, die Wahrscheinlichkeit hinter dem "
        "Doppelpunkt, als `1/3`, `0,5` oder `50%`. Blattwerk rechnet nach, ob die Äste einer Verzweigung "
        "zusammen 1 ergeben. Lücken: `%{1/3}` bei einem Wert, `%` am Zeilenanfang für den ganzen Ast."
    ),
    "block:termtree": (
        "Rechenbaum aus einem getippten Term wie `(3+4)*2`, eine Zeile pro Term. Er zeigt die "
        "Rechenreihenfolge, die Ergebnisse berechnet Blattwerk exakt. `·`, `:` und `^` gehen ebenfalls."
    ),
    "block:termtree.gaps": (
        "Was im Arbeitsblatt offen bleibt: `results` (Zwischenergebnisse), `leaves` (Zahlen), `all` oder `none`."
    ),
    "block:timeline": (
        "Zeitstrahl mit einem Ereignis pro Zeile: `1789: Französische Revolution`, auch `44 v. Chr.: Caesar` "
        "oder `14.07.1789: Sturm auf die Bastille`. `%` am Zeilenanfang blendet den Text im Arbeitsblatt aus, "
        "die Marke bleibt."
    ),
    "block:timeline.scale": ("`even` verteilt die Ereignisse gleichmäßig, `proportional` maßstäblich."),
    "block:chart": (
        "Statistikdiagramme aus kurzen Datenzeilen. `%` am Zeilenanfang lässt einen Wert im Arbeitsblatt "
        "weg. Beim Boxplot sind die Quartile die Mediane der unteren und oberen Hälfte ohne den Median, "
        "die übliche Schulmethode."
    ),
    "block:chart.type": (
        "`bar` (`Äpfel: 12`), `pie` (`Äpfel: 12`, Anteile werden berechnet), `box` (`8a: 3, 5, 7`, "
        "Rohdaten), `histogram` (`0-10: 4`) oder `scatter` (`1,5; 3`)."
    ),
    "block:chart.gaps": ("`values` blendet nur die Zahlen aus, Balken und Sektoren bleiben stehen."),
    "block:venn": (
        "Venn-Diagramm für 2 oder 3 Mengen, eine Zeile pro Bereich: `A: 2, 4`, `A B: 6`, `rest: 9` außerhalb "
        "aller Mengen. Blattwerk prüft, dass jedes Element nur in einem Bereich steht. Lücken: `%{6}` oder "
        "`%` am Zeilenanfang."
    ),
    "block:venn.variant": (
        "`compare` macht daraus einen Schreibrahmen mit größeren Feldern, zum Beispiel `Hund: bellt` und "
        "`Hund Katze: Haustier`."
    ),
    "block:arrowdiagram": (
        "Pfeildiagramm für Relationen, Zuordnungen und Funktionen: `1 -> 2`. `3 -> _` zeigt ein Element ohne "
        "Pfeil, `_ -> 4` eines auf der rechten Seite. `%` am Zeilenanfang lässt den Pfeil im Arbeitsblatt weg."
    ),
    "option:left": ("Überschrift der linken Seite."),
    "option:right": ("Überschrift der rechten Seite."),
    "block:arrowdiagram.kind": ("`function` prüft, dass jedes Element links genau einen Pfeil hat."),
    "block:fractions": (
        "Brüche als Kreise oder Balken mit gefärbten Teilen, eine Zeile pro Bruch: `3/4`. `5/4` zeigt mehrere "
        "Ganze. `%` am Zeilenanfang lässt Färbung und Zahl im Arbeitsblatt offen."
    ),
    "block:fractions.shape": ("Form: `circle` oder `bar`."),
    "block:fractions.filled": ("`false` lässt alle Teile leer, zum Selbstausmalen."),
    "block:memorydiagram": (
        "Speicherbild, um Code nachzuvollziehen: `reihung r: 3, 5, 7` mit Indizes, `variable x: 5`, "
        "`referenz p -> r` (auch `-> null`), `stapel s: 1, 2` mit dem letzten Wert oben und `schlange q: 1, 2`. "
        "Lücken: `%{5}` oder `%` am Zeilenanfang."
    ),
    "block:flowchart": (
        "Flussdiagramm für logische Abläufe, mit genau derselben Syntax wie `structogram`: Derselbe Text "
        "lässt sich als beide Diagramme darstellen. Bedingungen und Schleifen werden zu Rauten, Anweisungen "
        "zu Rechtecken, dazu Start- und Endmarke. `signature=` ist hier freiwillig."
    ),
    "block:sequencediagram": (
        "Sequenzdiagramm aus kurzen Zeilen: `A -> B: Nachricht` für einen Aufruf, `A --> B: Antwort` für "
        "die gestrichelte Rückgabe, `A -> A: Text` an sich selbst. Die Teilnehmer erscheinen in der "
        "Reihenfolge ihres Auftretens, `teilnehmer B` am Anfang legt sie fest. Lücken: `%{Nachricht}`."
    ),
    "block:syntaxdiagram": (
        "Syntaxdiagramme aus EBNF-ähnlichen Zeilen wie `Zahl = [ \"-\" ] Ziffer { Ziffer }`. `\"x\"` ist ein "
        "Terminal (rund), ein Name ein Nichtterminal (eckig), `|` trennt Alternativen, `[ … ]` ist optional, "
        "`{ … }` wiederholt sich, `( … )` gruppiert."
    ),
    "block:logicgates": (
        "Logikschaltung aus einer Formel wie `Q = (A und B) oder nicht C`, mit `und`, `oder`, `xoder`, "
        "`nand`, `nor` und `nicht`. Kommt eine Variable mehrfach vor, erscheint sie je Vorkommen als eigener "
        "Eingang."
    ),
    "block:logicgates.norm": ("Symbole: `iec` (rechteckig, Standard) oder `ansi` (geschwungen)."),
    "block:logicgates.truthtable": ("Ergänzt die aus der Formel berechnete Wahrheitstabelle."),
    "block:logicgates.gaps": ("Lässt die Ergebnisspalte der Wahrheitstabelle im Arbeitsblatt offen."),
    "block:graph": (
        "Graph oder Baum aus kurzen Zeilen, zum Beispiel für Graphalgorithmen: `A - B: 5` ist eine "
        "ungerichtete Kante mit Gewicht, `A -> B: 5` eine gerichtete, `A` allein ein einzelner Knoten. Die "
        "Anordnung entsteht automatisch, ein Baum wird als Baum gezeichnet. Lücken: `%{5}` beim Gewicht."
    ),
    "block:graph.layout": ("Anordnung: `auto` (Baum als Baum, sonst frei), `tree` oder `circle`."),
    "block:graph.binary": (
        "Liest die Kanten als Binärbaum: Die Kinder gelten in Zeilenreihenfolge als links und rechts, ein "
        "einzelnes Kind ist das linke, `8 - _` lässt das linke Kind frei."
    ),
    "block:networkdiagram": (
        "Netzwerkplan mit einfachen Symbolen aus kurzen Verbindungszeilen: `PC1 - Switch - Router`. Das "
        "Symbol ergibt sich aus dem Namensanfang (`PC`, `Laptop`, `Tablet`, `Handy`, `Switch`, `Router`, "
        "`WLAN`, `Server`, `Internet`, `Drucker`); `Kasse1: rechner` setzt es ausdrücklich."
    ),
    "block:erdiagram": (
        "ER-Diagramm in der Gestalt der zentralen Prüfungsaufgaben (GO Informatik, S. 8). `entität Name` "
        "beginnt eine Entität, die eingerückten Zeilen sind ihre Attribute; `__Name__` unterstreicht ein "
        "Schlüsselattribut. Beziehungen stehen in kurzen Zeilen wie beim Klassendiagramm: "
        "`Klasse 1 - gehoertZu - n Schueler`, eingerückte Zeilen darunter sind Attribute der Beziehung. "
        "Rekursive Beziehungen schreibt man `Schueler 1 - istPateVon - 1 Schueler`. Die Anordnung entsteht "
        "automatisch. Lücken: `%` nach der Einrückung bei Attributen, `%{1}` bei Kardinalitäten."
    ),
    "block:statediagram": (
        "Automaten in der Gestalt der zentralen Prüfungsaufgaben (GO Informatik, S. 12): eine kurze Zeile "
        "pro Übergang, `S0 -> S1: c`. `start -> S0` setzt den Startzustand, `ende: S1, S2` die Endzustände. "
        "Mehrere Übergänge zwischen denselben Zuständen teilen sich eine Kante mit gestapelter Beschriftung. "
        "`S0` erscheint als tiefgestellter Index, `eps` als ε. Lücken: `%{c}` in der Beschriftung."
    ),
    "block:statediagram.kind": (
        "Prüft die Notation aus der GO: `dfa` und `mealy` verlangen von jedem Zustand genau einen Pfeil je "
        "Eingabezeichen (Mealy schreibt `Eingabe / Ausgabe`), `pda` schreibt `(oben, Eingabe) : Kellerwort`. "
        "Ohne `input` ergibt sich das Alphabet aus den Pfeilen."
    ),
    "block:statediagram.input": ("Eingabealphabet, z. B. `input=\"a, b, c\"`, erscheint als Zeile über dem Graphen und wird mit den Pfeilen abgeglichen."),
    "block:statediagram.output": ("Ausgabealphabet eines Mealy-Automaten, erscheint als Zeile über dem Graphen und wird mit den Pfeilen abgeglichen."),
    "block:statediagram.stack": ("Kelleralphabet eines Kellerautomaten, erscheint als Zeile über dem Graphen und wird mit den Pfeilen abgeglichen."),
    "block:classdiagram": (
        "Klassendiagramm und Objektkarten in der Gestalt der zentralen Prüfungsaufgaben (Ergänzende "
        "Hinweise zur GO Informatik, S. 7). `klasse Name` beginnt eine Klasse, die eingerückten Zeilen "
        "darunter sind ihre Attribute und Operationen: `- id: Ganzzahl`, `+ getName(): Zeichenkette`, "
        "`c Person()` für Konstruktoren, `...` für nicht aufgeführte Mitglieder. Zeilen mit Klammern oder "
        "`c` zählen als Operationen. Beziehungen stehen in kurzen Zeilen: `Schueler -|> Person` für "
        "Vererbung (der Pfeil zeigt zur Oberklasse), `Person - Adresse` für eine Assoziation, auch "
        "`Person - Person`. `objekt p42 : Person` beginnt eine Objektkarte mit eingerückten Belegungen "
        "wie `id = 123`. Die Anordnung entsteht automatisch. Lücken: `%` nach der Einrückung blendet eine "
        "Zeile im Arbeitsblatt aus, der Platz bleibt erhalten; `%{…}` wirkt auf Teiltexte."
    ),
    "block:structogram": (
        "Struktogramm in der Gestalt der zentralen Prüfungsaufgaben (Ergänzende Hinweise zur GO "
        "Informatik, S. 5-6). Eine Zeile ist ein Element, die Einrückung (4 Leerzeichen oder Tab) "
        "die Schachtelung. Schlüsselwörter am Zeilenanfang: `wenn B` (+ optional `sonst`) für die "
        "Verzweigung, `auswahl A` mit `fall W`-Zeilen (+ optional `sonst`) für die Mehrfachauswahl, "
        "`solange …`/`für …`/`wiederhole 100-mal` für kopfgesteuerte Schleifen, `wiederhole` allein "
        "+ Rumpf + `bis B` für die fußgesteuerte Schleife, `rückgabe X` (angezeigt als „gib X "
        "zurück“) und `eingabe x` (angezeigt als „lies x ein“). Jede andere Zeile ist eine "
        "Anweisung; `<-` wird als `←` gesetzt, `//`-Kommentare bleiben Text, `\\` am Zeilenanfang "
        "hebt ein Schlüsselwort auf. Lücken-Struktogramm: `%` nach der Einrückung blendet den Text "
        "eines Elements im Arbeitsblatt aus (Struktur bleibt, Zelle bleibt mindestens so hoch wie in "
        "der Lösung), `%{…}` einen Teiltext. Der Validator prüft Struktur, Signatur und ob "
        "Rückgaben, Rückgabetyp und Parameter zueinander passen."
    ),
    "option:signature": (
        "Methodenkopf in GO-Notation `Bezeichnung(Parameter: Typ, ...): Rückgabetyp`, fett über "
        "dem Diagramm, z. B. `signature=\"minimum(a, b: Fließkommazahl): Fließkommazahl\"`. "
        "Parameter ohne eigenen Typ gehören zur nächsten getypten Gruppe; ohne Rückgabewert "
        "entfällt `: Rückgabetyp`. Wird streng geprüft; fehlt die Option bei `structogram`, gibt es eine Warnung, bei `flowchart` ist sie freiwillig."
    ),
}
