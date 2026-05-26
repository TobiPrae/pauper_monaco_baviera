## Plan: Build Streamlit MTG Tournament App

TL;DR - Build a Streamlit multipage app (hosted on Streamlit Cloud) backed by GCP Datastore. App supports player management, match recording (best-of-3), a configurable top-n playoff bracket, and local testing with the Datastore emulator or service account JSON.

**Steps**
1. Project scaffolding: create Python app entry, pages, data model, and helper modules.
2. Implement Datastore adapter with two modes: local emulator (for dev) and GCP service account (for deployment). (*depends on step 1*)
3. Implement authentication: simple password gate using Streamlit secrets / env var and hashed password check. (*parallel with step 4*)
4. Implement Player Management page: Add/Edit/Delete players and overview table. (*parallel with step 3*)
5. Implement Record Game page: UI for selecting players, starting player, per-game winners, auto-calc match result, "went in time" flag, and store match + per-game records. (*depends on step 4 for player list*)
6. Implement Edit Game page: list matches, open match for edit, update results and recalc statistics. (*depends on step 5*)
7. Implement League page: compute and display sortable table with required columns and default sort by Points + (Game Wins / Total Games Played). Implement tiebreakers and configurable top-n cut control. (*depends on steps 4-6*)
8. Implement Playoffs bracket generator for top-n cut (single-elimination), with seeding from league standings and configurable n. (*depends on step 7*)
9. Add tests and local-run instructions: unit tests for scoring logic and a small demo dataset. Provide commands to run Datastore emulator and Streamlit locally.
10. Prepare Streamlit Cloud deployment: requirements, .streamlit/secrets.toml guidance, README deploy steps.

**Relevant files to create**
- app.py — main Streamlit entry that enforces password gate and page routing
- pages/Player_Management.py — player add/edit/delete and overview
- pages/League.py — league table and top-n control
- pages/Record_Game.py — record match UI
- pages/Edit_Game.py — edit existing matches
- models.py — Player, Match, Game dataclasses and scoring helpers
- datastore_client.py — wrapper around google-cloud-datastore with emulator switch
- utils.py — helpers: sorting, pagination, bracket generation
- requirements.txt — dependencies: streamlit, google-cloud-datastore, pytest, python-dotenv
- README.md — local run, emulator setup, deploy steps

**Verification**
1. Run local Datastore emulator and `streamlit run app.py` to exercise flows.
2. Unit tests: scoring rules (points, draw handling), league aggregation, playoff seeding.
3. Manual checks: add players, record matches, edit matches, verify league table and playoff bracket correctness.

**Decisions & assumptions**
- "Swiss system where each player plays once against each other player" will be implemented as full round-robin (confirmed).
- Match scoring: 3 points win / 1 point draw / 0 loss as specified.
- Persist both match-level and per-game records to support detailed stats and tiebreakers.
- Password gate: use Streamlit secrets on deployment and `dotenv` or env var locally.

Responses provided by user / Further considerations:
1. Full round-robin.
2. Player fields: `player_name`, `deck_name`, `deck_list_link` (URL).
3. Tiebreakers: default (Points then Game Win %).
4. Playoff seeding: seeded by standings (best vs worst, 2nd best vs 2nd worst, etc.).

**Further Considerations / Questions (if needed later)**
1. If you prefer true Swiss pairing (not everyone plays everyone), we can adapt to Swiss pairings.
2. Additional player metadata (club, rating) can be added later if desired.
3. Additional tiebreakers (Buchholz, opponent match-win %) can be implemented if you want them.
4. Confirm whether you want to allow byes for odd player counts in playoffs, and how to handle them.
