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

- `build_workbook.py` – Generator, um die XLSX-Ein-Datei aus den CSV-Quellen zu erzeugen

### Start in einer Tabellenkalkulation

1. Ein-Datei-Mappe erzeugen:

```bash
python3 spreadsheet_model/build_workbook.py
```

2. Danach `spreadsheet_model/hyperion_spreadsheet_model.xlsx` öffnen.
3. Parameter setzen (Perioden/Jahre, Event-Chance etc.).
4. Simulation periodisch berechnen.
5. Ergebnisse über Pivot/Diagramme auswerten.

Hinweis: Die generierte XLSX wird bewusst nicht versioniert, um Push-/Binary-Probleme zu vermeiden; sie wird lokal reproduzierbar erzeugt.

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

## Notebook-Demo (optional)

- `trade_sim_notebook.ipynb`

## Tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```
