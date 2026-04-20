---
Titel: Wie Text im Computer gespeichert wird (UTF-8)
Fach: Informatik
Thema: Textkodierung
Stufe: 7-9
show_student_header: true
show_document_header: true
---

:::material title="Start"
Arbeitszeit: 8-10 Minuten

Ziel: Du verstehst die Grundstrategie der Textkodierung:
1. Zeichen bekommen Nummern (Codepunkte).
2. Diese Nummern werden als Bytes gespeichert (z. B. in UTF-8).
3. Eine gemeinsame Norm verhindert Zeichensalat.
:::

:::info
Mini-Merkhilfe:
- Codepunkt = Nummer eines Zeichens (z. B. U+0041 für A)
- UTF-8 = Speicherformat für diese Nummern
- ASCII = alte Teilmenge für Basiszeichen
:::

---

:::task points=3 work=single action=match
Ordne die Begriffe zu.
:::

:::grid rows=3
::: 

:::solution
- Codepunkt -> abstrakte Zeichennummer
- UTF-8 -> speichert Zeichen als 1 bis 4 Byte
- ASCII -> 7-Bit-Standard, in UTF-8 enthalten
:::

---

:::task points=4 work=single action=write
Ergänze den Lückentext sinnvoll.
:::

:::cloze gap=fixed words=below
Unicode vergibt für jedes {{Zeichen}} eine eindeutige {{Nummer}}.
Diese Nummer heißt {{Codepunkt}}.
Damit der Computer sie speichern kann, wird sie mit einem Format wie {{UTF-8}} in {{Bytes}} umgewandelt.
Die ersten 128 Zeichen sind identisch mit {{ASCII}}.
Ohne gemeinsame Kodierung entstehen leicht {{Zeichensalat}} oder falsch dargestellte {{Umlaute}}.
:::

---

:::task points=3 work=partner action=decide
Kurzfall: Zwei Klassen tauschen Texte aus.

Klasse A speichert als UTF-8, Klasse B als altes lokales Format.
Was ist die beste Strategie? Kreuze an und begründe in 2 Sätzen.
:::

:::mc inline=true
- [ ] Jede Klasse nutzt weiter ihr eigenes Format.
- [x] Beide Klassen nutzen durchgängig UTF-8.
- [ ] Klasse A entfernt alle Sonderzeichen.
:::

:::dots height=3.5cm
:::

:::solution
Richtig ist UTF-8 für beide Klassen, weil dann dieselben Zeichen gleich interpretiert werden. So bleiben Umlaute, Sonderzeichen und verschiedene Sprachen stabil lesbar.
:::

---

:::task points=2 work=single action=reflect
Prüfe dein Verständnis: Schreibe eine 20-Sekunden-Erklärung.

"Warum braucht man bei Texten eine Normkodierung?"
:::

:::dots height=3cm
:::

:::solution
Eine Normkodierung sorgt dafür, dass dieselbe Bytefolge auf verschiedenen Geräten als dasselbe Zeichen gelesen wird.
:::

---

:::material title="Quellen"
- Unicode Consortium: What is Unicode? https://www.unicode.org/standard/WhatIsUnicode.html
- IETF RFC 3629: UTF-8, a transformation format of ISO 10646. https://www.rfc-editor.org/rfc/rfc3629
- Encyclopaedia Britannica: ASCII. https://www.britannica.com/technology/ASCII
:::
