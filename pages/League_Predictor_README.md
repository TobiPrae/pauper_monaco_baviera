# League Predictor

Diese README beschreibt die Streamlit-Seite `League Predictor` (`pages/League_Predictor.py`) sowie die darunterliegende Prediction-Engine im Ordner `prediction/`.

## Ziel der Seite

Der League Predictor soll schnell zeigen:

- wer sehr wahrscheinlich in die Playoffs kommt,
- wie groß die Chancen pro Spieler sind,
- warum diese Einschätzung entsteht (Form, Historie, Matchups, Restprogramm).

## UI-Überblick (Seitenaufbau)

1. **Prediction Settings**
2. **Top-Kennzahlen** (League, Simulations, Title Favorite, Bubble Teams)
3. **Playoff Dashboard**
4. **Playoff Quick Overview**
5. Weitere Detailsektionen:
   - Playoff Odds
   - Champion Odds
   - Expected Final Ranking
   - Remaining Schedule
   - Critical Matches
   - Scenario Explorer (What If)
   - Player Details
   - Prediction Confidence
   - Prediction Diagnostics
   - AI Explanation
   - JSON Export

---

## Architektur

### 1) Page Layer (`pages/League_Predictor.py`)

- Sammelt User-Inputs (Simulationen, Playoff-Cutoff, Seed, Feature-Weights).
- Baut den Report über `PredictionService`.
- Rendert Metriken, Tabellen, Charts und den What-If-Bereich.
- Nutzt `@st.cache_data` für den Report-Aufbau.

### 2) Datenaufbereitung (`prediction/data.py`)

`build_prediction_dataset(...)`:

- lädt Ligen, Runden, Matches, User, Decks, Memberships,
- trennt Target-Liga in:
  - `completed_target_matches`
  - `remaining_target_matches`
- berechnet `current_standings` (Punkte, GWR, Rang),
- baut zusätzlich `historical_completed_matches` über alle Ligen für Features.

### 3) Feature Layer (`prediction/features.py`)

`FeatureRegistry.default()` enthält aktuell:

- `historical_match_win_rate`
- `historical_game_win_rate`
- `head_to_head`
- `deck_matchup`
- `current_form`
- `strength_of_schedule`
- `remaining_opponent_strength`

Jedes Feature liefert:

- `score` in `[-1, 1]`
- `confidence` in `[0, 1]`
- `explanation`

### 4) Probability Engine (`prediction/probability.py`)

`ProbabilityEngine.compute(...)`:

- gewichtet Feature-Scores über `feature_weights`,
- bildet daraus einen aggregierten Edge-Wert,
- wandelt den Edge-Wert via Sigmoid in Win/Loss um,
- ergänzt Draw-Wahrscheinlichkeit (geclamped durch min/max),
- normalisiert auf `p_a_win + p_draw + p_b_win = 1`.

### 5) Simulation Layer (`prediction/simulation.py`)

`run_monte_carlo(...)`:

- sampelt für jedes verbleibende Match ein Ergebnis (A/Draw/B),
- addiert Punkte/Game-Wins/Total-Games je Simulation,
- rankt pro Simulation inkl. Tiebreak:
  1. Punkte
  2. Game-Win-Rate
  3. Head-to-Head-Minileague bei kompletter Gleichheit

### 6) Szenario- und Report-Layer (`prediction/scenarios.py`, `prediction/report.py`)

- berechnet `player_predictions` (Playoff-/Champion-Wahrscheinlichkeit, best/worst/expected finish),
- bestimmt `critical_matches` (Leverage + Reason),
- setzt `league_summary` und `confidence_metrics`,
- liefert ein vollständiges `PredictionReport`-Objekt.

### 7) What-If Layer (`prediction/what_if.py`)

`recalculate_with_overrides(...)`:

- überschreibt selektiv Outcomes einzelner Restmatches,
- berechnet die resultierenden Ränge erneut auf Basis derselben Simulationsbasis.

---

## Einstellungen (Prediction Settings)

In der UI verfügbar:

- **Monte Carlo simulations**  
  Optionen: `1_000`, `5_000`, `10_000`, `25_000`, `50_000`, `100_000`  
  Mehr Simulationen = stabilere Wahrscheinlichkeiten, aber mehr Laufzeit.

- **Playoff cutoff (Top N)**  
  Anzahl Plätze, die als Playoff-Qualifikation zählen.

- **Random seed**  
  Steuert Reproduzierbarkeit der Monte-Carlo-Samples.

- **Feature weights (JSON)**  
  Feinjustierung des Modells pro Feature.

Standard-Konfiguration aus `prediction/config.py`:

- `simulations = 50_000`
- `random_seed = 42`
- `laplace_alpha = 6.0`
- `logistic_scale = 3.0`
- `min_draw_probability = 0.08`
- `max_draw_probability = 0.22`
- `playoff_cut = 4`

Default-Feature-Weights:

- `historical_match_win_rate`: `1.35`
- `historical_game_win_rate`: `1.1`
- `head_to_head`: `1.25`
- `deck_matchup`: `0.95`
- `current_form`: `1.05`
- `strength_of_schedule`: `0.75`
- `remaining_opponent_strength`: `0.6`

---

## Playoff Dashboard

Vor dem Quick Overview zeigt ein visuelles Dashboard:

- Balken-Chart mit den Top-Playoff-Chancen
- Segmentierung der Playoff-Race-Gruppen
- Scatter-Chart für Playoff- vs. Champion-Wahrscheinlichkeit

## Playoff Quick Overview (user-friendly Layer)

Der Schnellüberblick (`build_playoff_overview`) gruppiert Spieler in:

- **Very Likely** (`>= 75%`)
- **In Contention** (`>= 45% und < 75%`)
- **Long Shot** (`< 45%`)

Zusätzlich gibt es pro Spieler eine kompakte Begründung (ein Satz) mit:

- Playoff-Chance
- aktuellem Rang
- erwartetem Endrang
- Einordnung Restprogramm (schwer/günstig)
- optionalem Schlüsselspiel

---

## Datenobjekte und Output

Kernobjekt ist `PredictionReport` (`prediction/types.py`) mit u. a.:

- `current_standings`
- `remaining_schedule`
- `match_probabilities`
- `player_predictions`
- `critical_matches`
- `league_summary`
- `diagnostics`
- `confidence_metrics`
- `internal_artifacts` (für What-If/Recalc)

Export ist als JSON über `report.to_json()` verfügbar.

---

## Bekannte Grenzen / Interpretation

- Diagnostics sind aktuell konservativ (siehe Kommentar in `prediction/diagnostics.py`) und noch kein vollwertiger Out-of-Sample-Backtest.
- Prognosen sind sensitiv gegenüber Feature-Weights und Datenqualität (z. B. kleine historische Samples).
- Der Predictor ist eine probabilistische Entscheidungshilfe, keine deterministische Vorhersage.
