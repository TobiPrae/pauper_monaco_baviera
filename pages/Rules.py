import streamlit as st
from auth import require_auth

st.set_page_config(page_title="Rules")

require_auth()

st.markdown("""
### Match Scheduling

*   Each pairing has **one week** to complete their match. Matches can be played either online or offline.
*   There is a **one-week buffer** if a match cannot be scheduled within the primary window. Both players are equally responsible for coordinating their match.
*   Matches may be played ahead of schedule to accommodate planned absences or vacations.

### Match Format & Timing

*   Matches are played in a **Best of 3** format with a **50-minute** time limit.
*   The timer starts immediately after the die roll, before any mulligan decisions are made.
*   If the 50-minute limit is reached, there are **5 additional turns** in total before the match results in a draw.
*   The player whose turn it is when time expires finishes their current turn. The first extra turn then begins with the opponent.

### Ranking & Tiebreakers

*   Rankings are determined by match points: **Win = 3, Draw = 1, Loss = 0**.
*   **Tiebreaker 1:** Game Win Rate (GWR).
*   **Tiebreaker 2:** Head-to-head (direct comparison) results.
*   **Tiebreaker 3:** If the head-to-head match resulted in a draw, a final tiebreaker match will be played.

### Playoffs

*   Playoff matches are **Best of 3** and have **no time limit**.
*   The playoff format features a **Top 4 cut**, consisting of two semi-finals, a third-place match, and a grand final.

### Decklists

*   Decklists have to be created **before** the first match and are not allowed to be changed afterwards.
*   It is mandatory to share the decklists via a Moxfield link.
*   The decklists will remain hidden until the playoffs are generated.
            
### Most Important Rule
*   Good luck, have fun 🍆

### Hall of Fame
""")

st.image("assets/202501.png", caption="Tobi (2025-01)", width=150)
st.image("assets/202601.png", caption="Pat (2026-01)", width=150)
st.image("assets/202602.png", caption="Juri (2026-02)", width=150)
