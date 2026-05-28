import streamlit as st
from datastore_client import get_client
from models import Game, Match, compute_match_summary
from auth import require_auth

st.set_page_config(page_title="Record Game")

require_auth()
client = get_client()

players = client.list_players()
player_map = {p.player_name: p.id for p in players}

if len(players) < 2:
    st.info("Add at least two players on the Player Management page.")
else:
    player_names = [p.player_name for p in players]
    a_name = st.selectbox("Player A", player_names)
    # Ensure Player B choices exclude Player A
    b_choices = [n for n in player_names if n != a_name]
    if not b_choices:
        st.error("Not enough distinct players to choose Player B.")
    else:
        b_name = st.selectbox("Player B", b_choices)
        starting = st.selectbox("Starting Player", [a_name, b_name])
        st.write("Select winners for up to 3 games (None = no result)")
        g_opts = [None, a_name, b_name]
        g1 = st.selectbox("Game 1 winner", g_opts, index=0)
        g2 = st.selectbox("Game 2 winner", g_opts, index=0)
        g3 = st.selectbox("Game 3 winner", g_opts, index=0)
        went_in_time = st.checkbox("Went in time")

        # Build a temporary Match object to show a live summary before saving
        def name_to_code(name):
            if name == a_name:
                return 'A'
            if name == b_name:
                return 'B'
            return None

        temp_games = [Game(game_index=1, winner=name_to_code(g1)), Game(game_index=2, winner=name_to_code(g2)), Game(game_index=3, winner=name_to_code(g3))]
        temp_match = Match(id="preview", player_a=player_map[a_name], player_b=player_map[b_name], starting_player=starting, games=temp_games, went_in_time=went_in_time)
        summary = compute_match_summary(temp_match)
        #st.subheader("Match preview")
        #st.json(summary)

        save_disabled = (a_name == b_name)
        if save_disabled:
            st.error("Player A and Player B must be different")

        if st.button("Save match", disabled=save_disabled):
            games_payload = []
            for g in [g1, g2, g3]:
                code = name_to_code(g)
                games_payload.append({'winner': code})

            m = client.add_match(player_a=player_map[a_name], player_b=player_map[b_name], starting_player=starting, games=games_payload, went_in_time=went_in_time)
            st.success("Match recorded")
            st.json(compute_match_summary(m))
            st.rerun()
