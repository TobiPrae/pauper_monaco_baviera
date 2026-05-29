import streamlit as st
from datastore_client import get_client
from models import compute_match_summary, Game
from auth import require_auth

st.set_page_config(page_title="Edit Match")

require_auth()
client = get_client()

# Display success message from previous run if it exists
if "success_msg" in st.session_state:
    st.success(st.session_state.success_msg)
    del st.session_state.success_msg

matches = client.list_matches()
players = client.list_players()
leagues = client.list_leagues()
player_map = {p.id: p.player_name for p in players}

if not matches:
    st.info("No matches recorded yet.")
else:
    sel = st.selectbox("Select match", [f"{m.id} - {player_map.get(m.player_a,'?')} vs {player_map.get(m.player_b,'?')}" for m in matches])
    leagues.sort(key=lambda x: x.nr, reverse=True)
    mid = sel.split(" - ")[0]
    m = next((x for x in matches if x.id == mid), None)
    if m:
        name_a = player_map.get(m.player_a, m.player_a)
        name_b = player_map.get(m.player_b, m.player_b)
        st.write(f"**{name_a}** vs **{name_b}**")
        #summ = compute_match_summary(m)
        #st.json(summ)

        # build current selections
        def winner_name(winner_code):
            if winner_code == 'A':
                return name_a
            if winner_code == 'B':
                return name_b
            return None

        # League selection
        league_index = 0
        if leagues:
            league_index = next((i for i, l in enumerate(leagues) if l.id == m.league_id), 0)
            selected_league = st.selectbox("League", leagues, format_func=lambda x: f"League {x.nr}", index=league_index)
        else:
            st.warning("No leagues found. Please create one in League Management.")

        g_opts = [None, name_a, name_b]
        g1 = st.selectbox("Game 1 winner", g_opts, index=(g_opts.index(winner_name(m.games[0].winner)) if len(m.games) >= 1 else 0))
        g2 = st.selectbox("Game 2 winner", g_opts, index=(g_opts.index(winner_name(m.games[1].winner)) if len(m.games) >= 2 else 0))
        g3 = st.selectbox("Game 3 winner", g_opts, index=(g_opts.index(winner_name(m.games[2].winner)) if len(m.games) >= 3 else 0))

        starting = st.selectbox("Starting player", [None, name_a, name_b], index=( [None, name_a, name_b].index(m.starting_player) if m.starting_player in [None, name_a, name_b] else 0))
        went_in_time = st.checkbox("Went in time", value=bool(m.went_in_time))

        if st.button("Save changes"):
            # map selected names back to A/B
            def sel_to_code(sel_name):
                if sel_name == name_a:
                    return 'A'
                if sel_name == name_b:
                    return 'B'
                return None

            games_payload = [
                {'winner': sel_to_code(g1)},
                {'winner': sel_to_code(g2)},
                {'winner': sel_to_code(g3)},
            ]

            client.update_match(m.id, games=games_payload, starting_player=starting, went_in_time=went_in_time, league_id=selected_league.id if leagues else m.league_id)
            st.session_state.success_msg = "Match updated"
            st.rerun()

        if st.button("Delete match"):
            confirm = st.checkbox("Confirm delete? This cannot be undone.", key=f"confirm_match_{m.id}")
            if confirm:
                client.matches.pop(m.id, None)
                st.success("Match deleted")
                st.rerun()
