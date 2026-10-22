"""Die vier Struktogramm-Beispiele der GO Informatik (Ergänzende Hinweise, S. 5–6) als Testdaten.

Jeder Eintrag: `(signature, content)` in `:::struktogramm`-Syntax. Gemeinsame
Quelle für Parser-, Validator- und Rendering-Tests -- alle vier müssen ohne
jede Diagnose durchlaufen, weil sie die normative Vorlage des Blocks sind.
"""

# line-limit: data-only

GO_EXAMPLE_1 = (
    "istEnthalten(d: dyn. Reihung vom Inhaltstyp Ganzzahl, v: Ganzzahl): Wahrheitswert",
    "für alle Elemente e aus d\n"
    "    wenn e = v\n"
    "        rückgabe wahr\n"
    "rückgabe falsch\n",
)

GO_EXAMPLE_2 = (
    "anzahlZeichen(s: Stapel vom Inhaltstyp Zeichen): stat. Reihung vom Inhaltstyp Ganzzahl",
    "anzahl <- stat. Reihung der Länge 27 vom Inhaltstyp Ganzzahl, deren Elemente mit 0 initialisiert sind\n"
    "solange s nicht leer\n"
    "    v <- entnimm Element aus s\n"
    "    w <- ASCII-Wert von v\n"
    "    wenn w = 32  // v ist ein Leerzeichen\n"
    "        erhöhe anzahl[0] um 1\n"
    "    sonst\n"
    "        erhöhe anzahl[w-64] um 1\n"
    "rückgabe anzahl\n",
)

GO_EXAMPLE_3 = (
    "erzeugePixel(): dynamische Reihung vom Inhaltstyp Pixel",
    "f <- leere dynamische Reihung vom Inhaltstyp Pixel\n"
    "solange f nicht leer\n"
    "    lösche Element an Position 0 von f\n"
    "anzahlRot <- 0\n"
    "wiederhole\n"
    "    wiederhole 100-mal\n"
    "        z <- ganzzahlige Zufallszahl zwischen 1 und 4\n"
    "        auswahl z ist gleich\n"
    "            fall 1\n"
    "                p <- erzeuge Pixel(255,0,0)\n"
    "                anzahlRot <- anzahlRot + 1\n"
    "            fall 2\n"
    "                p <- erzeuge Pixel(0,255,0)\n"
    "            fall 3\n"
    "                p <- erzeuge Pixel(0,0,255)\n"
    "            fall 4\n"
    "                p <- erzeuge Pixel(120,75,250)\n"
    "            sonst\n"
    "        füge p zu f hinzu\n"
    "bis anzahlRot > 30\n"
    "rückgabe f\n",
)

GO_EXAMPLE_4 = (
    "istEnthalten(b: Binärbaum vom Inhaltstyp Person, n: Zeichenkette): Wahrheitswert",
    "wenn b.isEmpty()\n"
    "    rückgabe falsch\n"
    "aktuell <- b.getItem()\n"
    "wenn aktuell.getNachname() = n\n"
    "    rückgabe wahr\n"
    "sonst\n"
    "    links <- istEnthalten(b.getLeft(), n)\n"
    "    rechts <- istEnthalten(b.getRight(), n)\n"
    "    wenn links = wahr ODER rechts = wahr\n"
    "        rückgabe wahr\n"
    "    sonst\n"
    "        rückgabe falsch\n",
)

GO_EXAMPLES = (GO_EXAMPLE_1, GO_EXAMPLE_2, GO_EXAMPLE_3, GO_EXAMPLE_4)

GO_SIGNATURES = (
    "istGerade(x: Ganzzahl): Wahrheitswert",
    "minimum(a, b: Fließkommazahl): Fließkommazahl",
    "sortiere(a: dynamische Reihung vom Inhaltstyp Zeichenkette)",
    GO_EXAMPLE_1[0],
    GO_EXAMPLE_2[0],
    GO_EXAMPLE_3[0],
    GO_EXAMPLE_4[0],
)
"""Alle sieben Signaturen von GO S. 5–6 (inkl. der drei Notationsbeispiele)."""
