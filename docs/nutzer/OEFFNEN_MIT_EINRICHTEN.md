# Blattwerk unter „Öffnen mit" einrichten (.md-Dateien)

Diese Anleitung erklärt, **was** die Einrichtung tut, **wann** du sie ausführst, **wofür** sie gut ist und **wieso** sie so gebaut ist.

## Kurzfassung

1. Einmalig im Blattwerk-Ordner ausführen (PowerShell):
   ```powershell
   .\register-blattwerk-file-association.ps1 -WhatIf   # nur ansehen, nichts wird geändert
   .\register-blattwerk-file-association.ps1           # wirklich eintragen
   ```
2. Rechtsklick auf eine `.md`-Datei → **Öffnen mit** → **Blattwerk**.
3. Läuft Blattwerk schon, erscheint die Datei als neuer Tab im bestehenden Fenster. Es öffnet sich kein zweites Fenster.

Rückgängig machen: `.\unregister-blattwerk-file-association.ps1`

## Wofür ist das gut?

Ohne diese Einrichtung musst du Blattwerk starten und die Datei über „Durchsuchen…" laden. Mit ihr öffnest du ein Arbeitsblatt direkt aus dem Explorer. Weil Blattwerk mehrere Dokumente als Tabs in **einem** Fenster verwaltet, soll jede weitere Datei dort landen und kein neues Fenster erzeugen.

## Was genau ändert das Skript?

Nur Einträge in der Windows-Registry, und nur für **deinen** Windows-Benutzer (`HKEY_CURRENT_USER\Software\Classes`). Dateien werden nicht angelegt oder verändert.

| Eintrag | Wert | Wofür |
|---|---|---|
| `Applications\Blattwerk.exe` → `FriendlyAppName` | `Blattwerk` | Name in der „Öffnen mit"-Liste |
| `Applications\Blattwerk.exe\shell\open\command` | `"…\.venv\Scripts\pythonw.exe" "…\blattwerk.py" "%1"` | Startbefehl; `%1` ist der Pfad der angeklickten Datei |
| `Applications\Blattwerk.exe\DefaultIcon` | `…\assets\app.ico` | Symbol in der Liste (nur wenn die Datei existiert) |
| `Applications\Blattwerk.exe\SupportedTypes` → `.md` | (leer) | Meldet, dass Blattwerk `.md`-Dateien versteht |
| `.md\OpenWithList\Blattwerk.exe` | (leerer Schlüssel) | Bietet Blattwerk für `.md` in der Auswahl an |

Die Pfade in der Tabelle leitet das Skript aus dem Ordner ab, in dem es liegt.

Es setzt Blattwerk **nicht** als Standardprogramm. Ein Doppelklick auf eine `.md`-Datei öffnet sie weiterhin mit dem bisherigen Programm (z. B. VS Code). Blattwerk erscheint nur zusätzlich in der Auswahl.

## Wann musst du es (erneut) ausführen?

- **Einmal**, nachdem Blattwerk eingerichtet ist (`.venv` existiert).
- **Erneut**, wenn du den Blattwerk-Ordner **verschiebst** oder die `.venv` **neu anlegst**. Der gespeicherte Startbefehl zeigt sonst auf einen Pfad, den es nicht mehr gibt; „Öffnen mit → Blattwerk" tut dann nichts.
- Bei Updates von Blattwerk selbst ist nichts nötig, solange der Ordner am selben Ort bleibt.

Mehrfaches Ausführen ist unschädlich: vorhandene Einträge werden aktualisiert, nichts wird doppelt angelegt.

## Wieso ist es so gebaut?

- **`HKEY_CURRENT_USER` statt `HKEY_LOCAL_MACHINE`:** gilt nur für dich, braucht keine Administratorrechte und lässt andere Benutzer und das System unberührt. Es ist jederzeit vollständig rückgängig zu machen.
- **Direkt `pythonw.exe` statt `start-blattwerk.bat`:** eine `.bat` würde bei jedem „Öffnen mit" kurz ein schwarzes Konsolenfenster aufblitzen lassen.
- **Kein Standardprogramm:** Blattwerk ist ein Zusatzangebot, kein Ersatz für deinen Editor.
- **`-WhatIf`:** zeigt vorab jede Änderung, die geschrieben würde, ohne etwas zu ändern.

