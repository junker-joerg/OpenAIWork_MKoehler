# Juno auf dem iPad

## Vorbereitung

1. Den Ordner `OpenAIWork_MKoehler` in Juno öffnen oder als Lesezeichen speichern.
2. `Juno_Demo.ipynb`, `Juno_AI_Agents_Demo.ipynb`, `juno_demo.py`, `learning_agents.py`, `trade_sim.py` und `spreadsheet_model/` im selben Projektordner lassen.
3. `Juno_Demo.ipynb` öffnen und die Zellen von oben nach unten ausführen.

Für einen Ein-Klick-Lauf kann in Juno alternativ `run_juno_demo.py` gestartet
werden. Das Skript schreibt die kompakten CSV-Ergebnisse in `demo_exports/` und
eignet sich auch als Ziel für einen Juno-Siri-Shortcut.

Juno führt Python-Skripte und Jupyter-Notebooks lokal auf dem iPad aus. Die
Wirtschafts-Demo benötigt für den Standardlauf nur Pandas und Matplotlib.
`ipywidgets` ist optional; ohne Widgets funktionieren die normalen
Parameterzellen weiter.

## Lernende KI-Agenten

`Juno_AI_Agents_Demo.ipynb` zeigt drei lokale Lernagenten:

- `Profit-Scout` nutzt SARSA und optimiert stärker den Portfolio-Endwert.
- `Reserve-Keeper` nutzt Dyna-Q und wird für Instabilität, Time Debt und Ereignisse stärker belastet.
- `Hyperion-Speculator` nutzt einen einfacheren Bandit-Vergleich.

Die Agenten lernen aus echten Hyperion-Snapshots: Reliktpreis, Stabilität,
Time Debt, Ereignissen, Hyperion-Bestand, Liquidität und Agentenbestand. Ihr
Gedächtnis wird als versionierte `agent_memory.json` gespeichert und kann in
einem späteren Juno-Lauf wieder geladen und weitertrainiert werden. Die
Lernlogik bleibt transparent und benötigt kein externes Online-Modell.

Für einen schnellen Lauf ohne Notebook:

```bash
python run_juno_agents.py --episodes 30 --years 20
```

Mit `--resume` wird das vorhandene Gedächtnis weitertrainiert:

```bash
python run_juno_agents.py --episodes 20 --years 20 --resume
```

Für die erste iPad-Präsentation sind `10` Episoden schnell, `30` Episoden
anschaulich und `50` Episoden stabiler. Das Gedächtnis bleibt lokal im
Projektordner.

## Empfohlener Demo-Ablauf

- `Juno_Demo.ipynb`: Umgebung, Baseline, Dashboard und Szenarien zeigen.
- Danach `Juno_AI_Agents_Demo.ipynb`: Training starten, Lernkurve zeigen,
  neue Marktverläufe bewerten und die JSON-Datei demonstrieren.

## Bokeh in Juno

Bokeh ist fuer diese Demo eine optionale lokale Notebook-Ausgabe. Im Juno-
Paketmanager nach `bokeh` suchen und installieren. Die Story-Capsule prueft
`BOKEH_AVAILABLE` automatisch und zeigt bei fehlendem Paket die Daten als
Tabellen an. Fuer eine Vorfuehrung ohne Paketinstallation ist kein Umbau des
Notebooks notwendig.

## Fehlerbehebung

- Bei fehlenden Widgets die Parameterzellen verwenden.
- Bei fehlendem Parquet-Backend CSV nutzen; CSV ist der verbindliche Export.
- Falls Importe fehlschlagen, prüfen, ob `juno_demo.py`, `learning_agents.py`,
  `trade_sim.py` und `spreadsheet_model/` im gleichen Ordner liegen.
- Bei einer Live-Demo zunächst mit den festen Standard-Seeds arbeiten.

## Story Capsule

`Juno_Story_Capsule.ipynb` buendelt Agentenrat, Scenario Composer, Time-Debt-
Routenkarte, Flight Recorder und reproduzierbaren Export. Die drei
Vorfuehrungsvarianten stehen in `DEMO_RUNBOOK.md`.

Die Auswahlzelle am Notebook-Anfang bietet `einsteiger`, `agentenvergleich`
und `tiefenanalyse`. Sie steuert Episoden, Simulationsjahre, sichtbare
Abschnitte und den Capsule-Export.
