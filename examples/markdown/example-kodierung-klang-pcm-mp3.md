---
Titel: Wie Klänge gespeichert werden (PCM und MP3)
Fach: Informatik
Thema: Audiokodierung
Stufe: 7-9
show_student_header: true
show_document_header: true
---

:::material title="Start"
Arbeitszeit: 8-10 Minuten

Ziel: Du verstehst die Grundstrategie der Klangkodierung:
1. Ein analoges Signal wird zeitlich abgetastet (Sampling).
2. Jeder Messwert wird auf Stufen gerundet (Quantisierung).
3. MP3 spart Platz durch psychoakustische Kompression.
:::

:::info
Mini-Merkhilfe:
- Abtastrate: Messungen pro Sekunde (z. B. 44,1 kHz)
- Bittiefe: Genauigkeit pro Messung (z. B. 16 Bit)
- PCM: unkomprimiert, MP3: verlustbehaftet komprimiert
:::

---

:::task points=3 work=single action=calculate
Rechne kurz:
CD-Audio hat 44.100 Samples/s, 16 Bit, Stereo (2 Kanäle).
Wie viele Bit pro Sekunde entstehen unkomprimiert?
:::

:::dots height=4cm
:::

:::solution
44100 x 16 x 2 = 1411200 Bit/s (ca. 1,411 Mbit/s).
:::

---

:::task points=4 work=single action=write
Ergänze den Lückentext sinnvoll.
:::

:::cloze gap=fixed words=below
Bei PCM wird ein analoges Signal in festen Zeitabständen {{abgetastet}}.
Jeder Messwert wird auf eine endliche Zahl von Stufen {{quantisiert}}.
Die Abtastrate beeinflusst die zeitliche Genauigkeit, die {{Bittiefe}} die Wertgenauigkeit.
MP3 nutzt {{psychoakustische}} Effekte und entfernt schwer hörbare Anteile.
Darum ist MP3 meist {{kleiner}}, aber nicht völlig verlustfrei.
:::

---

:::task points=2 work=partner action=decide
Fallentscheidung:
Du willst ein Musikarchiv für späteres Mischen aufbauen.
Wähle: PCM/WAV oder MP3? Begründe kurz.
:::

:::lines rows=3
:::

:::solution
Für Bearbeitung und Archivierung eher PCM/WAV, weil es unkomprimiert und verlustarm ist. MP3 ist besser für platzsparendes Verteilen.
:::

---

:::task points=3 work=single action=reflect
Erkläre in 2-3 Sätzen den Unterschied zwischen
A) "Daten erfassen" und
B) "Daten weglassen, um zu komprimieren".
:::

:::dots height=4cm
:::

:::solution
Erfassen bedeutet, das Signal durch Sampling und Quantisierung digital messbar zu machen. Beim Komprimieren werden danach Redundanzen oder schwer wahrnehmbare Anteile reduziert, um Speicher zu sparen.
:::

---

:::material title="Quellen"
- Wikipedia: Abtastrate. https://de.wikipedia.org/wiki/Abtastrate
- Wikipedia: Quantisierung (Signalverarbeitung). https://de.wikipedia.org/wiki/Quantisierung_(Signalverarbeitung)
- Wikipedia: MP3. https://de.wikipedia.org/wiki/MP3
- Wikipedia (EN): Pulse-code modulation. https://en.wikipedia.org/wiki/Pulse-code_modulation
:::
