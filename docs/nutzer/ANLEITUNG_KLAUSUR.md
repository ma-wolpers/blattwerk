<!--
Automatisch generiert aus app/core/markdown_conventions.py.
NICHT VON HAND BEARBEITEN.
Neu erzeugen: python tools/docs/generate_authoring_guides.py
-->



# Klausur erstellen

Eine Klausur ist eine Blattwerk-Datei mit der Endung `.kbw`. Sie nutzt denselben `:::`-Blockdialekt wie ein Arbeitsblatt (siehe [`ANLEITUNG_ARBEITSBLATT_PRAESENTATION.md`](ANLEITUNG_ARBEITSBLATT_PRAESENTATION.md)), zeigt aber keine Sozialform-Symbole und bietet zusätzlich Anforderungsbereiche, den Hilfsmittel-Trenner `--hm`, die Klausur-Übersicht und den Erwartungshorizont. Die Diagnose-Codes (`KL…`, `PK…`, `SL…`, `EV…`) stehen in [`VALIDATOR.md`](VALIDATOR.md).

## 1. Schnellstart

```markdown
---
document_type: exam
Titel: Neue Klausur
Fach: Fach eintragen
Thema: Thema eintragen
Lerngruppe: Lerngruppe eintragen
Datum: Datum eintragen
Dauer: 90 Minuten
Hilfsmittel: Hilfsmittel eintragen
---

:::task points=4 afb=1
Formuliere hier die erste Aufgabe.
:::

:::solution
1. Erwarteter Lösungsschritt (2P)
2. Zweiter Lösungsschritt (2P)
:::
```

## 2. Punkte und Teilpunkte

Punktzahl der Aufgabe bzw. Teilaufgabe, wird rechts am Zeilenrand als `X P` angezeigt (Zahl, Komma oder Punkt als Dezimaltrenner). Halbe Punkte sind möglich: `points=0,5` oder `points=1.5` erscheinen einheitlich als `0,5 P` bzw. `1,5 P`. Sind alle Teilaufgaben bepunktet, ergibt ihre Summe die Punktzahl der Aufgabe; ein zusätzlich gesetztes `points` an der Aufgabe muss genau dieser Summe entsprechen (`PK001`). Nur einen Teil der Teilaufgaben zu bepunkten ist ein Fehler (`PK004`).

Musterlösungstext. `label=true|false` (Standard `true`) blendet das Label "Lösung" ein/aus. Gehört zur nächsten vorangehenden Aufgabe bzw. Teilaufgabe (nie über `--hm` hinweg); mit `target=task` bzw. `target=b` lässt sie sich gezielt der Aufgabe bzw. Teilaufgabe b derselben Aufgabe zuordnen. Lösungspunkte sind Zeilen der Form `1. …` (nicht `1)`); eingerückte oder direkt folgende Zeilen und Unterlisten gehören zum Punkt darüber, Inhalt in Codeblöcken, Kommentaren `%%…%%` und Formeln zählt nie als Punkt. Lösungspunkte können Teilpunkte am Ende ihrer ersten Zeile tragen, z. B. `1. Ansatz aufgestellt (2P)` oder `(1,5P)`; sind alle Punkte einer Aufgabe annotiert, muss ihre Summe zur Punktzahl der Aufgabe passen (sonst Fehler `PK002`). Für alternative Lösungswege steht ein Buchstabe vor dem P: `(0,5aP)` gehört zu Weg A, `(1bP)` zu Weg B, Punkte ohne Buchstabe gelten für alle Wege. Erreichbar sind dann die gemeinsamen Punkte plus der beste Weg, und genau das muss die Punktzahl ergeben. In der Lösung erscheint `(0,5P, Weg A)`, im Erwartungshorizont „Weg A:“ vor dem Text. Die Buchstaben gelten je (Teil-)Aufgabe; zwei voneinander unabhängige Wahlmöglichkeiten gehören in zwei Teilaufgaben. Zählen dagegen mehrere Möglichkeiten zusammen („von diesen vier Begründungen brauchst du zwei“), steht statt des Buchstabens ein Höchstwert: `(1/2P)` ist eine Option mit 1 Punkt, alle Optionen zusammen bringen höchstens 2 Punkte. Erreichbar sind dann gemeinsame Punkte + bester Weg + Optionen bis zum Höchstwert. In der Lösung erscheint `(1P, Option, max. 2P)`. Alle Optionen einer (Teil-)Aufgabe brauchen denselben Höchstwert (`SL019`), keine darf ihn allein übersteigen (`SL020`), zusammen müssen sie ihn erreichen (`SL021`); ergeben sie genau den Höchstwert, genügt `(xP)` (Hinweis `SL022`). Eine unlesbare Punktangabe wie `(0,5abP)` ist Fehler `SL018`. Ein Minuszeichen macht einen Lösungspunkt zum Abzug je Fehler, z. B. `5. Je falsches Kreuz (−0,5P)` oder `(-1P)` (`-`, `−` und `–` gelten gleich): Abzüge zählen nicht zur Summe, gelten für die ganze (Teil-)Aufgabe (ein Weg-Buchstabe daran wird ignoriert, Hinweis `SL016`) und stehen im Erwartungshorizont als „Abzug je Fehler“ am Ende der Tabelle. Optional benennt ein Wort nach dem P, was für eine Leistung erwartet wird (Erwartungstyp, Name oder Kürzel): Ansatz (An), Anwendung (Aw), Antwortsatz (Sa), Fachsprache (Fs), Entscheidung (En), Ergebnis (Er), Beobachtung (Be), Begründung (Bg), Einheit/Größe (Ei), Darstellung (Da), Formales (Fo) -- z. B. `(0,5P An)`, `(1aP Anwendung)`, `(−1P Bg)`. Der Erwartungshorizont zeigt dafür ein Symbol vor dem Text und eine Legende der verwendeten Typen, die Lösung blendet den Typ aus. Ein unbekannter Typ ist eine Warnung (`SL017`).

