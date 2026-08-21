<!--
Automatisch generiert aus app/core/markdown_conventions.py.
NICHT VON HAND BEARBEITEN.
Neu erzeugen: python tools/docs/generate_authoring_guides.py
-->

# Kurzentwurf erstellen

Kurzentwurf ist ein eigener Blattwerk-Dokumenttyp mit einer **eigenen DSL** -- nicht dem `:::`-Blockdialekt aus der Arbeitsblatt-/Präsentations-Anleitung. Diese Anleitung wird automatisch aus dem Code erzeugt (`app/core/markdown_conventions.py`). Fehlermeldungen tragen stabile Codes wie `KZF011`/`KZF152` -- die vollständige Liste steht in [`docs/VALIDATOR.md`](VALIDATOR.md#kurzentwurf-dsl-kzf).

## 1. Schnellstart

```markdown
---
document_type: kurzentwurf
Stundenthema: Neuer Kurzentwurf
Lerngruppe: Klasse eintragen
start: 08:00
Material:
    - Material eintragen
---

#einstieg t=10
S> Aktivierung von Vorwissen und Zieltransparenz.
A>
s< Erste Vermutungen formulieren.
U> Plenum; Tafel
ant< Typische Fehlannahme notieren.

---
A>
s< Schwerpunkt der Lernaktivitaet festhalten.

#erarbeitung t=20
S> Leitfrage in Teams bearbeiten.
A>
s< Arbeitsphase mit Materialanalyse und Zwischenfeedback.
U> Teamarbeit; Materialset A
```

## 2. Frontmatter/Identitäts-Metadaten

Titel, Untertitel und globale Startzeit können sowohl im YAML-Frontmatter (`---`-Block) als auch als einzelne `@title:`/`@subtitle:`/`@start:`-Metazeilen im Dokument gesetzt werden -- beide Varianten verstehen dieselben deutschen/englischen Alias-Schreibweisen (z. B. `Stundenthema` für den Titel, `Lerngruppe` für den Untertitel).

Akzeptierte Schlüssel (alle gleichwertig, case-insensitiv): `lerngruppe`, `start`, `start_time`, `startuhrzeit`, `startzeit`, `stundenthema`, `subtitle`, `title`.

## 3. Phasen

Ein Kurzentwurf gliedert sich in `#phase`-Abschnitte. Wichtig: der nach `#` getippte Hashtag ist **nicht** derselbe Text wie der Anzeigename der Phase (siehe Tabelle unten) -- z. B. heißt die Phase `Ergebnissicherung`, aber der Hashtag lautet `#sicherung`, und `Didaktische Reserve` ist `#reserve`. `t=<minuten>` gibt die Dauer der Phase an und ist optional; ohne Zeitangaben wird die Phase ohne Zeitlabel gerendert. `Hausaufgabe` und `Didaktische Reserve` benötigen nie ein `t=...` (fließen nicht in die Zeitrechnung ein). Zusätzlich gibt es `start=HH:MM` als optionales Attribut im `#phase`-Header: das steuert **nicht** die Zeitberechnung, sondern ist nur ein Plausibilitäts-Check gegen die aus `t=` fortlaufend berechnete Startzeit -- weicht `start=` davon ab, wird es ignoriert und es erscheint lediglich die Warnung `KZF136`.

| Anzeigename | Hashtag | Braucht `t=`? |
|---|---|---|
| `Einstieg` | `#einstieg` | ja |
| `Erarbeitung` | `#erarbeitung` | ja |
| `Ergebnissicherung` | `#sicherung` | ja |
| `Vertiefung` | `#vertiefung` | ja |
| `Hausaufgabe` | `#hausaufgabe` | nein |
| `Didaktische Reserve` | `#reserve` | nein |

## 4. Zeilenmarker innerhalb einer Phase

Innerhalb einer Phase gliedern Zeilenmarker den Inhalt in drei Spalten (Lernschritte/Lernaktivitäten/Lernumgebung) plus eine Antizipations-Spur -- siehe die einzelnen Marker unten. Zusätzlich: `---` allein auf einer Zeile trennt zwei Segmente innerhalb derselben Phase; `|` allein auf einer Zeile springt ohne Werteingabe zur nächsten Spalte.

- **`S>`**: Beginnt die Spalte Lernschritte; der Inhalt steht direkt hinter `S>` auf derselben Zeile.
- **`A>`**: Schaltet die aktive Spalte auf Lernaktivitäten um, trägt aber selbst **keinen** Inhalt -- Inhalt direkt hinter `A>` auf derselben Zeile ist ungültig und löst `KZF150` aus. Der eigentliche Inhalt gehört auf eine folgende `s<`-Zeile.
- **`s<`**: Lernaktivität der Lernenden -- der eigentliche Inhalt der Spalte Lernaktivitäten, folgt typischerweise auf `A>`. Inhalt in dieser Spalte vor dem ersten `s<` löst `KZF151` aus.
- **`U>`**: Beginnt die Spalte Lernumgebung/Sozialform; Inhalt direkt hinter `U>`.
- **`ant<`**: Markiert eine antizipierte Schülerreaktion/Fehlvorstellung zum jeweiligen Lernschritt und sollte nach jedem `s<` gesetzt werden -- fehlt es, erscheint die Warnung `KZF152`.
- **`ant>`**: **Kein** gültiger Alias von `ant<`, obwohl es vom Zeilenmarker-Muster erkannt wird -- führt immer zum Fehler `KZF153` ("Bitte ant< verwenden"). Nur `ant<` verwenden.

## 5. Legacy-Erkennungs-Felder (nicht aktiv verwenden)

Diese Felder werden derzeit ausschließlich zur Erkennung älterer Kurzentwurf-Dokumente berücksichtigt (falls kein explizites `document_type: kurzentwurf` gesetzt ist). Sie steuern weder Inhalt noch Darstellung des gerenderten Kurzentwurfs und sollten für neue Dokumente nicht als funktionale DSL-Felder verwendet, sondern höchstens als rein organisatorische Notiz betrachtet werden.

- **`Dauer`**: Historische Freitext-Angabe zur geplanten Stundendauer.
- **`Kompetenzen`**: Historische Freitext-Auflistung angesprochener Kompetenzen.
- **`Material`**: Historische Materialliste. Für neue Dokumente stattdessen das YAML-Frontmatter-Feld `Material` im Schnellstart-Beispiel oben verwenden (dort aktiv gerendert).
- **`Oberthema`**: Historisches Feld für ein übergeordnetes Reihenthema.
- **`Stundentyp`**: Historisches Feld für eine Stundentyp-Bezeichnung (z. B. Einführung).
- **`Stundenziel`**: Historisches Feld für das übergeordnete Stundenziel.
- **`Teilziele`**: Historische Freitext-Auflistung von Teilzielen der Stunde.
- **`Unterrichtsbesuch`**: Historisches Feld, ursprünglich zur Kennzeichnung von Unterrichtsbesuchs-Kurzentwürfen.
