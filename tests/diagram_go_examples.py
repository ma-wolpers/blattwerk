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

GO_ER_DIAGRAM = """\
entität Klasse
    __Bezeichnung__
    Klassenraum
entität Schueler
    __Name__
    __Vorname__
    __Geburtsdatum__
    Wohnort
entität Unterricht
    __ID__
    Schuljahr
entität Lehrer
    Nachname
    Vorname
    __Kuerzel__
entität Fach
    Fachname
    __Abkuerzung__
Klasse 1 - gehoertZu - n Schueler
    seitSchuljahr
Schueler 1 - istPateVon - 1 Schueler
Klasse 1 - hat - n Unterricht
Unterricht n - bei - 1 Lehrer
Unterricht n - in - 1 Fach
Lehrer n - unterrichtet - m Fach
"""

GO_DFA = ("a, b, c", """\
start -> S0
ende: S1
S0 -> S0: a, b
S0 -> S1: c
S1 -> S1: a, b
S1 -> F: c
F -> F: a, b, c
""")

GO_MEALY = ("a, b, c", "A, B", """\
start -> N
N -> N: c / eps
N -> F: b / B
N -> X: a / A
X -> X: c / eps
X -> F: b / AB
X -> F: a / AA
F -> F: a / eps
F -> F: b / eps
F -> F: c / eps
""")

GO_PUSHDOWN = ("a, b, c", "A, B, #", """\
start -> q0
ende: q3
q0 -> q1: (#, a) : #
q1 -> q1: (#, a) : A#
q1 -> q1: (#, b) : B#
q1 -> q1: (A, a) : AA
q1 -> q1: (B, b) : BB
q1 -> q1: (B, a) : AB
q1 -> q1: (A, b) : BA
q1 -> q2: (A, eps) : A
q1 -> q2: (B, eps) : B
q2 -> q2: (A, a) : eps
q2 -> q2: (B, b) : eps
q2 -> q3: (#, eps) : #
""")
