"""Redaktionelle Prosa der Diagrammblöcke, gemergt in `authoring_guide_prose.PROSE_SECTIONS`."""

# line-limit: data-only
from __future__ import annotations

DIAGRAM_PROSE_SECTIONS: dict[str, str] = {
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
        "Prüft die Notation aus der GO: `dfa` (je Zustand und Zeichen genau ein Übergang), `mealy` "
        "(`Eingabe / Ausgabe`), `pda` (`(oben, Eingabe) : Kellerwort`). Ohne Angabe keine Prüfung."
    ),
    "block:statediagram.input": ("Eingabealphabet, z. B. `input=\"a, b, c\"`, erscheint als Zeile über dem Graphen."),
    "block:statediagram.output": ("Ausgabealphabet eines Mealy-Automaten, erscheint als Zeile über dem Graphen."),
    "block:statediagram.stack": ("Kelleralphabet eines Kellerautomaten, erscheint als Zeile über dem Graphen."),
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
    "block:structogram.signature": (
        "Methodenkopf in GO-Notation `Bezeichnung(Parameter: Typ, ...): Rückgabetyp`, fett über "
        "dem Diagramm, z. B. `signature=\"minimum(a, b: Fließkommazahl): Fließkommazahl\"`. "
        "Parameter ohne eigenen Typ gehören zur nächsten getypten Gruppe; ohne Rückgabewert "
        "entfällt `: Rückgabetyp`. Wird streng geprüft; fehlt die Option, gibt es eine Warnung."
    ),
}
