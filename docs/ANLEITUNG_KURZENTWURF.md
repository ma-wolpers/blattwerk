<!--
Automatisch generiert aus app/core/markdown_conventions.py.
NICHT VON HAND BEARBEITEN.
Neu erzeugen: python tools/docs/generate_authoring_guides.py
-->

# Kurzentwurf erstellen

Kurzentwurf ist ein eigener Blattwerk-Dokumenttyp mit einer **eigenen DSL** -- nicht dem `:::`-Blockdialekt aus der Arbeitsblatt-/Präsentations-Anleitung. Diese Anleitung wird automatisch aus dem Code erzeugt (`app/core/markdown_conventions.py`).

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

Ein Kurzentwurf gliedert sich in `#phase`-Abschnitte, deren Name einer der sechs festen Unterrichtsphasen entsprechen muss (siehe Liste unten), z. B. `#einstieg t=10` für eine 10-minütige Einstiegsphase. `t=<minuten>` ist optional; ohne Zeitangaben wird die Phase ohne Zeitlabel gerendert. `Hausaufgabe` und `Didaktische Reserve` benötigen nie ein `t=...`.

Zulässige Phasennamen:

- `Einstieg`
- `Erarbeitung`
- `Ergebnissicherung`
- `Vertiefung`
- `Hausaufgabe`
- `Didaktische Reserve`

## 4. Zeilenmarker innerhalb einer Phase

Innerhalb einer Phase gliedern Zeilenmarker den Inhalt in drei Spalten: `S>` (Lernschritte), `A>` gefolgt von `s<` (Lernaktivität der Lernenden) und `U>` (Lernumgebung/Sozialform). `ant<` markiert eine antizipierte Schülerreaktion/Fehlvorstellung zum jeweiligen Lernschritt und sollte nach jedem `s<` gesetzt werden. `---` trennt zwei Segmente innerhalb derselben Phase; `|` allein auf einer Zeile springt zur nächsten Spalte.

## 5. Legacy-Erkennungs-Felder (nicht aktiv verwenden)

Diese Felder werden derzeit ausschließlich zur Erkennung älterer Kurzentwurf-Dokumente berücksichtigt (falls kein explizites `document_type: kurzentwurf` gesetzt ist). Sie steuern weder Inhalt noch Darstellung des gerenderten Kurzentwurfs und sollten für neue Dokumente nicht als funktionale DSL-Felder verwendet, sondern höchstens als rein organisatorische Notiz betrachtet werden.

Betroffene Felder: `Dauer`, `Kompetenzen`, `Material`, `Oberthema`, `Stundentyp`, `Stundenziel`, `Teilziele`, `Unterrichtsbesuch`.
