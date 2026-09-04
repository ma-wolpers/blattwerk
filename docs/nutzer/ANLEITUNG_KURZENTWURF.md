<!--
Automatisch generiert aus app/core/markdown_conventions.py.
NICHT VON HAND BEARBEITEN.
Neu erzeugen: python tools/docs/generate_authoring_guides.py
-->

# Kurzentwurf erstellen

Kurzentwurf ist ein eigener Blattwerk-Dokumenttyp mit einer **eigenen DSL** -- nicht dem `:::`-Blockdialekt aus der Arbeitsblatt-/Präsentations-Anleitung. Diese Anleitung wird automatisch aus dem Code erzeugt (`app/core/markdown_conventions.py`). Fehlermeldungen tragen stabile Codes wie `KZF011`/`KZF152` -- die vollständige Liste steht in [`docs/nutzer/VALIDATOR.md`](VALIDATOR.md#kurzentwurf-dsl-kzf). Reine Schreibkonventionen und didaktische Empfehlungen (keine Korrektheitsregeln) stehen separat in [`docs/nutzer/EMPFEHLUNGEN_STIL_KURZENTWURF.md`](EMPFEHLUNGEN_STIL_KURZENTWURF.md).

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

Ein Kurzentwurf gliedert sich in `#phase`-Abschnitte. Wichtig: der nach `#` getippte Hashtag ist **nicht** derselbe Text wie der Anzeigename der Phase (siehe Tabelle unten) -- z. B. heißt die Phase `Ergebnissicherung`, aber der Hashtag lautet `#sicherung`, und `Didaktische Reserve` ist `#reserve`. `t=<minuten>` gibt die Dauer der Phase an und ist optional; ohne Zeitangaben wird die Phase ohne Zeitlabel gerendert. `Hausaufgabe` und `Didaktische Reserve` benötigen nie ein `t=...` (fließen nicht in die Zeitrechnung ein). Zusätzlich gibt es `start=HH:MM` als optionales Attribut im `#phase`-Header: das steuert **nicht** die Zeitberechnung, sondern ist nur ein Plausibilitäts-Check gegen die aus `t=` fortlaufend berechnete Startzeit -- weicht `start=` davon ab, wird es ignoriert und es erscheint lediglich die Warnung `KZF136`. Jede Phase darf mehrfach im selben Dokument vorkommen (Wiederholungen werden automatisch mit römischen Ziffern durchnummeriert, z. B. "Erarbeitung I"/"Erarbeitung II") und es gibt **keine** vorgeschriebene Reihenfolge der Phasen -- sie können in beliebiger, auch wiederholter Abfolge auftreten.

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
- **`U>`**: Beginnt die Spalte Lernumgebung/Sozialform; Inhalt direkt hinter `U>`. Materialangaben (z. B. welches Arbeitsblatt verwendet wird) gehören strukturell ausschließlich hierhin -- keine andere Spalte ist dafür vorgesehen.
- **`ant<`**: Markiert eine antizipierte Schüler:innen-Antwort/-Reaktion zum jeweiligen Lernschritt -- **nicht nur Fehlvorstellungen**, sondern gute, neutrale wie falsche erwartete Antworten gleichermaßen. Sollte nach jedem `s<` gesetzt werden -- fehlt es, erscheint die Warnung `KZF152`.
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

## 6. Inline-Formatierung in Zellentext

Innerhalb von Zelleninhalten (Schritte/Aktivitäten/Umgebung) gilt dieselbe zentrale Inline-Formatierung wie im Arbeitsblatt-Editor -- Text markieren und eine Marker-Taste drücken. Die Hervorhebungsfarbe (`==...==`) ist in Kurzentwurf-Dokumenten fest, da Kurzentwurf kein eigenes Farbprofil hat.

- ***kursiv* -> **fett** -> ***fett und kursiv*****: `*text*` kursiv, `**text**` fett, `***text***` fett und kursiv zugleich -- im Editor per Auswahl markieren und wiederholt `*` drücken: erster Druck kursiv, zweiter fett, dritter fett+kursiv, vierter entfernt die Formatierung wieder.
- **_kursiv_ -> __unterstrichen__**: `_text_` kursiv (Alias zu `*text*`), `__text__` unterstrichen -- im Editor per Auswahl markieren und wiederholt `_` drücken: erster Druck kursiv, zweiter unterstrichen, dritter entfernt die Formatierung wieder. Anders als bei `*` bedeutet der doppelte Marker hier **nicht** Fett, sondern Unterstreichung.
- **==Hervorhebung==**: `==text==` hebt Text farbig hervor (`<mark>`). Im Editor markiert ein Tastendruck auf `=` die Auswahl direkt mit `==...==`; erneutes Drücken entfernt die Hervorhebung wieder. Die Farbe richtet sich im Arbeitsblatt/in der Präsentation nach dem aktiven Farbprofil, in Kurzentwurf-Dokumenten ist sie fest (Kurzentwurf hat kein eigenes Farbprofil).
- **~tief~ / ~{tief}**: `~x` (einzelnes Zeichen) oder `~{mehrere Zeichen}` stellt Text tief -- z. B. für chemische Formeln wie `H~2` oder `H~{2}O`. Im Editor fügt ein Tastendruck auf `~` bei einzeichiger Auswahl das Präfix ohne Klammern ein, bei mehrzeichiger Auswahl automatisch mit Klammern.
- **~~durchgestrichen~~**: `~~text~~` streicht Text durch. Im Editor: dieselbe `~`-Taste wie für Tiefstellung, aber ein zweiter Druck auf eine bereits tiefgestellte Auswahl eskaliert zu Durchstreichen; erneutes Drücken entfernt die Formatierung wieder.
- **^hoch^ / ^{hoch}**: `^x` (einzelnes Zeichen) oder `^{mehrere Zeichen}` stellt Text hoch -- z. B. für Exponenten wie `x^2` oder `x^{23}`. Im Editor fügt ein Tastendruck auf `^` bei einzeichiger Auswahl das Präfix ohne Klammern ein, bei mehrzeichiger Auswahl automatisch mit Klammern; erneutes Drücken entfernt die Formatierung wieder.
- **`code`**: `` `code` `` stellt kurzen Text als Inline-Code dar (Monospace-Schrift). Markup-Zeichen innerhalb der Backticks (`*`, `_`, `==`, ...) werden dabei **nicht** ausgewertet.
- **``` / code / ```**: Ein mit ` ``` ` auf eigener Zeile eingeleiteter und beendeter Block stellt mehrzeiligen Text als Codeblock dar. Im Editor fügt ein Tastendruck auf `` ` `` bei mehrzeiliger Auswahl automatisch die Fence-Zeilen vor und nach der Auswahl ein.
- **||spoiler||**: `||text||` versteckt Text hinter einer Markierung derselben Farbe wie der Text selbst -- lesbar erst, wenn die Stelle im PDF markiert/kopiert wird. Im Editor markiert ein Tastendruck auf `|` die Auswahl direkt mit `||...||`; erneutes Drücken entfernt den Spoiler wieder.
- **%%Kommentar%%**: `%%Text%%` markiert einen Autor:innen-Kommentar: der eingeschlossene Text erscheint in **keiner** Ausgabe (weder Vorschau noch PDF) und darf beliebiges Markup oder Formeln enthalten, ohne dass diese ausgewertet werden. Ein `%%` ohne passendes schließendes `%%` wird als normaler Text behandelt (keine Formatierung, aber auch kein Verschlucken nachfolgenden Inhalts) und als Diagnose-Hinweis gemeldet. Aktuell ohne eigene Editor-Taste -- von Hand eingetippt.
