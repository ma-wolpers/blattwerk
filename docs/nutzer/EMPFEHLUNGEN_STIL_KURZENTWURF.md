# Stilempfehlungen: Kurzentwurf

Dieses Dokument sammelt Autor:innen-Empfehlungen für die Kurzentwurf-DSL -- im
Unterschied zu [`docs/nutzer/ANLEITUNG_KURZENTWURF.md`](ANLEITUNG_KURZENTWURF.md) handelt es
sich hier **nicht** um Regeln, die der Validator durchsetzt oder die für ein technisch
gültiges Dokument nötig sind. Zwei unterschiedliche Arten von Empfehlungen sind bewusst
getrennt: reine Schreibkonventionen (wie man den Freitext-Inhalt formatiert) und
didaktische Gestaltungsempfehlungen (pädagogisches Urteil, kein Syntaxbezug).

Nicht codegeneriert (rein redaktionell) und nicht Teil der `assert_prose_coverage`-Prüfung.

## Schreibkonventionen

**Mehrschritt-Aufgaben und Mittel-zum-Zweck-Schritte in einer `s<`-Zeile bündeln.** Ein
Zwischenschritt wie "Koordinatensystem erstellen" ist in oberen Jahrgangsstufen selten eine eigene Lernaktivität,
sondern nur noch ein Mittel zum Zweck -- mit Konjunktionen (`und`/`indem`/`durch`) in die Hauptaktivität
integrieren statt in mehrere `s<`-Zeilen zu zerlegen:

- Weniger hilfreich: drei separate `s<`-Zeilen für "Koordinatensystem erstellen",
  "Begriffe markieren", "Markierungen beschriften"
  (außer: es ist ein eigenständiger, didaktisch relevanter Schritt, z. B. für das Lernen, wie man einen Graphen korrekt zeichnet)
- Besser: `s< markieren ihre Begriffe in einem Koordinatensystem und beschriften die
  Markierungen.`

