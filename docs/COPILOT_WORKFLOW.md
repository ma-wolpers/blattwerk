# Copilot Workflow (Blattwerk)

Ziel: Du sagst nur, was fachlich getan werden soll. Copilot setzt Code und Pflicht-Dokumentation im selben Zyklus um.

## Standard-Prompt (empfohlen)

Nutze diese Formulierung am Anfang eines Tickets:

"Setze folgende Aenderung um: <Beschreibung>. Halte Guardrails ein, aktualisiere alle Pflichtdokumente (Architektur nur bei Regel-/Schnitt-Aenderung, Development-Log bei Feature/Architektur, Changelog bei nutzerrelevanten Aenderungen), fuehre relevante Checks aus und nenne mir am Ende exakt, was geaendert wurde."

## Was Copilot dabei automatisch mitziehen soll

1. Code-Aenderung im betroffenen Modul.
2. `docs/DEVELOPMENT_LOG.md` bei Feature-/Architektur-Aenderung.
3. `docs/ARCHITEKTUR.md` und `docs/ARCHITEKTUR_EINFACH.md` nur bei echter Architektur-Regelaenderung.
4. `CHANGELOG.md` bei nutzerrelevanter Aenderung.
5. PR-Checkliste in `.github/pull_request_template.md` beachten.

## Wann du kurz praezisieren solltest

1. Wenn unklar ist, ob etwas nur Bugfix oder bereits Feature ist.
2. Wenn eine Aenderung mehrere Schichten betrifft (Core, UI, Storage).
3. Wenn Release-Note-Text eine bestimmte Formulierung haben soll.

## Minimaler Review-Check (30 Sekunden)

1. Sind Code und Doku im selben Zyklus aktualisiert?
2. Ist `docs/DEVELOPMENT_LOG.md` aktualisiert (falls Feature/Architektur)?
3. Ist `CHANGELOG.md` aktualisiert (falls nutzerrelevant)?
4. Sind die Guardrail-/Test-Checks gruen?

## Verbindliche Quellen in Blattwerk

1. Guardrails: `AGENTS.md`
2. Copilot-Regeln: `.github/copilot-instructions.md`
3. Architektur Ist-Zustand: `docs/ARCHITEKTUR.md` und `docs/ARCHITEKTUR_EINFACH.md`
4. Entwicklungsverlauf: `docs/DEVELOPMENT_LOG.md`
5. Oeffentliche Kommunikation: `CHANGELOG.md`