## Was passiert im Alltag?

- **Blattwerk läuft schon:** Die neue Datei wird als Tab geöffnet, das Fenster kommt nach vorn. Ist die Datei bereits offen, wird nur ihr Tab aktiviert. Es erscheint keine Warnung.
- **Blattwerk läuft noch nicht:** Blattwerk startet und öffnet die Datei. Sie hat Vorrang vor der Einstellung „Beim Start letzte Datei laden".
- **Mehrere Dateien gleichzeitig** (im Explorer markieren → „Öffnen mit"): Windows startet mehrere Prozesse. Der erste wird das Fenster, die anderen geben ihre Datei ab und beenden sich. Alle Dateien landen als Tabs im selben Fenster.
- **Blattwerk ohne Datei starten** (z. B. `start-blattwerk.bat`), obwohl es schon läuft: Es öffnet sich **kein** zweites Fenster, das vorhandene kommt nach vorn.
- **Windows verweigert das In-den-Vordergrund-Holen:** Windows erlaubt Programmen nicht immer, sich selbst nach vorn zu schieben. Dann blinkt Blattwerk in der Taskleiste. Die Datei ist trotzdem geöffnet.
- **Datei existiert nicht mehr:** Es erscheint die Meldung „Datei nicht gefunden", es wird kein leerer Tab angelegt.

Auch die Kommandozeile funktioniert: `start-blattwerk.bat "C:\Pfad\zum\Blatt.md"` oder `.venv\Scripts\pythonw.exe blattwerk.py "C:\Pfad\zum\Blatt.md"`. Relative Pfade werden vom Startort aus aufgelöst.

## Technik im Überblick (für Neugierige)

Jeder Blattwerk-Start versucht als Erstes, den Port `127.0.0.1:47653` zu belegen (nur dein eigener Rechner, nicht im Netzwerk erreichbar). Wer ihn bekommt, wird das Fenster. Alle anderen Starts (auch mehrere gleichzeitig) schicken ihren Dateipfad dorthin und warten auf eine Bestätigung, dass das Fenster lebt. Erst danach beenden sie sich. Bleibt die Bestätigung aus (z. B. weil die erste Instanz hängt oder etwas anderes den Port belegt), starten sie einfach ganz normal ein eigenes Fenster. Es geht also nie eine Datei „still" verloren. Übertragen wird nur der Dateipfad, keine Inhalte.

## Fehlersuche

| Problem | Ursache / Lösung |
|---|---|
| „Blattwerk" fehlt in „Öffnen mit" | Explorer-Fenster schließen und neu öffnen; sonst einmal ab- und wieder anmelden. Bei Windows 11: im Kontextmenü ggf. „Weitere Optionen anzeigen" wählen. |
| PowerShell meldet „Skriptausführung ist deaktiviert" | `powershell -ExecutionPolicy Bypass -File .\register-blattwerk-file-association.ps1` (gilt nur für diesen einen Aufruf). |
| Skript meldet „Blattwerk-Umgebung fehlt" | Erst die `.venv` einrichten (siehe `README.md`), dann erneut ausführen. |
| „Öffnen mit → Blattwerk" tut nichts | Ordner verschoben oder `.venv` neu angelegt: Skript erneut ausführen. |
| Zweites Fenster statt Tab | Die erste Instanz war beim zweiten Start gerade beschäftigt oder hing länger als ~30 Sekunden; oder eine ältere Blattwerk-Version ohne diese Funktion läuft noch. Alle Blattwerk-Fenster schließen und neu starten. |

## Hinweis zur Prüfung

Die Übergabe zwischen zwei Blattwerk-Starts, das Öffnen als Tab und beide Skripte sind automatisiert bzw. gegen einen Test-Registry-Schlüssel geprüft. Ob der Windows-Explorer den Eintrag tatsächlich in „Öffnen mit" anzeigt, hängt von der Windows-Version ab und lässt sich nur nach dem echten Einrichten am eigenen Rechner bestätigen (Rechtsklick auf eine `.md`-Datei).
