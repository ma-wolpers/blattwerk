# Blattwerk Architektur (einfach)

Diese Datei erklärt die Architektur in einfacher Sprache.

Wichtig:
Sie muss immer zusammen mit [docs/ARCHITEKTUR.md](docs/ARCHITEKTUR.md) geändert werden.

Dokumentrollen:
- Die beiden Architekturdateien zeigen nur den aktuellen Zustand.
- Der Aenderungsverlauf steht nur in [docs/DEVELOPMENT_LOG.md](docs/DEVELOPMENT_LOG.md).

## Die Grundidee

Blattwerk hat klare Schichten.
Jede Schicht hat eine Aufgabe.
So vermeiden wir Klebercode und Verwirrung.

## Wer macht was?

- `app/core`
  - Das ist der Programmkern.
  - Hier werden fachliche Entscheidungen getroffen.
  - Parse, Validate, Render und Build passieren hier.

- `app/ui`
  - Hier ist die Oberfläche.
  - Sie nimmt Eingaben an und zeigt Ergebnisse.
  - Sie soll keine Fachregeln erfinden.
  - Geoeffnete Markdown-Dateien laufen als Tabs in einer Dokumentleiste; jedes Blatt bleibt als eigener UI-Zustand erhalten.
  - Beim Tab-Wechsel stellt die UI dokumentbezogene Vorschau-Einstellungen wieder her (z. B. Aufgabe/Loesung, DIN A4/A5, Kontrast und Gestaltung).
  - Beim Tab-Wechsel werden auch Zoom, aktive Seite und Scrollposition des jeweiligen Blatts wiederhergestellt.
  - Vorschauseiten werden pro Tab zwischengespeichert und bei unveraenderten Dateien/Optionen ohne erneutes Kompilieren wiederverwendet.
  - Alle Oeffnungswege (Dateidialog, Recent-Menue, Shortcut `Z`) laufen ueber denselben UI-Dispatcher; bereits offene Dateien werden fokussiert statt doppelt geoeffnet.
  - Das Hauptfenster kann Vorschau und Schreibbereich einzeln oder zusammen anzeigen.
  - Der Schreibbereich speichert Aenderungen debounced direkt in die Markdown-Datei.
  - Der Schreibbereich zeigt Live-Diagnostik aus dem Programmkern (Validator) und markiert nur betroffene Zeilen in der UI.
  - Syntax-Highlighting und Completion sind UI-Funktionen; ihre fachlichen Vorschlagsquellen kommen weiterhin aus dem Programmkern.
  - Completion-Kandidaten kommen zentral aus `app/core/completion_catalogs.py`; die UI hält dafür keine eigenen statischen Fachlisten.
  - Als Folding-Ersatz gibt es eine Struktur-Outline im UI, die direkt zu Frontmatter/Blockstellen springt.
  - Die Vorschau wird weiterhin bewusst manuell aktualisiert.

- `app/storage`
  - Hier werden Daten gespeichert und geladen.
  - Pfade und Konfigurationswerte werden hier normalisiert.

- `app/styles`
  - Hier werden Profile und Designregeln aufgelöst.
  - Hier gehört das Aussehen hin, nicht die Fachlogik.

- `app/cli`
  - Das ist ein Adapter für Werkzeuge wie die Diagnostik-CLI.

## Was heißt Programmkern konkret?

Im Kern läuft immer dieselbe Reihenfolge:
1. Dokument lesen und parsen
2. Dokument prüfen (validieren)
3. Dokument rendern
4. Ausgabe bauen (HTML/PDF)

Zusatz im Kern:
- Warntexte aufbereiten (`diagnostic_warnings.py`)
- Typisierte Build-Anfragen (`build_requests.py`)
- Fachregel für BW/Farbhinweise (`color_mentions.py`)

## Was ist verboten?

- Blindes Retry mit pauschalem Sleep
- Doppelte Parser-Logik in verschiedenen Modulen
- Stille Fallbacks ohne klaren Vertrag
- Fachentscheidungen in der UI

## Was ist als Ausnahme erlaubt?

Retries sind erlaubt, wenn alle Punkte gelten:
- nur an I/O-Grenzen
- nur bei transienten, klassifizierten Fehlern
- begrenzt und mit klarer Fehlermeldung bei Abbruch

## Wie prüfen wir, ob die Architektur gut ist?

Frage 1: Macht die GUI nur Input/Output und View-State?
- Soll: Ja.

Frage 2: Werden Speichermodule konsequent benutzt?
- Soll: Ja, pro Ressource eine führende API.

Frage 3: Weiß jedes Modul nur das Nötige?
- Soll: Ja, nach Schichtgrenzen.

## Dokumentgrenze

Diese Datei ist kein Aenderungsprotokoll.
"Was wurde wann geaendert" steht nur im Development-Log.

## Guardrails (Build, Export, CI)

1. Die Diagnostik-CLI hat klare Modi:
  - `--mode standard`: blockiert kritische Diagnostik
  - `--mode strict`: blockiert jede Diagnostik
  - `--mode permissive`: blockiert nur Fehler (`severity=error`)
2. Export-Regeln bleiben im Kern:
  - Die UI liefert nur Eingaben
  - Ob ein Build blockiert, entscheidet nicht die UI
  - Exportziele werden vor dem Schreiben zentral geprüft
  - interne Technikordner wie `.git` oder `.venv` sind als Ziel gesperrt
3. Persistierte JSON-Pfade im Repo bleiben portabel:
  - keine absoluten Systempfade in getrackten State-JSON-Dateien
  - CI prüft das über `tools/repo_ci/check_no_absolute_paths.py`
4. Bildpfade in Markdown bleiben portabel:
  - der Validator meldet absolute lokale Bildpfade als `PT001`
  - relative Pfade und Web-URLs bleiben erlaubt
5. Development-Log ist Pflicht:
  - keine Feature- oder Architekturänderung ohne Eintrag in [docs/DEVELOPMENT_LOG.md](docs/DEVELOPMENT_LOG.md)
  - der Eintrag passiert im gleichen Arbeitszyklus

## Regel vor jedem Merge

1. Wer entscheidet fachlich?
2. Passen die Schichtgrenzen?
3. Wird eine Brute-Force-Regel verletzt?
4. Wurden beide Architekturdateien zusammen aktualisiert?
5. Wurde bei Feature- oder Architekturänderung [docs/DEVELOPMENT_LOG.md](docs/DEVELOPMENT_LOG.md) aktualisiert?