Eigene `s<`-Zeile bleibt angemessen, wenn ein Schritt zeitlich/didaktisch eigenständig ist
(z. B. "erst Gruppenarbeit, dann Präsentation") -- oder wenn nach einer Aktivität eine
**explizite Reflexion** stattfindet (z. B. "benennen, welche Fachbegriffe/Perspektiven
genutzt wurden"): das ist ein eigener kognitiver Schritt, keine implizite Zugabe zu den
Antizipationen.

**Parallele/alternative Aufgaben als mehrere `s<`-Zeilen, getrennt durch `---`.** Wählen
Lernende zwischen gleichwertigen Varianten, jede Variante als eigene `s<`-Zeile mit `---`
als Trenner -- nicht als Aufzählung innerhalb einer Zeile. Das macht sichtbar, dass es
echte, gleichwertige Alternativen sind (nicht mehrere verpflichtende Teilaufgaben), und
bleibt auch bei längeren Formulierungen pro Variante lesbar:

```markdown
s< schreiben eine fiktive Geschichte über den Graphen.
---
s< erstellen ein Diagramm zum Graphen.
```

**Mehrere Antizipationen als Liste darstellen.** Gibt es zu einem Lernschritt mehrere
erwartete Antworten (z. B. eine gute, eine mittelmäßige, eine falsche, eine abwägige, ...), diese als
Markdown-Liste innerhalb von `ant<` schreiben statt als einzelnen Fließtext-Satz:

```markdown
ant< - "Photosynthese wandelt Licht in Zucker um." (gut)
      - "Pflanzen brauchen Licht zum Wachsen." (unvollständig)
      - "Pflanzen atmen wie wir." (Fehlvorstellung)
```

Zeigt eine Antizipation eine *Progression* (Lernende nähern sich der Erkenntnis in
Schritten), gehört sie genauso in eine `ant<`-Liste -- nicht in mehrere separate
`ant<`-Blöcke, sonst geht der Sequenz-Charakter verloren:

```markdown
ant< - "Drei Männer, die sich die Hand geben."
      - "Drei Männer, die es versuchen, aber nicht schaffen."
      - "Auf dem einen werden Zahlen auf sich selbst zugeordnet..."
      - "Das sind alles drei die gleiche Funktion."
```

**Antizipationen sind einzelne, alternative Aussagen -- kein Dialog.** Jeder `ant<`-Eintrag
ist *eine* mögliche Reaktion auf das zugehörige `s<`, die für sich allein stehen kann, als
käme sie von einer anderen Person. Die Einträge sind Alternativen zueinander, keine
Gesprächsfolge. Das heißt konkret:

- Kein Wechsel zwischen Sprecher:innen: keine Frage-Antwort-Paare und kein "A sagt ...,
  B antwortet ..." innerhalb derselben Liste.
- Keine Lehrkraft-Äußerungen in `ant<` (Rückfragen, Impulse, Bestätigungen). Was die
  Lehrkraft sagt oder tut, gehört nach `S>`.
- Keine Bezüge auf den vorherigen Eintrag ("Oder ...", "Kann auch sein ...", "Genau, und
  ..."), die eine Aussage erst im Zusammenhang verständlich machen.

Beispiele:

- Nicht (Dialog): `ant< - "Ist das überhaupt eine Funktion?" \n      - "Ja, weil jedem x genau ein y zugeordnet ist."`
- Nicht (Lehrkraft im Dialog): `ant< - "Das ist linear." \n      - L: "Woran erkennst du das?"`
- Nicht (verkettet): `ant< - "Der Server ist kaputt." \n      - "Oder der Router spinnt."`
- Sondern: `ant< - "Der Server ist kaputt." \n      - "Der Router spinnt schon wieder."`

(Ausnahme: eine bewusst dargestellte *Progression*, siehe oben -- dort ist die Abfolge
selbst der Punkt. Auch dann ist jeder Schritt eine eigenständige Aussage der Lernenden und
kein Gespräch.)

**Kein "Schüler:innen"-Subjekt nach `S>`/`s<`.** Der Marker selbst steht bereits für das
Subjekt ("die Lernenden") -- es noch einmal auszuschreiben ist redundant. Prädikat direkt,
klein geschrieben, 3. Person Plural:

- Nicht: `s< Die Schüler:innen formulieren erste Vermutungen.`
- Sondern: `s< formulieren erste Vermutungen.`

**Zeitangaben nicht im Segmentinhalt wiederholen.** `t=`/`start=` am Phasenkopf sind die
einzige vorgesehene Stelle für Zeitangaben. Eine Formulierung wie `U> 10 Minuten
Gruppenarbeit` dupliziert Information, die bereits strukturell in `t=10` steckt, und kann
bei einer späteren Änderung der Phasendauer leicht veralten.

**Sozialformen präzise benennen.** Konkrete Abkürzungen statt vager Begriffe wie "Plenum"
oder "Diskussion", die offenlassen, wer eigentlich mit wem spricht:

- `LSG` (Lehrer-Schüler-Gespräch) -- die Lehrkraft moderiert, Schüler:innen antworten.
- `SSG` (Schüler-Schüler-Gespräch) -- Lernende geben sich gegenseitig Feedback, ohne dass
  die Lehrkraft moderiert.
- `GA` -- Lernende arbeiten in Kleingruppen.
- `PA` -- Lernende arbeiten in Paaren.
- `EA` -- Lernende arbeiten allein.

**Material stets mit konkretem Dateinamen -- und `U>`-Angaben jede Phase erneut nennen.**
`U>` ist die richtige Spalte für Materialangaben (siehe Hauptanleitung) -- innerhalb dieser
Spalte so konkret sein, dass klar ist, was tatsächlich vorzubereiten ist:

- Weniger hilfreich: `U> GA; Arbeitsblatt` / `U> Papier` / `U> Stifte`
- Besser: `U> GA; Arbeitsblatt_Photosynthese_V2.pdf` / `U> kariertes Heft für
  die Tabelle` / `U> Buntstifte; Bleistift; Lineal; A3-Papier`

Das gilt in **jeder** Phase erneut, auch wenn Sozialform/Material sich von der vorherigen
Phase nicht unterscheiden oder selbsterklärend wirken -- kein stillschweigendes
Fortgelten-Lassen, das nur beim Lesen einer einzelnen Phase auffällt.

**Jede Angabe in ihre Spalte.** Jede Spalte hat genau eine Aufgabe:

| Marker | Inhalt | Nicht hierhin |
| --- | --- | --- |
| `S>` | Lernschritte und Handlungen der Lehrkraft (Impuls, Arbeitsauftrag, Material verteilen, Ergebnisse vergleichen lassen) | Lernaktivitäten, Material-/Sozialformangaben |
| `A>` + `s<` | Was die Lernenden tun | Lehrkraft-Handlungen |
| `ant<` | Erwartete Äußerungen der Lernenden, **nur** im `A>`-Block direkt hinter dem zugehörigen `s<` | Hinter `S>`- oder `U>`-Inhalt (löst `KZF154` aus) |
| `U>` | Nur Material, Sozialform und Methode | Beschreibungen, was die Lehrkraft tut |

- Nicht: `U> GA; Lehrkraft verteilt die Kartensätze und erklärt die Spielregeln`
- Sondern: `S> Kartensätze verteilen, Spielregeln erklären` und `U> GA; Gruppenpuzzle;
  Kartensätze ❎🔺🔷☀️`

**`S>` in Stichpunkten statt Fließtext.** Mehrere Lernschritte in einer Zelle als
Markdown-Liste mit einem Schritt pro Zeile schreiben (wird als Liste gerendert), nicht als
zusammenhängenden Satz:

```markdown
S> - Leitfrage präsentieren
   - Arbeitsauftrag erteilen
   - Kartensätze verteilen
```

statt `S> Die Lehrkraft präsentiert die Leitfrage, erteilt anschließend den Arbeitsauftrag
und verteilt danach die Kartensätze.` Ein einzelner kurzer Schritt darf ohne Spiegelstrich
direkt hinter `S>` stehen.

**Keine selbstverständlichen Schritte in `S>`.** Nur nennen, was eine inhaltliche
Information trägt (welcher Impuls, welcher Auftrag, welches Material). Was schon aus dem
Phasennamen oder dem Ablauf folgt, weglassen:

- Weglassen: `S> Ergebnisse der Sicherung sichern` / `S> Phase beenden` / `S> zur
  Erarbeitung überleiten`
- Behalten: `S> Tafelbild mit den drei Funktionsdarstellungen entwickeln`

**Schreibweise: Umlaute und Prozentzeichen.** Umlaute und ß konsequent ausschreiben (ä,
ö, ü, ß statt ae, oe, ue, ss). Zwischen Zahl und Prozentzeichen steht ein Leerzeichen:
`75 %` statt `75%`.

## Didaktische Gestaltungsempfehlungen

**Nur echte Lernaktivitäten als eigene Phase/Segment.** Kurztest: braucht der Schritt Zeit
und bringt er Lernfortschritt? Dann ja. Ist er eine Rahmenbedingung, Anleitung oder
Metaebene, dann nein:

- ❌ Nicht: "Schüler:innen verstehen, dass Fehler gewünscht sind" -- das ist eine
  Mindset-Setzung, gehört in die mündliche Anleitung, nicht in eine eigene Phase.
- ✅ Sondern: "vergleichen Definitionen verschiedener Funktionsdimensionen und überprüfen
  sie auf Gleichheit" -- das ist eine echte Aktivität mit eigenem Zeitbudget.
- ❌ Nicht: "Schüler:innen wählen Schwierigkeitsgrad" -- das ist eine Rahmenbedingung der
  Erarbeitung, keine eigenständige Phase.
- ✅ Sondern: "markieren ihre Begriffe in einem Koordinatensystem und beschriften die
  Markierungen" -- das ist eine echte Lernaktivität.

Rahmenbedingungen (Material, Sozialform, Differenzierung, Dokumentation, auch "sich
gegenseitig helfen" innerhalb einer Gruppenarbeit) gehören nach `U>` oder in die mündliche
Anleitung, Qualitätskriterien (z. B. "mindestens 5 relevante Fachbegriffe") direkt in die
`s<`-Formulierung -- keins von beidem als eigene Phase. **Ausnahme:** Ist Kooperation/
gegenseitige Hilfe selbst der fachliche Fokus der Einheit, kann sie sehr wohl eine eigene
Lernaktivität sein.

**Antizipationen als Sprechakte der Lernenden formulieren.** `ant<` sollte lauten wie
etwas, das Lernende selbst sagen könnten -- nicht wie eine Frage der Lehrkraft:

- Nicht: `ant< "Was ist besonders klar dargestellt?"`
- Sondern: `ant< "Besonders klar hast du dargestellt..."`
- Nicht: `ant< "Welche Fachbegriffe habt ihr erkannt?"`
- Sondern: `ant< "Hier ist zusätzlich noch..."`

Dabei auch naheliegende/offensichtliche Antworten mit aufnehmen (z. B. "Sie erstellt ein
Koordinatensystem."), nicht nur überraschende -- Antizipationen sind für die Lehrkraft da,
um zu wissen, welche Reaktionen zu erwarten sind; je vollständiger antizipiert ist, desto
besser kann sie darauf reagieren.

**`Vertiefung`/`Reserve` (und andere wiederholbare Phasen) chronologisch einordnen.** Phasen
dürfen mehrfach vorkommen und müssen keiner festen Reihenfolge folgen (siehe Hauptanleitung)
-- diese Freiheit nutzen: eine Vertiefungsphase gehört an die Stelle im Unterrichtsverlauf,
an der sie inhaltlich tatsächlich stattfindet, nicht pauschal ans Dokumentende. `Reserve`
ist ein flexibel platzierter Puffer, kein fester Stundenabschluss -- sie kann z. B. zwischen
einer Sicherung und der folgenden Vertiefung stehen, wenn dort am ehesten Zeit übrig bleibt,
oder an jeder anderen Stelle, die zur Stundenlogik passt. Ein Dokumentende suggeriert
dagegen fälschlich, `Reserve` sei eine reguläre, feste Abschlussphase.

**`Reserve` nie von unsicheren Fakten abhängig machen.** Der Inhalt einer `Reserve`-Phase
muss unabhängig vom tatsächlichen Verlauf der Stunde ausführbar sein -- nicht auf Dinge
setzen, die vielleicht gar nicht eintreten ("falls noch unzugeteiltes Material übrig ist",
"falls Lernenden spontan ein Beispiel einfällt"). Stattdessen auf garantiert vorhandenes
Material zurückgreifen, z. B. eigene Arbeitsergebnisse aus einer früheren Phase oder
Stunde, die in jedem Fall existieren.

**Gesamtzeit muss der tatsächlichen Stundenlänge entsprechen.** Die Summe der `t=`-Angaben
aller zeitpflichtigen Phasen (Einstieg/Erarbeitung/Ergebnissicherung/Vertiefung -- Hausaufgabe
und Reserve zählen nicht mit) muss der geplanten Gesamtdauer entsprechen, z. B. 90 Minuten
bei einer Doppelstunde, nicht nur einem Teil davon. Nach dem Verteilen der einzelnen `t=`-Werte
die Summe gegenrechnen, bevor der Kurzentwurf als fertig gilt.

Faustregel für die Phasenlänge: möglichst nicht unter ~5 Minuten (`t=2` ist fast immer ein
Signal, dass der Inhalt eigentlich zu einer Nachbarphase gehört) -- sonst wirkt der
Kurzentwurf fragmentierter, als der tatsächliche Unterrichtsverlauf ist.

**Lernaktivitäten (`s<`) nur konstruktiv und überprüfbar, nicht rezeptiv formulieren -- und auf die
kognitive Aktivität fokussieren, nicht auf Spielmechanik/Prozedur.** Was Lernende selbst
tun/herstellen/entscheiden, nicht was sie passiv aufnehmen, und nicht die Ablaufregeln
eines Spiels/Verfahrens:

Prüffrage: Könnte eine beobachtende Person am Ende der Phase feststellen, ob die Aktivität
stattgefunden hat (es liegt ein Ergebnis vor, eine Aussage wurde gemacht, etwas wurde
geordnet)? Wenn nein, ist es keine `s<`-Aktivität. Damit fallen auch Verben für innere,
nicht beobachtbare Vorgänge weg: **sehen, hören, verstehen, wissen, kennenlernen, sich
bewusst machen**. Geeignet sind dagegen z. B. berechnen, vergleichen, ordnen, zuordnen,
begründen, beschreiben, formulieren, skizzieren, überprüfen.

- Vermeiden: `s< lesen den Text.` / `s< hören dem Vortrag zu.` / `s< schauen das Video.`
- Vermeiden: `s< verstehen das Prinzip der Proportionalität.` / `s< wissen, was eine
  Nullstelle ist.`
- Vermeiden (zu viel Spielregel): `s< spielen "Definitionsraten": Person A zeigt eine
  Definition, B und C suchen die passenden Begriffe...`
- Besser: `s< fassen den Text in eigenen Worten zusammen.` / `s< vergleichen Definitionen
  verschiedener Funktionsdimensionen und überprüfen sie auf Gleichheit.`
