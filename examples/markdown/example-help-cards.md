---
Titel: Hilfekarten-Test
Fach: Informatik
Thema: Primzahlen und Teilbarkeit
show_document_header: true
show_student_header: true
---

# Hilfe-Block Demo

Diese Seite enthält normale Inhalte **und** Hilfeblöcke.
Im Hauptfenster siehst du alles, im zweiten Fenster nur die Hilfekarten.

:::task points=2 work=single action=read
Lies die Definition einer Primzahl und erkläre sie in eigenen Worten.
:::

:::help title="Hilfe 1: Definition" level=1
Eine Primzahl hat **genau zwei** positive Teiler: `1` und sich selbst.

Beispiele: `2`, `3`, `5`, `7`, `11`.
:::

:::help title="Hilfe 2: Prüfschema" level=2
So kannst du prüfen, ob `n` prim ist:

1. Starte bei `2`.
2. Prüfe Teilbarkeit bis einschließlich $\sqrt{n}$.
3. Wenn kein Teiler gefunden wird: prim.
:::

:::hilfe title="Hilfe 3: Beispielrechnung" level=3
Prüfe `n = 29`:

- $\sqrt{29} \approx 5{,}38$
- Teste nur `2`, `3`, `5`
- 29 ist durch keinen dieser Werte teilbar

**Also ist 29 eine Primzahl.**
:::

:::info type=note
Du kannst auch `show=solution` oder `show=worksheet` in Help-Blöcken setzen,
um sie abhängig vom Modus ein-/auszublenden.
:::
