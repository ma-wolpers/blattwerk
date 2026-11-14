# Fachkonventionen Mathematik

Diese Datei sammelt fachwissenschaftliche Festlegungen (Schreibweisen, Definitionen, Konventionen), die in allen Mathematik-Materialien einheitlich gelten sollen – in Aufgaben genauso wie in Musterlösungen. Didaktische und gestalterische Regeln für Arbeitsblätter stehen dagegen in `docs/intern/ARBEITSBLATT_NOTIZEN.md`.

## Definitionsmengen

- Definitionsmengen immer kanonisch als Menge angeben, nicht in Worten, und immer mit Doppelstrich-D (`\mathbb{D}`):

  | Schreibweise | Bedeutung |
  |---|---|
  | $\mathbb{D}=\mathbb{R}$ | alle reellen Zahlen |
  | $\mathbb{D}=\mathbb{R}\setminus\{0\}$ | alle reellen Zahlen außer $0$ |
  | $\mathbb{D}=\mathbb{R}^+$ | nur die positiven Zahlen |
  | $\mathbb{D}=\mathbb{R}^+_0$ | die nicht negativen Zahlen ($x\ge0$) |

## Potenzen mit Bruch-Exponent

- Potenzen mit Bruch-Exponent ($x^{\frac{1}{n}}$, allgemein $x^{\frac{m}{n}}$) sind **immer nur für $x\ge0$** definiert, auch bei ungeradem Nenner. Also z. B. $x^{\frac13}$ mit $\mathbb{D}=\mathbb{R}^+_0$.
- Grund: Nur so bleiben die Potenzgesetze widerspruchsfrei. Der Wert darf nicht davon abhängen, wie der Bruch im Exponenten geschrieben wird, z. B. $x^{\frac13}=x^{\frac26}=(x^2)^{\frac16}$. Für $x=-8$ ergäbe das links $-2$, rechts aber $64^{\frac16}=2$.
- Das Wurzelzeichen ist von dieser Festlegung nicht betroffen: $\sqrt[3]{-8}=-2$ ist in Ordnung. Die Einschränkung gilt nur für die Potenzschreibweise.
