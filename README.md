# OpenAI_Codex_MKoehler

Arbeitsverzeichnis für OpenAI Codex.

## Hyperion Economy als Tabellenkalkulations-Modell (Hauptvariante)

Die Simulation ist vollständig als **tabellenkalkulations-taugliches Modell** aufbereitet (ohne Excel-spezifische Funktionen), nutzbar z. B. in:

- SoftMaker Plan
- Apple Numbers (iPad)
- LibreOffice Calc

### Dateien

Im Ordner `spreadsheet_model/`:

- `00_parameters.csv` – globale Simulationsparameter
- `01_goods.csv` – Güterstammdaten (Basispreis, Volatilität, strategische Relevanz)
- `02_worlds.csv` – Weltenstammdaten (Kern/Peripherie/Farcaster usw.)
- `03_profiles.csv` – Produktions- und Verbrauchsprofile je Welt/Gut
- `04_events_table.csv` – Event-Gewichte und Modifikatoren
- `SPREADSHEET_GUIDE.md` – Schritt-für-Schritt-Aufbau inkl. neutraler Formeln

### Start in einer Tabellenkalkulation

1. CSV-Dateien als einzelne Tabellenblätter importieren.
2. Nach Anleitung in `SPREADSHEET_GUIDE.md` die Jahr-Sheets (`Y0`, `Y1`, …) aufbauen.
3. Parameter setzen (Perioden/Jahre, Event-Chance etc.).
4. Simulation periodisch berechnen.
5. Ergebnisse über Pivot/Diagramme auswerten.

### Enthaltene Hyperion-Mechaniken

- Hegemonie / TechnoCore / Ousters / Templars
- Kernwelten vs. Peripherie/Grenzwelten
- Farcaster vs. konventionelle Routen
- Time Debt
- Hyperion als Sonderwelt mit Pilger-/Relikt-Dynamik
- Eventschocks (Farcaster-Ausfall, Ouster-Raid, Sanktionen, Pilgerboom, Aufstand, Core-Effekte)

---

## Python-Referenzimplementierung (optional)

Die gleiche Logik ist weiterhin in Python verfügbar:

- `trade_sim.py` (Text-App / CLI)
- `hyperion_economy.py` (Kompatibilitäts-Wrapper)

Die Python-Simulation lädt Güter, Welten, Produktionsprofile, Ereignisse und
Basisparameter aus `spreadsheet_model/`. Beispiel für einen reproduzierbaren
Batch-Lauf:

```bash
python3 trade_sim.py --ticks 30 --seed 7 --event-chance 0.45
```

Ungültige Parameter werden mit einer erklärenden Fehlermeldung abgewiesen.

## Notebook-Demo (optional)

- `trade_sim_notebook.ipynb`

## Juno-Demo auf dem iPad

- `Juno_Demo.ipynb` (geführte, kompakte Demo)
- `juno_demo.py` (Simulation, KPIs, Diagramme und CSV-Export)
- `run_juno_demo.py` (Ein-Klick-/Shortcut-Einstieg)
- `Juno_AI_Agents_Demo.ipynb` (lokale lernende Agenten mit Q-Learning)
- `learning_agents.py` (SARSA, Dyna-Q, Bandit, Hyperion-Integration und JSON-Gedächtnis)
- `run_juno_agents.py` (Ein-Klick-/Shortcut-Einstieg für Agententraining)
- `JUNO_SETUP.md` (Einrichtung und Präsentationsablauf)

Die Juno-Demo verwendet feste Szenarien, große Matplotlib-Diagramme und kurze
Tabellen für eine flüssige iPad-Präsentation. CSV wird immer exportiert;
Parquet ist optional. Widgets sind eine Komfortfunktion und haben einen
Parameterzellen-Fallback.

Die Agenten-Demo läuft ebenfalls lokal/offline. Sie verwendet nur die
Standardbibliothek für das Lernen; Pandas und Matplotlib werden im Notebook
für Tabellen und Diagramme genutzt.

## Story Capsule und Bokeh

`Juno_Story_Capsule.ipynb` buendelt Agentenrat, Scenario Composer,
Time-Debt-Routenkarte und Flight Recorder. `juno_showcase.py` erzeugt die
Bokeh-Ansichten und exportiert die reproduzierbare `demo_capsule/`. Bokeh ist
optional; ohne Paket bleibt die Matplotlib-/Tabellen-Demo verfuegbar.
Am Notebook-Anfang kann zwischen `einsteiger`, `agentenvergleich` und
`tiefenanalyse` gewaehlt werden; dadurch werden Laufzeit und Detailtiefe
automatisch angepasst.

## Tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```
