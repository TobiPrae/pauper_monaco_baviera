
**Local quickstart**:

1. Create a virtualenv and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Add secrets to .streamlit/secrets.toml:


```bash
[service_account_key]
"type"= "service_account"
"project_id"= "..."
"private_key_id"= "..."
"private_key"= "..."
"client_email"= "..."
"client_id"= "..."
"auth_uri"= "https://accounts.google.com/o/oauth2/auth"
"token_uri"= "https://oauth2.googleapis.com/token"
"auth_provider_x509_cert_url"= "https://www.googleapis.com/oauth2/v1/certs"
"client_x509_cert_url"= "..."
"universe_domain"= "googleapis.com"
```

3. Configure .env file:
```bash
Create .env file in base folder and variable accordingly
For Development and Test(enables local_datastore.json): 
USE_GCP_DATASTORE=false
For Production(enables proper GCP Connection):
USE_GCP_DATASTORE=true
```

or in secrets.toml:
```
[USE_GCP_DATASTORE]
"var"="true"
```

4. Run Streamlit:

```bash
streamlit run app.py
```

## League Predictor (v2.0 + v2.1)

The League Predictor is a deterministic simulation pipeline:

Feature Engine  
→ Probability Engine  
→ Prediction Explainability Engine  
→ Monte Carlo  
→ Scenario Engine  
→ Prediction Report

### Version 2.0 – Prediction Explainability

Version 2.0 focuses on transparency and trust:

- Every prediction includes explicit feature contributions.
- Positive and negative drivers are shown separately.
- Confidence scores describe how reliable each explanation is.
- Match and player explanations are fully deterministic.
- The reconstruction property is enforced:
  - baseline + sum(feature contributions) = final probability

UI additions:

- Prediction Explainability section
- Player filter for focused explainability
- Waterfall chart (green positive / red negative / gray neutral)
- Detailed contribution table (Feature, Contribution, Confidence, Explanation)
- "🔍 Why?" panel on prediction details
- League Insights section

### Version 2.1 – Scenario Explorer

Version 2.1 introduces three automatic story-driven scenarios:

1. 🎯 Most Likely Scenario
2. ⚔ Bubble Race
3. 😱 Chaos Scenario

Scenario Explorer is rendered in the **Overview** tab (directly below the Playoff Dashboard) and includes:

- Scenario cards (name, probability, description, confidence)
- Detail views per scenario
- Final standings
- Remaining match timeline
- Playoff qualification badges
- Champion badge
- Critical match highlight
- Short scenario summary based only on Prediction Report data

Interpretation note for **Most Likely**:

- The current implementation measures the probability of the **exact full final standings order**.
- In leagues with many close outcomes, there are many valid ranking permutations.
- As a result, even the most frequent exact table can be small (for example `0.4%`), while still being the most likely single exact outcome.

### League Predictor page structure (current)

To reduce visual overload, the League Predictor UI is split into three tabs:

1. **Overview**
   - Playoff Dashboard (core charts only)
   - Scenario Explorer (3 cards + expandable details)
   - League Story (AI explanation + league insights)
   - Optional detailed playoff overview in an expander

2. **Explainability**
   - Player explainability (with single-player filter)
   - Feature contribution waterfall chart
   - Contribution table and "🔍 Why?" panel
   - Optional expanded sections for expected ranking, critical matches, and schedule

3. **Advanced**
   - What-if scenario overrides
   - Player detail inspector
   - Prediction confidence and diagnostics
   - JSON export

Design principle:
- Keep default view focused on decision-relevant outputs.
- Move deep technical tables and diagnostics behind expanders.

### PredictionReport contract (UI boundary)

The `PredictionReport` is the only interface used by the UI.
UI components must not access internal model calculations directly.

Relevant report extensions:

- `player_predictions[].feature_contributions`
- `player_predictions[].positive_drivers`
- `player_predictions[].negative_drivers`
- `player_predictions[].confidence`
- `match_probabilities[].feature_contributions`
- `match_probabilities[].confidence`
- `league_insights`
- `scenario_reports[]` (list of `ScenarioReport`)

`ScenarioReport` contains:

- `scenario_type`
- `scenario_name`
- `scenario_probability`
- `final_standings`
- `remaining_results`
- `playoff_teams`
- `champion`
- `critical_match`
- `summary`
- `confidence`
- `short_description`
- `key_remaining_matches`
- `bubble_players`
- `required_results`
- `helpful_results`
- `current_momentum`
- `largest_upsets`
