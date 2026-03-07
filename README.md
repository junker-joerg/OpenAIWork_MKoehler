# OpenAI_Codex_MKoehler

Arbeitsverzeichnis für OpenAI Codex.

## Neon Trade Tycoon (Python Terminal-App)

Eine kleine Wirtschaftshandelssimulation mit schickem Textinterface **ohne `curses` und ohne externe Abhängigkeiten**.

### Start

```bash
python3 trade_sim.py
```

### Steuerung

- `k/j` **oder** `Pfeil hoch/runter`: Ware auswählen
- `w/s`: Zielstadt auswählen
- `b`: Ware kaufen
- `v`: Ware verkaufen
- `t`: In ausgewählte Stadt reisen
- `r`: Treibstoff tanken
- `d`: Schulden tilgen
- `n`: Nächsten Tag starten (Marktpreise ändern sich)
- `q`: Spiel beenden

Hinweis: In Nicht-TTY-Umgebungen nutzt das Spiel automatisch Zeileneingabe (`Befehl >`).
