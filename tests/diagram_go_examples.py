"""Referenzbeispiele aus den Ergänzenden Hinweisen zur GO Informatik, in Blattwerk-Syntax.

Quelle: S. 7 (Klassendiagramm, Objektkarten), S. 8 (ER-Diagramm), S. 12 (Automaten).
Nur die Struktur der Beispiele, gemeinsam genutzt von Tests und Sichtprüfung.
"""

GO_CLASS_DIAGRAM = """\
klasse Person
    - id: Ganzzahl
    - name: Zeichenkette
    - adresse: Adresse
    - bekannte: stat. Reihung vom Inhaltstyp Person
    ...
    c Person()
    c Person(name: Zeichenkette)
    + getName(): Zeichenkette
    + kennt(anderer: Person): Wahrheitswert
    ...
klasse Adresse
    - strasse: Zeichenkette
    - plz: Zeichenkette
    - ort: Zeichenkette
    c Adresse(a_str, a_plz, a_ort: Zeichenkette)
    + alsText(): Zeichenkette
    ...
klasse Schueler
    - jahrgang: Ganzzahl
    c Schueler()
    + getJahrgang(): Ganzzahl
    + setJahrgang(jg: Ganzzahl)
klasse Lehrer
    - faecher: dyn. Reihung vom Inhaltstyp Zeichenkette
    ...
    c Lehrer()
    + addFach(fach: Zeichenkette)
    ...
Schueler -|> Person
Lehrer -|> Person
Person - Adresse
Person - Person
objekt p42 : Person
    id = 123456789
    name = "Max Mustermann"
    adresse = adr37
    bekannte = [p12, p44, p52]
    ...
objekt adr37 : Adresse
    strasse = "Turingstraße 42"
    plz = "12345"
    ort = "Bletchley"
"""
