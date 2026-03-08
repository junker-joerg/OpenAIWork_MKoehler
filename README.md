# OpenAI_Codex_MKoehler

Arbeitsverzeichnis für OpenAI Codex.

## Hyperion-inspirierte Wirtschaftssimulation (Textanwendung)

Die Simulation ist jetzt als **reine Textanwendung (print/input)** ausgelegt und läuft dadurch auch in **Pythonista auf dem iPad**.

Enthaltene Systemelemente:

- Hegemonie, TechnoCore, Ousters, Templars als Fraktionsdruck
- Kernwelten vs. Peripherie- und Grenzwelten
- Farcaster-Infrastruktur vs. konventionelle Routen
- Time-Debt-Effekte außerhalb des Farcaster-Netzes
- Hyperion als Sonderwelt (hohe Unsicherheit, Pilgerdruck, Reliktökonomie)
- Ereignisse: Farcaster-Störung, Ouster-Raid, Sanktionen, Pilgerboom, Aufstand, Core-Schocks, Templar-Korridor

### Implementierungsplan (kurz)

1. Welten + Güter als Datamodelle definieren.
2. Produktion/Konsum und preisgetriebene Engpässe pro Tick berechnen.
3. Handelsheuristik mit Transportkosten, Time Debt und Fraktionsmodifikatoren anwenden.
4. Event-System für politische/technologische Schocks pro Tick integrieren.
5. Textausgabe pro Tick mit Preisen, Engpässen, Fraktionslage und Handelslog bereitstellen.

### Start

#### Pythonista / interaktiv

```bash
python3 hyperion_economy.py
```

Bei Start ohne Parameter läuft die interaktive Textanwendung:

- `n`: 1 Tick weiter
- `r`: mehrere Ticks laufen lassen
- `w`: Weltenstatus anzeigen
- `q`: beenden

#### Nicht-interaktiv (Batch-Lauf)

```bash
python3 hyperion_economy.py --ticks 12 --seed 7
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
