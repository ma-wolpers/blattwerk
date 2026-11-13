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

Musterlösungstext, nur in der Lösungsfassung sichtbar. `label=true|false` (Standard `true`) blendet das Label "Lösung" ein/aus. Der Inhalt ist gewöhnliches Markdown (Rechenwege, Sätze, Listen) und wird nie bewertet: Teilpunkte und Erwartungen gehören in `:::expectation`. Steht in einer Lösung noch eine Punktangabe wie `(1P)`, warnt `SL024`; `target=` ist an `:::solution` veraltet und wird ignoriert (`OP004`).

## 3. Erwartungstypen

Ein Wort nach dem P einer Erwartung (`:::expectation`) benennt, was für eine Leistung erwartet wird, z. B. `Ableitung gebildet (0,5P Anwendung)` oder kurz `(0,5P Aw)`; Groß-/Kleinschreibung ist egal. Der Erwartungshorizont zeigt das Symbol vor dem Text und erklärt am Ende die verwendeten Typen mit genau den Sätzen aus dieser Tabelle. Im Editor erscheinen die Typen als Vorschläge, sobald nach dem P ein Leerzeichen steht; übernommen wird der volle Name. Lernhilfen sind in Klausuren erlaubt, ihre Nutzung soll aber Punkte kosten: Jede (Teil-)Aufgabe mit Lernhilfe braucht in ihren Erwartungen (oder denen der zugehörigen Aufgabe) einen Abzug vom Typ Lernhilfe, z. B. `Lernhilfe genutzt (−1P Lh)`, sonst warnt `KL013`. Der Erwartungshorizont beschriftet ihn als „Abzug bei Nutzung der Lernhilfe“; ohne Minuszeichen ist der Typ die Warnung `SL023`.

| Symbol | Typ | Kürzel | Bedeutung |
| --- | --- | --- | --- |
| 💡 | Ansatz | `An` | Ein passender Lösungsansatz bzw. das Vorgehen ist gewählt und notiert. |
| 🛠️ | Anwendung | `Aw` | Ein Verfahren ist richtig durchgeführt, z. B. gerechnet, umgeformt oder eingesetzt. |
| 💬 | Antwortsatz | `Sa` | Das Ergebnis ist in einem Satz auf die Frage bezogen formuliert. |
| 📚 | Fachsprache | `Fs` | Fachbegriffe sind passend und korrekt verwendet. |
| ⚖️ | Entscheidung | `En` | Eine Entscheidung (z. B. wahr/falsch, ja/nein, schneller/langsamer) ist richtig getroffen. |
| ✅ | Ergebnis | `Er` | Das (Teil-)Ergebnis ist richtig. |
| 🔍 | Beobachtung | `Be` | Etwas ist aus Graph, Tabelle oder Text richtig abgelesen bzw. beschrieben. |
| 🧩 | Begründung (auch: Begruendung) | `Bg` | Eine Aussage ist schlüssig begründet. |
| 📏 | Einheit/Größe (auch: Einheit, Größe, Groesse) | `Ei` | Die passende Einheit bzw. Größe ist angegeben. |
| 📐 | Darstellung | `Da` | Graph, Skizze oder Tabelle ist richtig und sauber dargestellt. |
| 📝 | Formales (auch: Formal, Form) | `Fo` | Eine formale Anforderung ist erfüllt, z. B. eine verlangte Schreibweise. |
| 🛟 | Lernhilfe | `Lh` | Abzug, wenn die Lernhilfe zu dieser Aufgabe genutzt wurde. |

## 4. Anforderungsbereiche (`afb`)

Anforderungsbereich der Aufgabe bzw. Teilaufgabe (`1`, `2` oder `3`). Rein informativ: wird nicht im Schülerdokument angezeigt, sondern in der Klausur-Übersicht des Editors ausgewertet (interne Statistik, nicht im Erwartungshorizont). Bonuspunkte zählen nicht mit. Eine Teilaufgabe ohne eigene Angabe erbt die AFB ihrer Aufgabe.

## 5. Hilfsmittelfreier Teil (`--hm`)

`--hm` auf einer eigenen Zeile trennt in einer Klausur (`.kbw`) den hilfsmittelfreien Teil vom Teil mit Hilfsmitteln: davor erscheint "Teil A – hilfsmittelfrei", am Marker beginnt eine neue Seite mit "Teil B – mit Hilfsmitteln"; die Aufgabennummern laufen weiter, Punkte und AFB werden je Teil ausgewertet. Nur zwischen zwei Aufgaben; in anderen Dokumenttypen ohne Wirkung. Ein zweites `--hm` davor trennt ein Deckblatt ab: Alles vor dem ersten `--hm` (Hinweise, Bewertungstabelle …, aber keine Aufgaben) steht auf der ersten Seite ohne Teilüberschrift, "Teil A" beginnt dann auf einer neuen Seite. Mehr als zwei `--hm` sind ein Fehler. Mit `show_student_header: ja` trägt jeder Teil, der auf einer neuen Seite beginnt, oben die Schülerkopfzeile (Name, Lerngruppe, Datum), damit getrennt eingesammelte Teile beschriftet sind.

## 6. Wahlteile (`--w`)

