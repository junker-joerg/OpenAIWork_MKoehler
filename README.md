# OpenAI_Codex_MKoehler

Arbeitsverzeichnis für OpenAI Codex.

## Hyperion-inspirierte Wirtschaftssimulation (Ein-Datei-Textanwendung)

Die Simulation liegt jetzt zentral in **`trade_sim.py`** (Ein-Datei-App), damit sie in **Pythonista auf dem iPad** direkt als eine Datei geladen und ausgeführt werden kann.

Enthaltene Systemelemente:

- Hegemonie, TechnoCore, Ousters, Templars als Fraktionsdruck
- Kernwelten vs. Peripherie- und Grenzwelten
- Farcaster-Infrastruktur vs. konventionelle Routen
- Time-Debt-Effekte außerhalb des Farcaster-Netzes
- Hyperion als Sonderwelt (hohe Unsicherheit, Pilgerdruck, Reliktökonomie)
- Ereignisse: Farcaster-Störung, Ouster-Raid, Sanktionen, Pilgerboom, Aufstand, Core-Schocks, Templar-Korridor

### Start

#### Pythonista / interaktiv (empfohlen)

```bash
python3 trade_sim.py
```

Bei Start ohne Parameter läuft die interaktive Textanwendung:

- `n`: 1 Tick weiter
- `r`: mehrere Ticks laufen lassen
- `w`: Weltenstatus anzeigen
- `q`: beenden

#### Nicht-interaktiv (Batch-Lauf)

```bash
python3 trade_sim.py --ticks 12 --seed 7
```

Optionen:

- `--event-chance` (Standard: `0.45`)
- `--trade-intensity` (Standard: `1.0`)
- `--faction-strength` (Standard: `1.0`)
- `--interactive` (erzwingt Interaktivmodus)

### Tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Hinweis zur Kompatibilität

`hyperion_economy.py` ist nur noch ein dünner Wrapper auf `trade_sim.py`.

---

## Notebook-Demo (optional)

Datei: `trade_sim_notebook.ipynb`

```bash
pip install ipywidgets
```
