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

`Juno_AI_Agents_Demo.ipynb` zeigt drei lokale Q-Learning-Händler:

- `Profit-Scout` optimiert stärker den Portfolio-Endwert.
- `Reserve-Keeper` wird für Instabilität und Ereignisrisiken stärker bestraft.
- `Hyperion-Speculator` handelt opportunistisch mit mittlerer Risikoaversion.

Die Agenten lernen aus Preisband, Stabilität, Liquidität und Bestand. Ihr
Gedächtnis wird als `agent_memory.json` gespeichert und kann in einem späteren
Juno-Lauf wieder geladen werden. Es ist bewusst eine transparente, kleine
Q-Tabelle und kein externes Online-Modell.

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

## Fehlerbehebung

- Bei fehlenden Widgets die Parameterzellen verwenden.
- Bei fehlendem Parquet-Backend CSV nutzen; CSV ist der verbindliche Export.
- Falls Importe fehlschlagen, prüfen, ob `juno_demo.py`, `learning_agents.py`,
  `trade_sim.py` und `spreadsheet_model/` im gleichen Ordner liegen.
- Bei einer Live-Demo zunächst mit den festen Standard-Seeds arbeiten.