## 3. Anforderungsbereiche (`afb`)

Anforderungsbereich der Aufgabe bzw. Teilaufgabe (`1`, `2` oder `3`). Rein informativ: wird nicht im Schülerdokument angezeigt, sondern in der Klausur-Übersicht und im Erwartungshorizont ausgewertet. Eine Teilaufgabe ohne eigene Angabe erbt die AFB ihrer Aufgabe.

## 4. Hilfsmittelfreier Teil (`--hm`)

`--hm` auf einer eigenen Zeile trennt in einer Klausur (`.kbw`) den hilfsmittelfreien Teil vom Teil mit Hilfsmitteln: davor erscheint "Teil A – hilfsmittelfrei", am Marker beginnt eine neue Seite mit "Teil B – mit Hilfsmitteln"; die Aufgabennummern laufen weiter, Punkte und AFB werden je Teil ausgewertet. Nur zwischen zwei Aufgaben; in anderen Dokumenttypen ohne Wirkung. Ein zweites `--hm` davor trennt ein Deckblatt ab: Alles vor dem ersten `--hm` (Hinweise, Bewertungstabelle …, aber keine Aufgaben) steht auf der ersten Seite ohne Teilüberschrift, "Teil A" beginnt dann auf einer neuen Seite. Mehr als zwei `--hm` sind ein Fehler. Mit `show_student_header: ja` trägt jeder Teil, der auf einer neuen Seite beginnt, oben die Schülerkopfzeile (Name, Lerngruppe, Datum), damit getrennt eingesammelte Teile beschriftet sind.

## 5. Bewertungstabelle

Bewertungstabelle (selbstschließend: `:::evaluation:::`) mit den Zeilen Aufgaben, maximale Punkte und leeren Feldern für die erreichten Punkte, rechts die Summe. Nur in Arbeitsblättern und Klausuren. Aufgaben ohne Punkte erscheinen mit `–` (Warnung `EV001`), widersprüchliche mit `?`; die Summe wird nur ausgewiesen, wenn alle Punktzahlen bekannt sind.

- `level`: `task` (Standard): eine Spalte je Aufgabe; `subtask`: bei bepunkteten Teilaufgaben je Teilaufgabe eine Spalte (1a, 1b, ...).
- `parts`: `true` teilt die Tabelle in Klausuren mit `--hm` in Teil A und Teil B (je mit Summe) und weist zusätzlich die Gesamtsumme aus. Ohne `--hm` ohne Wirkung.
- `grade`: `true` ergänzt unter der Tabelle rechtsbündig leere Felder „Dies sind ___ %“ und „Note: ___“ (auch bei `parts=true` nur einmal). Gilt nur für diesen Block: Bei mehreren Bewertungstabellen bekommt jede mit `grade=true` ihre eigenen Felder.

## 6. Operatorentabelle

Operatorentabelle (selbstschließend: `:::operators:::`) mit den Definitionen der mit `!!…!!` markierten Operatoren. Nur in Arbeitsblättern und Klausuren, standardmäßig nur im Arbeitsblatt (nicht in der Lösung; `mode=solution` kehrt das um). Im PDF rutscht die Tabelle ans Seitenende, wenn über ihr schon Inhalt steht -- typisch direkt vor `--!` oder `--hm`; steht sie als Erstes auf einer Seite, bleibt sie oben. `title="Operatoren"` setzt eine Überschrift. Ohne Tabelle meldet Blattwerk verwendete Operatoren (`OPR004`) bzw. Operatoren hinter der letzten Tabelle (`OPR005`); eine Tabelle ohne Operatoren ist ein Fehler (`OPR006`), sich überschneidende Bereiche eine Warnung (`OPR008`).

- `scope`: `previous` (Standard): Operatoren seit der vorigen Operatorentabelle bzw. seit Dokumentanfang; `all`: alle Operatoren des Dokuments, auch solche nach der Tabelle; `part`: alle Operatoren des Klausurteils (`--hm`), in dem die Tabelle steht -- Deckblatt und Teil A zählen zusammen, ohne `--hm` das ganze Dokument.

## 7. Klausur-Übersicht

Unter der Diagnostik zeigt der Editor bei Klausuren live die Gesamtpunkte und ihre Verteilung auf AFB I/II/III, mit `--hm` zusätzlich je Teil. Die Prozentangaben beziehen sich immer auf die Gesamtpunktzahl der Klausur. Fehlen Punkte oder Anforderungsbereiche, steht dort „unvollständig“ mit dem Grund statt einer Prozentzahl.

## 8. Erwartungshorizont

Im Exportdialog einer Klausur gibt es unter „Inhalt“ den Punkt „Erwartungshorizont“ (PDF oder HTML). Er listet je (Teil-)Aufgabe nur die nummerierten Lösungspunkte mit ihren Teilpunkten, ohne Aufgabentext, mit einer leeren Spalte „erreicht“, dazu Teilsummen je Hilfsmittel-Teil und die AFB-Tabelle. Alternative Wege stehen mit „Weg A:“ vor dem Text, Optionen mit „Option:“ (dazu eine Zeile mit ihrem Höchstwert), Abzüge je Fehler am Tabellenende, Erwartungstypen als Symbol vor dem Text mit einer Legende vor der AFB-Tabelle. Widersprüchliche Punkte verhindern den Export; fehlende Teilpunkte (`SL005`) oder Erwartungen (`SL007`) werden nur angemerkt.