Wahlteile in einer Klausur (`.kbw`): `--w[k] Titel` auf einer eigenen Zeile eröffnet einen Wahlbereich, jedes weitere `--w Titel` startet den nächsten Wahlteil desselben Bereichs. Von den n Wahlteilen wählen die Schülerinnen und Schüler k (1 ≤ k < n); gewertet werden die angekreuzten, auch wenn mehr bearbeitet wurde. Der Bereich endet am nächsten `--hm` oder am Dokumentende; nach `--hm` kann ein weiterer Bereich mit `--w[k]` beginnen. Jeder Wahlteil beginnt auf einer neuen Seite mit der Überschrift "Wahlteil 1 – Titel" (ohne Titel nur "Wahlteil 1") und einem Ankreuzfeld "Diesen Wahlteil wähle ich."; über dem ersten steht "Wähle k der n Wahlteile; gewertet werden die angekreuzten.". Alle Wahlteile eines Bereichs müssen gleich viele Punkte haben; die erreichbare Gesamtpunktzahl zählt k Wahlteile. Aufgabennummern laufen durch. Bewertungstabelle und Erwartungshorizont gruppieren nach Teilen mit "k aus n"; die AFB-Verteilung steht dann nur je Teil. Aufgaben vor dem ersten Bereich (ohne `--hm`) bilden den Pflichtteil (ohne Überschrift). Fehler blockieren den Export: `--w` ohne offenen Bereich (`KL008`), `--w[k]` in einem offenen Bereich (`KL009`), ungültiges k (`KL010`), ungleiche Punkte (`KL011`), `--w` außerhalb von Klausuren (`KL012`); jeder Wahlteil braucht eine Aufgabe (`KL004`). Ein Wahlteil ohne Titel ergibt nur eine Warnung (`KL014`).

## 7. Bewertungstabelle

Bewertungstabelle (selbstschließend: `:::evaluation:::`) mit den Zeilen Aufgaben, maximale Punkte und leeren Feldern für die erreichten Punkte, rechts die Summe. Nur in Arbeitsblättern und Klausuren. Aufgaben ohne Punkte erscheinen mit `–` (Warnung `EV001`), widersprüchliche mit `?`; die Summe wird nur ausgewiesen, wenn alle Punktzahlen bekannt sind.

- `level`: `task` (Standard): eine Spalte je Aufgabe; `subtask`: bei bepunkteten Teilaufgaben je Teilaufgabe eine Spalte (1a, 1b, ...).
- `parts`: `true` teilt die Tabelle in Klausuren mit `--hm` in Teil A und Teil B (je mit Summe) und weist zusätzlich die Gesamtsumme aus. Ohne `--hm` ohne Wirkung. Mit Wahlteilen (`--w`) ist die Tabelle immer nach Teilen gruppiert ("Wahlteile: k aus n"), die Gesamtsumme zählt k Wahlteile.
- `grade`: `true` ergänzt unter der Tabelle rechtsbündig leere Felder „Dies sind ___ %“ und „Note: ___“ (auch bei `parts=true` nur einmal). Gilt nur für diesen Block: Bei mehreren Bewertungstabellen bekommt jede mit `grade=true` ihre eigenen Felder.

## 8. Operatorentabelle

Operatorentabelle (selbstschließend: `:::operators:::`) mit den Definitionen der mit `!!…!!` markierten Operatoren. Nur in Arbeitsblättern und Klausuren, standardmäßig nur im Arbeitsblatt (nicht in der Lösung; `mode=solution` kehrt das um). Im PDF rutscht die Tabelle ans Seitenende, wenn über ihr schon Inhalt steht -- typisch direkt vor `--!` oder `--hm`; steht sie als Erstes auf einer Seite, bleibt sie oben. `title="Operatoren"` setzt eine Überschrift. Ohne Tabelle meldet Blattwerk verwendete Operatoren (`OPR004`) bzw. Operatoren hinter der letzten Tabelle (`OPR005`); eine Tabelle ohne Operatoren ist ein Fehler (`OPR006`), sich überschneidende Bereiche eine Warnung (`OPR008`).

- `scope`: `previous` (Standard): Operatoren seit der vorigen Operatorentabelle bzw. seit Dokumentanfang; `all`: alle Operatoren des Dokuments, auch solche nach der Tabelle; `part`: alle Operatoren des Klausurteils (`--hm`), in dem die Tabelle steht -- Deckblatt und Teil A zählen zusammen, ohne `--hm` das ganze Dokument.

## 9. Klausur-Übersicht

Unter der Diagnostik zeigt der Editor bei Klausuren live die Gesamtpunkte und ihre Verteilung auf AFB I/II/III, mit `--hm` zusätzlich je Teil. Die Prozentangaben beziehen sich immer auf die Gesamtpunktzahl der Klausur. Fehlen Punkte oder Anforderungsbereiche, steht dort „unvollständig“ mit dem Grund statt einer Prozentzahl.

## 10. Erwartungshorizont

Im Exportdialog einer Klausur gibt es unter „Inhalt“ den Punkt „Erwartungshorizont“ (PDF oder HTML); in der Vorschau ist er die dritte Ansicht neben Aufgabe und Lösung (`Tab` schaltet reihum). Er listet je (Teil-)Aufgabe nur die Erwartungen aus `:::expectation` mit ihren Teilpunkten, ohne Aufgabentext und ohne Musterlösung, mit einer leeren Spalte „erreicht“ (die Spalte „Nr.“ zeigt nur selbst geschriebene Nummern), dazu Teilsummen je Hilfsmittel-Teil (Bonuspunkte getrennt, z. B. „17 P + 2 Bonuspunkte“). Die AFB-Verteilung ist eine interne Statistik und steht nur in der Klausur-Übersicht des Editors. Alternative Wege stehen mit „Weg A:“ vor dem Text, Optionen mit „Option:“ (dazu eine Zeile mit ihrem Höchstwert), Abzüge je Fehler und Abzüge bei Nutzung der Lernhilfe am Tabellenende, Erwartungstypen als Symbol vor dem Text; am Ende erklärt eine Legende die verwendeten Typen mit je einem kurzen Satz. Widersprüchliche Punkte verhindern den Export; fehlende Teilpunkte (`SL005`) oder Erwartungen (`SL007`) werden nur angemerkt.
