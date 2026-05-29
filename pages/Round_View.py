import streamlit as st
from datastore_client import get_client
from auth import require_auth
from models import compute_match_summary

st.set_page_config(page_title="Match Day")

require_auth()
client = get_client()

leagues = client.list_leagues()
if not leagues:
    st.info("No leagues found. Please create a league in League Management.")
    st.stop()

leagues.sort(key=lambda x: x.nr, reverse=True)
selected_league = st.sidebar.selectbox("Select League", leagues, format_func=lambda x: f"League {x.nr}")

# Fetch rounds for the selected league
league_rounds = client.list_rounds(selected_league.id)
league_rounds.sort(key=lambda x: x.nr)

if not league_rounds:
    st.warning(f"No rounds found for League {selected_league.nr}.")
    st.stop()

st.title(f"League {selected_league.nr} - Match Days")

# Slider to select the round number
min_round = league_rounds[0].nr
max_round = league_rounds[-1].nr

selected_round_nr = st.slider("Select Match Day", min_value=min_round, max_value=max_round, value=min_round)

# Find the specific round object
current_round = next((r for r in league_rounds if r.nr == selected_round_nr), None)

if current_round:
    st.subheader(f"Match Day {current_round.nr}")
    st.info(f"**Schedule:** {current_round.start_date} to {current_round.end_date}")

    # Fetch matches for this specific round
    all_matches = client.list_matches()
    round_matches = [m for m in all_matches if getattr(m, 'round_id', None) == current_round.id]
    
    # Get player mapping for names
    players = client.list_players()
    player_map = {p.id: p.player_name for p in players}

    if not round_matches:
        st.write("No matches scheduled for this round.")
    else:
        for i, m in enumerate(round_matches, 1):
            name_a = player_map.get(m.player_a, "Unknown")
            name_b = player_map.get(m.player_b, "Unknown")
            
            with st.expander(f"Match {i}: {name_a} vs {name_b}"):
                # Helper to map codes to display names
                
                # Display current match standing
                match_summary = compute_match_summary(m)
                col1_summary, col2_summary, col3_summary = st.columns(3)
                col1_summary.metric(name_a, match_summary['player_a_game_wins'])
                col2_summary.write("vs")
                col3_summary.metric(name_b, match_summary['player_b_game_wins'])

                match_result_text = "Draw"
                if match_summary['match_result'] == 'A':
                    match_result_text = f"{name_a} Wins!"
                elif match_summary['match_result'] == 'B':
                    match_result_text = f"{name_b} Wins!"
                
                if match_summary['total_games_played'] > 0:
                    st.markdown(f"**Match Result:** {match_result_text}")
                st.write("---")

                def get_winner_name(winner_code):
                    if winner_code == 'A': return name_a
                    if winner_code == 'B': return name_b
                    return None

                # Helper to map names back to codes
                def name_to_code(name):
                    if name == name_a: return 'A'
                    if name == name_b: return 'B'
                    return None

                g_opts = [None, name_a, name_b]
                
                # Match input fields
                c1, c2, c3 = st.columns(3)
                g1_winner = c1.selectbox("Game 1 Winner", g_opts, index=g_opts.index(get_winner_name(m.games[0].winner if len(m.games) >= 1 else None)), key=f"g1_{m.id}")
                g2_winner = c2.selectbox("Game 2 Winner", g_opts, index=g_opts.index(get_winner_name(m.games[1].winner if len(m.games) >= 1 else None)), key=f"g2_{m.id}")
                g3_winner = c3.selectbox("Game 3 Winner", g_opts, index=g_opts.index(get_winner_name(m.games[2].winner if len(m.games) >= 3 else None)), key=f"g3_{m.id}")

                cs, ct = st.columns(2)
                start_opts = [None, name_a, name_b]
                starting_player = cs.selectbox("Starting player", start_opts, index=(start_opts.index(m.starting_player) if m.starting_player in start_opts else 0), key=f"start_{m.id}")
                went_in_time = ct.checkbox("Went in time", value=bool(m.went_in_time), key=f"time_{m.id}")

                if st.button("Save Result", key=f"save_{m.id}", use_container_width=True):
                    games_payload = [
                        {'winner': name_to_code(g1_winner)},
                        {'winner': name_to_code(g2_winner)},
                        {'winner': name_to_code(g3_winner)},
                    ]
                    
                    client.update_match(
                        m.id,
                        games=games_payload,
                        starting_player=starting_player,
                        went_in_time=went_in_time,
                        match_type=getattr(m, 'match_type', 'Round')
                    )
                    st.toast(f"Result for {name_a} vs {name_b} saved!")
                    st.rerun()