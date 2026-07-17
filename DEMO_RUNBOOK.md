# Hyperion Juno Demo Runbook

Dieses Runbook beschreibt die kurze, mittlere und ausfuehrliche Vorfuehrung
der iPad-Demo. Alle Daten werden lokal erzeugt; ein Netzwerkzugang und ein
externer KI-Dienst sind nicht erforderlich.

## Einmalige Einrichtung in Juno

1. Den Projektordner in Juno oeffnen.
2. `Juno_Story_Capsule.ipynb` starten.
3. Optional `bokeh` und `ipywidgets` ueber den Juno-Paketmanager installieren.
4. Die Zellen von oben nach unten ausfuehren.

## Demo-Modus am Anfang

In der ersten Auswahlzelle stehen drei Profile bereit:

- `einsteiger`: 3 Minuten, 8 Episoden, 8 Jahre, Agentenrat und Szenarien.
- `agentenvergleich`: 8 Minuten, 20 Episoden, 12 Jahre, zusaetzlich ein
  kurzer Flight Recorder.
- `tiefenanalyse`: 20 Minuten, 50 Episoden, 20 Jahre, Routenkarte, voller
  Flight Recorder und Capsule-Export.

Nach einer Dropdown-Auswahl die Zellen ab `Der Agentenrat` erneut ausfuehren.
Ohne `ipywidgets` kann `DEMO_MODE` in der ersten Notebook-Zelle direkt gesetzt
werden.

Wenn Bokeh nicht verfuegbar ist, bleiben Tabellen und CSV-Exporte nutzbar.
Die bestehende Matplotlib-Demo in `Juno_Demo.ipynb` ist der visuelle Fallback.

## 3-Minuten-Story

1. Agentenrat anzeigen: Rendite-Sucher, Reservenwaechter und Opportunist.
2. Lernfortschritt oder die Zusammenfassung der Endwerte zeigen.
3. Einen Satz zur Einordnung geben: Die Agenten sind lokale, erklaerbare
   Lernmodelle und keine externe Black-Box-KI.

## 8-Minuten-Story

1. Im Scenario Composer `farcaster_stoerung` auf Jahr 2 oder 3 setzen.
2. Mit `keines`, `pilgerboom` und `ouster_raid` vergleichen.
3. Auf Stabilitaet, Wohlstand, Handelswert und Time Debt achten.
4. Bei Bokeh die Tooltips ueber den Balken oeffnen; ohne Bokeh die Tabelle
   verwenden.

## 15-Minuten-Story

1. Eine Handelsroute in der Time-Debt-Karte auswaehlen.
2. Im Flight Recorder eine Kauf-, Verkauf- und Halten-Entscheidung zeigen.
3. `best_action`, Exploration, Q-Werte und realisierte Belohnung erklaeren.
4. Die Demo-Capsule exportieren und `DEMO_REPORT.md` oeffnen.

## Reproduzierbarkeit und Ausgabe

Die Standardwerte `EPISODES = 30`, `YEARS = 20` und `SEED = 7` ergeben bei
gleicher Codeversion denselben Lauf. Die Capsule schreibt CSV-Dateien fuer
Simulation, Agentenrat, Szenarien, Routen und Flight Recorder sowie eine
`metadata.json`. Bokeh erzeugt zusaetzlich `agent_dashboard.html`.

Laufzeitdaten wie `demo_capsule/`, `demo_exports/` und `agent_memory.json`
werden nicht versioniert. So bleibt der Quellstand klein und Notebook-Exports
koennen gefahrlos lokal neu erzeugt werden.

## Vorfuehrungsregeln

- Vor einer Live-Demo einmal alle Zellen ausfuehren und die Capsule erzeugen.
- Fuer eine stabile Story den Seed nicht veraendern.
- Fuer eine schnelle iPad-Demo zuerst `EPISODES = 10` und `YEARS = 12` nutzen.
- Fuer belastbare Vergleiche mehrere Seeds oder mehr Episoden verwenden.
