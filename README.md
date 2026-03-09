# OpenAI_Codex_MKoehler

Arbeitsverzeichnis für OpenAI Codex.

## Hyperion Economy – alles in einem IPython Notebook (Hauptvariante)

Die empfohlene Variante ist jetzt **ein einziges Notebook**:

- `trade_sim_notebook.ipynb`

Das Notebook enthält komplett in einer Datei:

- Datenmodell (`World`, `EventEffect`, `Config`)
- Simulationslogik (Produktion, Konsum, Preisbildung, Handel, Events, Time Debt)
- Batch-Lauf über konfigurierbare Jahre/Perioden
- Auswertungen in Tabellen (Pandas) und Grafiken (Matplotlib)

### Start

1. Notebook öffnen: `trade_sim_notebook.ipynb`
2. Parameter-Zelle anpassen (`YEARS`, `SEED`, `EVENT_CHANCE`, `TRADE_INTENSITY`, ...)
3. Alle Zellen nacheinander ausführen

### Abhängigkeiten

```bash
pip install jupyter pandas matplotlib
```

---

## Weitere Artefakte (optional)

- `trade_sim.py` / `hyperion_economy.py`: Python-Text/CLI-Referenz
- `spreadsheet_model/`: Tabellenkalkulations-Assets + Workbook-Builder

### Tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```
