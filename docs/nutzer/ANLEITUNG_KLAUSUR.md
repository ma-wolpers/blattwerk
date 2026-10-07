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

Musterlösungstext. `label=true|false` (Standard `true`) blendet das Label "Lösung" ein/aus. Gehört zur nächsten vorangehenden Aufgabe bzw. Teilaufgabe (nie über `--hm` hinweg); mit `target=task` bzw. `target=b` lässt sie sich gezielt der Aufgabe bzw. Teilaufgabe b derselben Aufgabe zuordnen. Nummerierte Lösungspunkte können Teilpunkte am Zeilenende tragen, z. B. `1. Ansatz aufgestellt (2P)` oder `(1,5P)`; sind alle Punkte einer Aufgabe annotiert, muss ihre Summe zur Punktzahl der Aufgabe passen (sonst Fehler `PK002`). Für alternative Lösungswege gibt es Teilpunkte `(x/nP)`: `(1/3P)` heißt „einer von drei erreichbaren Punkten“. Weil alternative Wege nicht addiert werden, darf die Summe die Punktzahl übersteigen -- das ist gewollt. Der Nenner muss der Punktzahl der (Teil-)Aufgabe entsprechen (`SL009`), kein Schritt darf mehr als n Punkte bringen (`SL010`), und zusammen müssen mindestens n Punkte erreichbar sein (`SL011`). Ergibt die Summe genau n, genügt die normale Schreibweise `(xP)` (Hinweis `SL012`).

## 3. Anforderungsbereiche (`afb`)

Anforderungsbereich der Aufgabe bzw. Teilaufgabe (`1`, `2` oder `3`). Rein informativ: wird nicht im Schülerdokument angezeigt, sondern in der Klausur-Übersicht und im Erwartungshorizont ausgewertet. Eine Teilaufgabe ohne eigene Angabe erbt die AFB ihrer Aufgabe.

## 4. Hilfsmittelfreier Teil (`--hm`)

`--hm` auf einer eigenen Zeile trennt in einer Klausur (`.kbw`) den hilfsmittelfreien Teil vom Teil mit Hilfsmitteln: davor erscheint "Teil A – hilfsmittelfrei", am Marker beginnt eine neue Seite mit "Teil B – mit Hilfsmitteln"; die Aufgabennummern laufen weiter, Punkte und AFB werden je Teil ausgewertet. Nur zwischen zwei Aufgaben; in anderen Dokumenttypen ohne Wirkung. Ein zweites `--hm` davor trennt ein Deckblatt ab: Alles vor dem ersten `--hm` (Hinweise, Bewertungstabelle …, aber keine Aufgaben) steht auf der ersten Seite ohne Teilüberschrift, "Teil A" beginnt dann auf einer neuen Seite. Mehr als zwei `--hm` sind ein Fehler.

## 5. Bewertungstabelle

Bewertungstabelle (selbstschließend: `:::evaluation:::`) mit den Zeilen Aufgaben, maximale Punkte und leeren Feldern für die erreichten Punkte, rechts die Summe. Nur in Arbeitsblättern und Klausuren. Aufgaben ohne Punkte erscheinen mit `–` (Warnung `EV001`), widersprüchliche mit `?`; die Summe wird nur ausgewiesen, wenn alle Punktzahlen bekannt sind.

- `level`: `task` (Standard): eine Spalte je Aufgabe; `subtask`: bei bepunkteten Teilaufgaben je Teilaufgabe eine Spalte (1a, 1b, ...).
- `parts`: `true` teilt die Tabelle in Klausuren mit `--hm` in Teil A und Teil B (je mit Summe) und weist zusätzlich die Gesamtsumme aus. Ohne `--hm` ohne Wirkung.
- `grade`: `true` ergänzt unter der Tabelle rechtsbündig leere Felder „Dies sind ___ %“ und „Note: ___“ (auch bei `parts=true` nur einmal). Gilt nur für diesen Block: Bei mehreren Bewertungstabellen bekommt jede mit `grade=true` ihre eigenen Felder.

## 6. Klausur-Übersicht

Unter der Diagnostik zeigt der Editor bei Klausuren live die Gesamtpunkte und ihre Verteilung auf AFB I/II/III, mit `--hm` zusätzlich je Teil. Die Prozentangaben beziehen sich immer auf die Gesamtpunktzahl der Klausur. Fehlen Punkte oder Anforderungsbereiche, steht dort „unvollständig“ mit dem Grund statt einer Prozentzahl.

## 7. Erwartungshorizont

Im Exportdialog einer Klausur gibt es unter „Inhalt“ den Punkt „Erwartungshorizont“ (PDF oder HTML). Er listet je (Teil-)Aufgabe nur die nummerierten Lösungspunkte mit ihren Teilpunkten, ohne Aufgabentext, mit einer leeren Spalte „erreicht“, dazu Teilsummen je Hilfsmittel-Teil und die AFB-Tabelle. Widersprüchliche Punkte verhindern den Export; fehlende Teilpunkte (`SL005`) oder Erwartungen (`SL007`) werden nur angemerkt.
