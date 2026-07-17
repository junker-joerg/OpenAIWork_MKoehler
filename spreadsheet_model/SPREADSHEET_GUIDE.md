# Spreadsheet-Umsetzung (plattformneutral)

Diese Umsetzung ist für Tabellenkalkulationen wie SoftMaker Plan, Apple Numbers oder LibreOffice Calc gedacht.

## Ziel

Die komplette Simulation läuft tabellenbasiert über Perioden/Jahre:

1. Parameter setzen
2. Jahres-Sheet duplizieren (`Y1`, `Y2`, ...)
3. Formeln berechnen Welt-/Gut-Zellen
4. Auswertung über Pivot-Tabellen und Charts

Keine Excel-spezifischen Features nötig.

---

## Benötigte Sheets

- `Parameters` (aus `00_parameters.csv`)
- `Goods` (aus `01_goods.csv`)
- `Worlds` (aus `02_worlds.csv`)
- `Profiles` (aus `03_profiles.csv`)
- `Events` (aus `04_events_table.csv`)
- `Y0` (Startzustand)
- `Y1..Yn` (Perioden)
- `Summary` (Aggregationen + Charts)

---

## Kernstruktur pro Jahr-Sheet (`Yk`)

Eine Zeile = `(world, good)` Kombination.

Empfohlene Spalten:

- `year`
- `world`
- `good`
- `base_price`
- `volatility`
- `strategic`
- `population_factor`
- `farcaster`
- `periphery`
- `hyperion_special`
- `pilgrim_pull`
- `stability`
- `prosperity`
- `opening_stock`
- `production`
- `consumption`
- `event_pilgrim_mult`
- `event_prod_penalty`
- `event_core_noise`
- `trade_in`
- `trade_out`
- `closing_stock`
- `price`
- `time_debt`

---

## Formeln (nur Standardfunktionen)

> Syntax ggf. lokal anpassen (`;` statt `,`).

### 1) Reserve

`reserve = BASE_RESERVE + population_factor * POP_RESERVE_FACTOR`

### 2) Nachfrage

`raw_demand = consumption * population_factor`

`luxury_mult = IF(OR(good="luxus",good="relikte"), event_pilgrim_mult, 1)`

`hyperion_mult = IF(AND(hyperion_special=1, OR(good="luxus",good="relikte")), 1 + pilgrim_pull*0.2, 1)`

`demand = raw_demand * luxury_mult * hyperion_mult`

### 3) Produktion

`stability_factor = 0.85 + stability*0.3`

`prod_penalty = IF(periphery=1, event_prod_penalty, event_prod_penalty*0.4)`

`produced = production * stability_factor * (1 - prod_penalty)`

### 4) Lager

`pre_trade_stock = opening_stock + produced - demand`

`closing_stock = MAX(0, pre_trade_stock + trade_in - trade_out)`

### 5) Knappheitseinfluss

`available = closing_stock + 1`

`imbalance = (demand + 1) / available`

`tension = MAX(0.8, 1.25 - stability)`

### 6) Preis

`noise` als externer Zufallswert pro Zeile (z. B. in Hilfsspalte), skaliert mit `event_core_noise`.

`price = MAX(4, base_price * (1 + volatility*(imbalance-1)) * (1 + strategic*(tension-1)) * (1 + noise))`

### 7) Time Debt (bei nicht-Farcaster-Handel)

`new_time_debt = prev_time_debt*0.92 + trade_in_non_farcaster * (TIME_DEBT_NORMAL + IF(periphery=1, TIME_DEBT_PERIPHERY_ADDON, 0))`

---

## Handelsheuristik in Tabellenform

Da Solver/Script nicht vorausgesetzt wird, nutze diese einfache Regel:

1. `surplus = MAX(0, pre_trade_stock - reserve)`
2. `deficit = MAX(0, reserve - pre_trade_stock)`
3. Für jedes Gut eine Matching-Tabelle in `Summary`:
   - Exportwelten nach niedrigem Preis sortieren
   - Importwelten nach hohem Preis sortieren
4. Setze `trade_out`/`trade_in` manuell oder über einfache Zuordnungsformeln (Top-3 Routen).

Das ist bewusst robust und kompatibel, statt komplexer Excel-spezifischer Optimierung.

---

## Eventmodell ohne Makros

- Lege in `Summary` pro Jahr eine Event-Zelle an (`active_event_key`).
- Wähle Event entweder manuell oder per Zufallszahl + Gewichtstabelle.
- Hole Modifier mit `INDEX/MATCH` oder `XLOOKUP`-Äquivalent deiner Tabellenkalkulation.

Beispiel:

- `event_pilgrim_mult`
- `event_prod_penalty`
- `event_core_noise`
- `event_transport_cost_bonus`

---

## Auswertung

Empfohlene Tabellen/Grafiken:

- Durchschnittspreis pro Gut und Jahr
- Wohlstand/Stabilität je Welt über Zeit
- Hyperion: Reliktpreis + Time Debt
- Core-Signal / Ouster-Druck / Templar-Zugang je Jahr

Diese sind in allen gängigen Tabellenkalkulationen als Pivot + Liniendiagramm machbar.
