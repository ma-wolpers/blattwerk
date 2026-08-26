# Stilempfehlungen: Arbeitsblatt & Präsentation

Dieses Dokument sammelt reine Autor:innen-Stilpräferenzen für den `:::`-Blockdialekt --
im Unterschied zu [`docs/nutzer/ANLEITUNG_ARBEITSBLATT_PRAESENTATION.md`](ANLEITUNG_ARBEITSBLATT_PRAESENTATION.md)
handelt es sich hier **nicht** um Regeln, die der Validator durchsetzt oder die für ein
korrekt funktionierendes Dokument nötig sind. Nichts hier ist "falsch", wenn man es
anders macht -- es ist einfach die empfohlene Schreibweise für konsistente, gut lesbare
Blattwerk-Quelltexte.

Nicht codegeneriert (rein redaktionell) und nicht Teil der `assert_prose_coverage`-Prüfung.

## Kompakte Schreibweise für inhaltslose Blöcke

Blöcke ohne Inhalt (`nextcol`, `endcolumns`, `pagebreak`-artige Marker o. ä.) auf einer
einzigen Zeile schreiben, öffnendes und schließendes `:::` zusammen:

```markdown
:::nextcol :::
```

statt der mehrzeiligen Form

```markdown
:::nextcol
:::
```

Beide Formen sind vom Parser gleichwertig akzeptiert (siehe Grundregel in der
Hauptanleitung) -- die einzeilige Form ist einfach kompakter und macht auf einen Blick
sichtbar, dass hier bewusst kein Inhalt folgt.

## Immer den passendsten Blocktyp wählen

Blattwerk hat für die meisten Aufgabentypen einen dedizierten Blocktyp -- diesen nutzen,
statt ihn mit einem generischeren Block nachzubauen. Zum Beispiel:

- Multiple-Choice-/Wahr-Falsch-Fragen → `:::mc`, nicht `:::task` mit handgeschriebener Liste.
- Zuordnungsaufgaben → `:::matching`, nicht `:::table` mit zwei Spalten.
- Lückentexte → `:::cloze`, nicht `:::task` mit Freitext-Lücken.

Die dedizierten Blocktypen bringen automatisches Layout, konsistente Lösungsdarstellung
und (wo zutreffend) Validierung mit -- ein nachgebauter Block über einen generischeren
Typ verliert diese Vorteile, auch wenn er optisch ähnlich aussehen mag.
