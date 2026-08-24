# Stilempfehlungen: Kurzentwurf

Dieses Dokument sammelt Autor:innen-Empfehlungen für die Kurzentwurf-DSL -- im
Unterschied zu [`docs/ANLEITUNG_KURZENTWURF.md`](ANLEITUNG_KURZENTWURF.md) handelt es
sich hier **nicht** um Regeln, die der Validator durchsetzt oder die für ein technisch
gültiges Dokument nötig sind. Zwei unterschiedliche Arten von Empfehlungen sind bewusst
getrennt: reine Schreibkonventionen (wie man den Freitext-Inhalt formatiert) und
didaktische Gestaltungsempfehlungen (pädagogisches Urteil, kein Syntaxbezug).

Nicht codegeneriert (rein redaktionell) und nicht Teil der `assert_prose_coverage`-Prüfung.

## Schreibkonventionen

**Mehrere Antizipationen als Liste darstellen.** Gibt es zu einem Lernschritt mehrere
erwartete Antworten (z. B. eine gute, eine mittelmäßige, eine falsche), diese als
Markdown-Liste innerhalb von `ant<` schreiben statt als einen Fließtext-Satz:

```markdown
ant< - "Photosynthese wandelt Licht in Zucker um." (gut)
      - "Pflanzen brauchen Licht zum Wachsen." (unvollständig)
      - "Pflanzen atmen wie wir." (Fehlvorstellung)
```

**Kein "Schüler:innen"-Subjekt nach `S>`/`s<`.** Der Marker selbst steht bereits für das
Subjekt ("die Lernenden") -- es noch einmal auszuschreiben ist redundant. Prädikat direkt,
klein geschrieben, 3. Person Plural:

- Nicht: `s< Die Schüler:innen formulieren erste Vermutungen.`
- Sondern: `s< formulieren erste Vermutungen.`

**Zeitangaben nicht im Segmentinhalt wiederholen.** `t=`/`start=` am Phasenkopf sind die
einzige vorgesehene Stelle für Zeitangaben. Eine Formulierung wie `U> 10 Minuten
Gruppenarbeit` dupliziert Information, die bereits strukturell in `t=10` steckt, und kann
bei einer späteren Änderung der Phasendauer leicht veralten.

**Material stets mit konkretem Dateinamen.** `U>` ist die richtige Spalte für
Materialangaben (siehe Hauptanleitung) -- innerhalb dieser Spalte den tatsächlichen
Dateinamen nennen, nicht nur eine generische Bezeichnung:

- Weniger hilfreich: `U> Gruppenarbeit; Arbeitsblatt`
- Besser: `U> Gruppenarbeit; Arbeitsblatt_Photosynthese_V2.pdf`

## Didaktische Gestaltungsempfehlungen

**`Vertiefung` (und andere wiederholbare Phasen) chronologisch einordnen.** Phasen dürfen
mehrfach vorkommen und müssen keiner festen Reihenfolge folgen (siehe Hauptanleitung) --
diese Freiheit nutzen: eine Vertiefungsphase gehört an die Stelle im Unterrichtsverlauf,
an der sie inhaltlich tatsächlich stattfindet, nicht pauschal ans Dokumentende.

**Lernaktivitäten (`s<`) nur konstruktiv, nicht rezeptiv formulieren.** Was Lernende
selbst tun/herstellen/entscheiden, nicht was sie passiv aufnehmen:

- Vermeiden: `s< lesen den Text.` / `s< hören dem Vortrag zu.` / `s< schauen das Video.`
- Besser: `s< fassen den Text in eigenen Worten zusammen.` / `s< notieren drei Kernaussagen
  aus dem Vortrag.` / `s< werten die im Video gezeigten Daten aus.`
