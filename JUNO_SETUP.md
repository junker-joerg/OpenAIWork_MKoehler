# Juno auf dem iPad

## Vorbereitung

1. Den Ordner `OpenAIWork_MKoehler` in Juno öffnen oder als Lesezeichen speichern.
2. `Juno_Demo.ipynb`, `juno_demo.py`, `trade_sim.py` und `spreadsheet_model/` im selben Projektordner lassen.
3. `Juno_Demo.ipynb` öffnen und die Zellen von oben nach unten ausführen.

Juno führt Python-Skripte und Jupyter-Notebooks lokal auf dem iPad aus. Die Demo benötigt für den Standardlauf nur Pandas und Matplotlib. `ipywidgets` ist optional; ohne Widgets funktionieren die normalen Parameterzellen weiter.

## Empfohlener Demo-Ablauf

- Zelle 1: Umgebung prüfen
- Zellen 2–4: Baseline und Dashboard zeigen
- Zellen 5–7: Farcaster-Ausfall und Hyperion-Detail erklären
- Zelle 8: interaktive Parameter verwenden
- Letzte Exportzelle: CSV-Ergebnisse speichern

## Fehlerbehebung

- Bei fehlenden Widgets die Parameterzellen verwenden.
- Bei fehlendem Parquet-Backend CSV nutzen; CSV ist der verbindliche Export.
- Falls Importe fehlschlagen, prüfen, ob `juno_demo.py`, `trade_sim.py` und `spreadsheet_model/` im gleichen Ordner liegen.
- Bei einer Live-Demo zunächst mit den festen Standard-Seeds arbeiten.
