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

players = client.list_players()
leagues = client.list_leagues()
player_map = {p.id: p.player_name for p in players}

if not leagues:
    st.warning("No leagues found. Please create one in League Management.")
    st.stop()

leagues.sort(key=lambda x: x.nr, reverse=True)
selected_league_sb = st.sidebar.selectbox("Select League", leagues, format_func=lambda x: f"League {x.nr}", key="sb_league_edit")

all_matches = client.list_matches()

# Filter matches belonging to rounds of the selected league
league_rounds = client.list_rounds(selected_league_sb.id)
round_ids = {r.id for r in league_rounds}
matches = [m for m in all_matches if getattr(m, 'round_id', None) in round_ids]

if not matches:
    st.info(f"No matches recorded for League {selected_league_sb.nr} yet.")
else:
    sel = st.selectbox("Select match to edit", [f"{m.id} - {player_map.get(m.player_a,'?')} vs {player_map.get(m.player_b,'?')}" for m in matches])
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

        current_round = next((r for r in league_rounds if r.id == getattr(m, 'round_id', None)), None)
        if current_round:
            st.markdown(f"**Match Day {current_round.nr}** (League {selected_league_sb.nr})")
            st.markdown(f"**Schedule:** {current_round.start_date} to {current_round.end_date}")
        else:
            st.markdown(f"**League {selected_league_sb.nr}** (Unknown Round)")
        
        st.write("---")

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

            client.update_match(
                m.id, 
                games=games_payload, 
                starting_player=starting, 
                went_in_time=went_in_time, 
                match_type=getattr(m, 'match_type', 'Round')
            )
            st.session_state.success_msg = "Match updated"
            st.rerun()

        #if st.button("Delete match"):
        #    confirm = st.checkbox("Confirm delete? This cannot be undone.", key=f"confirm_match_{m.id}")
        #    if confirm:
        #        client.matches.pop(m.id, None)
        #        st.success("Match deleted")
        #        st.rerun()
