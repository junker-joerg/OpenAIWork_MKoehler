# OpenAI_Codex_MKoehler

Arbeitsverzeichnis für OpenAI Codex.

## Hyperion Economy als IPython Notebook (Hauptvariante)

Die vollständige Hyperion-Wirtschaftssimulation ist als Notebook aufbereitet:

- Datei: `trade_sim_notebook.ipynb`
- Parameter werden in **einer Zelle** gesetzt
- Simulation läuft dann über eine feste Anzahl Jahre/Perioden
- Ergebnisse werden mit **Pandas** tabellarisch und mit **Matplotlib** grafisch dargestellt

### Features im Notebook

- Hegemonie / TechnoCore / Ousters / Templars als systemische Fraktionen
- Kernwelten, Peripherie- und Sonderwelten (inkl. Hyperion)
- Farcaster vs. konventionelle Routen inkl. Time Debt
- Eventsystem (z. B. Farcaster-Störung, Ouster-Raid, Pilgerboom, Sanktionen)
- Jahresdaten als DataFrames (`df_yearly`, `df_world`, `df_price`)
- Auswertung über Tabellen + mehrere Diagramme

### Start

1. Notebook öffnen: `trade_sim_notebook.ipynb`
2. Parameter-Zelle anpassen (`YEARS`, `SEED`, `EVENT_CHANCE`, ...)
3. Zellen der Reihe nach ausführen

### Abhängigkeiten

```bash
pip install pandas matplotlib jupyter
```

---

## CLI-Variante (optional)

Die gleiche Ökonomielogik ist weiterhin als Textanwendung in `trade_sim.py` vorhanden.

```bash
python3 trade_sim.py
```

Batch-Lauf:

```bash
python3 trade_sim.py --ticks 12 --seed 7
```

Kompatibilitäts-Wrapper:

- `hyperion_economy.py` ruft intern `trade_sim.main()` auf.

### Tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```
