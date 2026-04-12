---
Titel: Wie Bilder gespeichert werden (Rastergrafik und JPEG)
Fach: Informatik
Thema: Bildkodierung
Stufe: 7-9
show_student_header: true
show_document_header: true
---

:::material title="Start"
Arbeitszeit: 8-10 Minuten

Ziel: Du verstehst die Grundstrategie der Bildkodierung:
1. Ein Bild besteht aus Pixeln im Raster.
2. Jeder Pixel hat Farbwerte (Farbtiefe).
3. Kompression spart Speicherplatz (z. B. JPEG), oft mit Qualitätsverlust.
:::

:::info
Mini-Merkhilfe:
- Mehr Pixel -> mehr Details, aber größere Datei
- Hohe Farbtiefe -> feinere Farben, aber mehr Daten
- JPEG komprimiert stark, kann Artefakte erzeugen
:::

---

:::task points=3 work=single action=calculate
Rechne kurz:
Ein Bild hat 400 x 300 Pixel und 24 Bit Farbtiefe.
Wie viele Byte braucht es unkomprimiert? (1 Byte = 8 Bit)
:::

:::answer type=dots height=3.5cm
:::

:::solution
400 x 300 = 120000 Pixel.
120000 x 24 Bit = 2880000 Bit.
2880000 / 8 = 360000 Byte (ohne Dateikopf).
:::

---

:::task points=4 work=single action=write
Ergänze den Lückentext sinnvoll.
:::

:::answer type=cloze gap=fixed words=below
Eine Rastergrafik besteht aus vielen {{Pixeln}}.
Die {{Auflösung}} beschreibt, wie viele Pixel insgesamt vorhanden sind.
Die {{Farbtiefe}} legt fest, wie viele Farbwerte pro Pixel möglich sind.
Bei {{JPEG}} werden Daten stark komprimiert, was zu {{Artefakten}} führen kann.
Für Fotos ist JPEG oft geeignet, für harte Kanten ist häufig {{PNG}} besser.
:::

---

:::task points=3 work=partner action=decide
Wähle das passendere Format und begründe kurz.

A) Klassenfoto für Website: JPG oder PNG?
B) Schullogo mit klaren Kanten: JPG oder PNG?
:::

:::answer type=lines rows=4
:::

:::solution
A) Meist JPG, weil Fotos gut komprimiert werden.
B) Meist PNG, weil Kanten sauber bleiben.
:::

---

:::task points=2 work=single action=reflect
Kreuze an: Welche Aussage trifft am besten zu?
:::

:::answer type=mc inline=true
- [ ] Mehr Kompression verbessert immer die Bildqualität.
- [x] Mehr Kompression verkleinert oft die Datei, kann aber Qualität kosten.
- [ ] Die Auflösung hat keinen Einfluss auf die Dateigröße.
:::

---

:::material title="Quellen"
- Wikipedia: Rastergrafik. https://de.wikipedia.org/wiki/Rastergrafik
- Wikipedia: JPEG. https://de.wikipedia.org/wiki/JPEG
- ITU-T Recommendation T.81 (JPEG Standard). https://www.w3.org/Graphics/JPEG/itu-t81.pdf
:::
