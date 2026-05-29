import streamlit as st
from datastore_client import get_client
from utils import compute_standings, seed_playoff
from auth import require_auth

st.set_page_config(page_title="League")

require_auth()

client = get_client()

leagues = client.list_leagues()
if not leagues:
    st.info("No leagues found. Please create a league in League Management.")
    st.stop()

leagues.sort(key=lambda x: x.nr, reverse=True)
selected_league = st.sidebar.selectbox("Select League", leagues, format_func=lambda x: f"League {x.nr}")

# Filter players and matches for the selected league
league_rounds = client.list_rounds(selected_league.id)
round_ids = {r.id for r in league_rounds}
all_matches = client.list_matches()
league_matches = [m for m in all_matches if getattr(m, 'round_id', None) in round_ids and getattr(m, 'match_type', 'Round') == 'Round']

memberships = client.list_league_players(selected_league.id)
member_ids = {m.player_id for m in memberships}
all_players = client.list_players()
league_players = [p for p in all_players if p.id in member_ids]

table = compute_standings(league_players, league_matches)

import pandas as pd
if table:
    df = pd.DataFrame(table)

    # Mapping internal keys to display names
    col_mapping = {
        'player_name': 'Player',
        'points_plus': 'Points+GWR',
        'points': 'Points',
        'match_wins': 'Match Wins',
        'match_losses': 'Match Losses',
        'match_draws': 'Match Draws',
        'total_matches': 'Total Matches',
        'game_wins': 'Game Wins',
        'game_losses': 'Game Losses',
        'total_games': 'Total Games',
        'game_win_rate': 'Game Win Rate'
    }

    # Sort by the primary metric and apply name mapping
    df.insert(0, 'Rank', range(1, len(df) + 1))
    df = df.sort_values(by='Rank', ascending=True).reset_index(drop=True)
    df = df.rename(columns=col_mapping)

    # Configuration for dynamic columns
    all_display_cols = ['Rank'] + list(col_mapping.values())
    default_cols = ['Rank', 'Player', 'Points+GWR','Total Matches']

    selected_cols = st.multiselect("Select columns to display:", options=all_display_cols, default=default_cols)

    if selected_cols:
        st.dataframe(df[selected_cols], use_container_width=True, hide_index=True)
    else:
        st.info("Select at least one column to display the table.")

    # Top-n playoffs control
    max_top = len(df)
    top_n = st.number_input("Top N playoffs", min_value=2, max_value=max_top, value=min(4, max_top), step=1)
    st.caption("Playoff seeding: best vs worst, 2nd best vs 2nd worst, etc.")
    if st.button("Generate bracket"):
        bracket = seed_playoff(table, top_n)
        pairs = bracket.get('pairs', [])
        bye = bracket.get('bye')
        st.subheader("Playoff Bracket")
        for p in pairs:
            a = p['player_a']
            b = p['player_b']
            st.write(f"Seed {p['seed_a']} — {a['player_name']}  vs  Seed {p['seed_b']} — {b['player_name']}")
        if bye:
            st.info(f"Top seed gets a bye: {bye['player_name']}")
else:
    st.info("No players or matches yet.")
