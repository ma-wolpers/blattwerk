---
Titel: Antwortformate – Erweiterte Beispiele
Fach: Mathematik
Thema: Grid, Dots, Table mit Lösungsausgabe
Stufe: 8
show_student_header: true
show_document_header: true
---

:::material title="Hinweise zum Testen"
Dieses Dokument zeigt die neuen erweiterten `answer`-Möglichkeiten.

Empfohlener Testlauf in der UI:

1. **Arbeitsblatt** exportieren (ohne Lösung)
2. **Lösung** exportieren
3. **Arbeitsblatt + Lösung** exportieren

Achte dabei besonders auf:

- Overlay-Verhalten bei `lines`, `dots`, `grid`
- `%{...}`-Markierungen in `table`-Zellen
- markerbasierte Sichtbarkeit bei Grid- und Numberline-Elementen (`show: "§"|"%"|"&"`)
- Zahlengeraden mit `labels` und `answers`
:::

---

:::task points=3 work=single action=write
Notiere die Ergebnisse in das Linienfeld.
:::

:::answer type=lines rows=5
§ Ich rechne schrittweise ...
1) 2^5 = 32 $
& Kontrolliere am Ende alle Vorzeichen.
:::

:::task points=3 work=single action=write
Notiere im Punktfeld drei kurze Merksätze.
:::

:::answer type=dots height=5cm
§ Formulierungshilfe: "Ein Koordinatensystem ..."
Die x-Achse verläuft waagerecht. $
& Die y-Achse verläuft senkrecht.
:::

---

:::task points=4 work=single action=draw hint=tip
Markiere im Raster die angegebenen **Rasterpunkte** (ohne Koordinatensystem).
:::

:::answer type=grid rows=12 cols=18
points:
  - {col: 2, row: 2, label: "R1"}
  - {col: 10, row: 4, label: "R2"}
  - {col: 16, row: 9, label: "R3", show: "%"}
:::

:::info type=note
Im ersten Grid beziehen sich die Punkte auf **Rasterkoordinaten** (`col`, `row`), weil `axis` fehlt.
:::

---

:::task points=6 work=single action=calculate hint=definition
Arbeite mit dem Koordinatensystem:

1. Trage die Punkte A, B, C ein.
2. Lies die Funktionswertepaare ab.
3. Zeichne den Graphen von $y = x^2 - 2$ im angegebenen Bereich.
:::

:::answer type=grid rows=20 cols=20 axis=true origin="10,10" step_x=0.5 step_y=1
points:
  - {x: -3, y: 4, label: "A", show: "&"}
  - {x: 2, y: 3, label: "B", show: "&"}
  - {x: 4, y: -1, label: "C", show: "%"}

pairs:
  - {x: -2, y: 2, label: "P1", show: "§"}
  - {x: -1, y: -1, label: "P2", show: "§"}
  - {x: 0, y: -2, label: "P3", show: "§"}
  - {x: 1, y: -1, label: "P4", show: "%"}
  - {x: 2, y: 2, label: "P5", show: "%"}

functions:
  - {expr: "x^2-2", domain: "-4:4", show: "%"}
  - {expr: "0.5*x+1", domain: "-6:6", show: "§"}
:::

:::info
Hier gilt wegen `axis=true`:

- `points` und `pairs` nutzen Koordinaten (`x`, `y`)
- `functions` werden nur bei vorhandenem Koordinatensystem gezeichnet
- `x^2` und `x**2` sind beide möglich
:::

---

:::task points=5 work=single action=calculate
Lies die Zahlengerade und ergänze die fehlenden Werte in den markierten Kästchen.
:::

:::answer type=numberline min=-1.5 max=4.5 tick_spacing_cm=1 major_every=2 height=2.9cm
labels:
  - {value: -1.5, show: "&"}
  - {value: 0, show: "&"}
  - {value: 4.5, show: "&"}
  - {value: 2, text: "2", show: "§"}
answers:
  - {value: -0.5}
  - {value: 1.5}
  - {value: 3.5}
:::

---

:::task points=5 work=partner action=exchange
Vervollständigt die Tabelle. Inhalte in `%{...}` sind nur für die Lösung gedacht.
:::

:::answer type=table rows=5 cols=3 row_height=1.8cm headers="Signal|Bauteil|Funktion"
cells:
  - ["Taster", "Eingabe", "%{startet den Stromkreis}"]
  - ["LED", "Ausgabe", "%{zeigt den Zustand an}"]
  - ["", "Widerstand", "begrenzt Strom"]
  - ["Sensor", "%{Eingabe}", "liefert Messwert"]
  - ["", "", ""]
solution: |
  Zusatzhinweis (nur in der Lösungsversion):
  Prüft besonders die Fachbegriffe **Eingabe**, **Ausgabe** und **Signalfluss**.
:::

---

:::task points=2 work=single action=read
Optionaler Freitextbereich mit Lösungstext direkt im `space`-Block.
:::

:::answer type=space height=3.2cm
§ Satzstarter: "Der Signalfluss beginnt bei ..."
Der Signalfluss verläuft von der Eingabe über die Verarbeitung zur Ausgabe. $
& Verwende die Begriffe Eingabe, Verarbeitung, Ausgabe.
:::
