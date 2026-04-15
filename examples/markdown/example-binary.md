---
Titel: Binäre Codierung – Grundlagen
Fach: Informatik
Thema: Binäre Codierung
Stufe: 7–8
worksheet_type: Arbeitsblatt
show_student_header: false
---

:::material
In Computern werden Informationen nicht mit Buchstaben oder Zahlen gespeichert, sondern mit **Bits**.

Ein **Bit** kann genau zwei Zustände annehmen:
- 0 (aus)
- 1 (an)

Mehrere Bits zusammen nennt man eine **Binärzahl**.
:::

:::columns cols=2 widths="2 1" gap=1cm :::

![Alternativtext](../assets/testbild.png "w=100%")

:::nextcol :::

:::info
**Merke:**  
Je mehr Bits zur Verfügung stehen, desto mehr unterschiedliche Informationen können dargestellt werden.
:::

:::endcolumns :::

--

:::columns cols=2 gap=0.6cm :::

:::material title="Kurzinfo"
Die Potenzen von 2:

- 1 - 2 - 4 - 8 - 16 - 32 - 64 - 128 - 256
:::

:::nextcol :::

:::task points=1 work=partner action=exchange hint=tip
Ordne den Potenzen passende Binärstellen zu.
:::

:::lines rows=3
:::

:::solution
1 = 0001, 2 = 0010, 4 = 0100, 8 = 1000
:::

:::endcolumns :::

---

:::task points=2 work=single action=read hint=remember
Kreuze an, welche der folgenden Aussagen richtig sind.
:::

:::grid_field rows=4
:::

:::solution
Mögliche richtige Aussagen:
- Binärzahlen bestehen nur aus 0 und 1.
- Ein Bit kann genau zwei Zustände darstellen.
:::

---

:::material
### Beispiel: Binärzahlen

:::table rows=6 cols=2 row_height=1.0cm headers=Dezimal|Binär alignment=right
cells:
	-
		- { text: "Beispielwerte", colspan: 2 }
	- ["1", "0001"]
	- ["2", "0010"]
	- ["3", "0011"]
	- ["4", "0100"]
	- ["5", "0101"]
:::
:::

---

:::info type=note
Tipp: Du darfst dir beim Rechnen eine Stellenwerttabelle (1, 2, 4, 8, 16, …) aufzeichnen.
:::

:::task points=3 work=partner action=calculate hint=definition
Wandle die folgenden Dezimalzahlen in Binärzahlen um.
:::

:::lines rows=5
§ Rechenhilfe: Nutze eine Stellenwerttabelle (1, 2, 4, 8, ...).
5 -> 0101 $
& Achte auf führende Nullen.
:::

:::solution
Beispiel-Lösungen:
- 5 → 0101
- 7 → 0111
- 9 → 1001
:::

---

:::task
Wandle die folgenden Binärzahlen in Dezimalzahlen um.
:::

:::lines rows=5
§ Starte mit der größten Zweierpotenz.
0101 -> 5 $
& Addiere nur aktive Stellen (Bit = 1).
:::

:::solution
Beispiel-Lösungen:
- 0101 → 5
- 1000 → 8
- 1011 → 11
:::

---

:::task work=group action=write hint=expert
Ein Computer speichert Buchstaben mithilfe von Zahlen.

Erkläre **in eigenen Worten**, warum eine feste Codierung für Buchstaben notwendig ist.
:::

:::dots height=6cm
§ Eine feste Codierung ist nötig, weil ...
Ohne Normen würden Geräte Zahlen unterschiedlich deuten. $
:::

:::solution
Ohne feste Codierung würden unterschiedliche Geräte denselben Zahlenwert als verschiedene Zeichen interpretieren. Eine Norm (z. B. ASCII/Unicode) stellt sicher, dass Text überall gleich gelesen wird.
:::

---

:::task points=4
Ein System verwendet **3 Bits** zur Codierung.

1. Wie viele verschiedene Zustände sind möglich?  
2. Reichen 3 Bits aus, um alle Buchstaben des Alphabets zu speichern? Begründe.
:::

:::dots height=7cm
:::

:::solution
1. Mit 3 Bits sind $2^3 = 8$ Zustände möglich.
2. Nein, 8 Zustände reichen nicht für 26 Buchstaben (ohne Sonderzeichen).
:::

---

:::task points=2 work=single action=read
*Kreuze* an, welche Aussage zum EVA-Prinzip korrekt ist.
:::

:::mc inline=true
EVA steht für ...
- [x] Eingabe, Verarbeitung, Ausgabe
- [ ] Erfassen, Verteilen, Archivieren
- [ ] Einlesen, Vergleichen, Abspeichern
Diese Multiple-Choice-Aufgabe finde ich...
- [x] unpassend zur Aufgabenstellung.
- [ ] fantastisch.
- [x] emotional verwirrend.
Das ist richtig.
- [x] richtig
- [ ] falsch
:::

:::task points=2 work=single action=write
*Ergänze* den Lückentext zum EVA-Prinzip.
:::

:::cloze gap=fixed words=below
Bei der {{Eingabe}} werden Daten aufgenommen, in der {{Verarbeitung}} umgewandelt und bei der {{Ausgabe}} angezeigt.
:::
