---
Titel: Zahlengerade mit vier Zielzahlen
Fach: Mathematik
Thema: Ganze Zahlen auf der Zahlengeraden
Stufe: 6
show_student_header: true
show_document_header: true
---

:::task points=4 work=single action=draw
Markiere die vorgegebenen Zahlen auf der Zahlengeraden.
:::

:::numberline min=-22 max=32 tick_step=1 major_every=5 height=2cm
labels:
  - {value: -20, show: "&"}
  - {value: -10, show: "&"}
  - {value: 0, show: "&"}
  - {value: +20, show: "&"}
  - {value: +10, show: "&"}
  - {value: +30, show: "&"}
:::

---

:::task points=4 work=single action=calculate
Lies die Werte der markierten Kästchen ab und ergänze sie.
:::

:::numberline min=-17 max=33 tick_step=1 tick_spacing_mm=5 major_every=5 height=3.1cm
labels:
  - {value: -17, show: "§"}
  - {value: 33, show: "§"}
answers:
  - {value: -7}
  - {value: 13}
arcs:
  - {from: -17, to: -7, label: "?", side: above, arrow: true, show: "§"}
  - {from: -7, to: 13, label: "?", side: above, arrow: true, show: "§"}
  - {from: -17, to: -7, label: "+10", side: above, arrow: true, show: "%"}
  - {from: -7, to: 13, label: "+20", side: above, arrow: true, show: "%"}
solution: |
  Die gesuchten Werte sind -7 und 13.
:::
