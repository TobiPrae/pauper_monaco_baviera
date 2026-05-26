matches = client.list_matches()
import streamlit as st
from datastore_client import get_client
from utils import compute_standings, seed_playoff

st.set_page_config(page_title="League")
client = get_client()

st.title("League Table")
players = client.list_players()
matches = client.list_matches()

table = compute_standings(players, matches)

import pandas as pd
if table:
    df = pd.DataFrame(table)
    # Columns we support sorting by (keys from table entries)
    sort_columns = {
        'Points + (Game Win %)': 'points_plus',
        'Points': 'points',
        'Game Win Rate': 'game_win_rate',
        'Match Wins': 'match_wins',
        'Game Wins': 'game_wins',
        'Total Games': 'total_games'
    }

    st.sidebar.header("Table options")
    sort_label = st.sidebar.selectbox("Sort by", list(sort_columns.keys()), index=0)
    sort_key = sort_columns[sort_label]
    desc = st.sidebar.checkbox("Descending", value=True)

    # Apply sort
    df = df.sort_values(by=sort_key, ascending=(not desc))

    # Reorder and display desired columns in specified order
    display_cols = ['player_name', 'points', 'points_plus', 'match_wins', 'match_losses', 'match_draws', 'total_matches', 'game_wins', 'game_losses', 'total_games', 'game_win_rate']
    df = df[display_cols]
    df.columns = ['Player','Points','Points + (Game Wins / Total Games Played)','Match Wins','Match Losses','Match Draws','Total Matches Played','Game Wins','Game Losses','Total Games Played','Game Win Rate']

    st.subheader("Standings")
    st.dataframe(df)

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
