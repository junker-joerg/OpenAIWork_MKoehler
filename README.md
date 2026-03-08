# OpenAI_Codex_MKoehler

Arbeitsverzeichnis für OpenAI Codex.

## Hyperion-inspirierte Wirtschaftssimulation (neu)

Eine kleine, tick-basierte Interstellar-Ökonomie mit Fokus auf:

- Hegemonie/Kernwelten vs. Peripherie
- Farcaster-Netz als Niedrigfriktions-Infrastruktur
- TechnoCore-Einfluss (Signale, Gebühren, Prognosefehler/Optimierung)
- Ouster-Risiko auf Randrouten
- Templar-Weltenbaum-Sonderkorridor
- Hyperion als asymmetrische Sonderwelt (Pilgerdruck, Relikte, Risiko)
- Time-Debt-Effekte für nicht-farcaster-basierte Logistik
- Exogene Schocks (Sanktionen, Aufstände, Farcaster-Störungen usw.)

### Implementierungsplan (kurz)

1. Welten + Güter als Datamodelle definieren.
2. Produktion/Konsum und preisgetriebene Engpässe pro Tick berechnen.
3. Handelsheuristik mit Transportkosten, Time Debt und Fraktionsmodifikatoren anwenden.
4. Event-System für politische/technologische Schocks pro Tick integrieren.
5. CLI-Summary mit Top-Preisen, Engpässen, Fraktionslage und Handelslog ausgeben.

### Start

```bash
python3 hyperion_economy.py --ticks 12 --seed 7
```

Optionen:

- `--event-chance` (Standard: `0.45`)
- `--trade-intensity` (Standard: `1.0`)
- `--faction-strength` (Standard: `1.0`)

### Tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

---

## Bestehende Demo: Neon Trade Tycoon (Terminal-App)

```bash
python3 trade_sim.py
```

## Bestehende Demo: Neon Trade Tycoon (Jupyter/IPython Notebook)

Datei: `trade_sim_notebook.ipynb`

```bash
pip install ipywidgets
```
