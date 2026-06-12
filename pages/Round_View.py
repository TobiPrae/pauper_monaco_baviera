import streamlit as st
from datastore_client import get_client
from auth import require_auth
from models import compute_match_summary

st.set_page_config(page_title="Match Day")

require_auth()
client = get_client()

selected_league = st.session_state.get('current_league')
if not selected_league:
    st.info("No leagues found. Please create a league in League Management.")
    st.stop()

# Fetch rounds for the selected league
all_rounds = client.list_rounds(selected_league.id)

# Filter to only show round-robin match weeks (exclude playoff weeks)
league_rounds = [r for r in all_rounds if r.nr <= selected_league.weeks_rounds]
league_rounds.sort(key=lambda x: x.nr)

if not league_rounds:
    st.warning(f"No rounds found for League {selected_league.nr}.")
    st.stop()

# Button-based navigation for selecting the Match Day
selected_round_nr = st.segmented_control(
    "Select Match Week",
    options=[r.nr for r in league_rounds],
    default=league_rounds[0].nr,
    format_func=lambda x: f"Week {x}",
    key=f"round_selector_{selected_league.id}"
)

# Find the specific round object
current_round = next((r for r in league_rounds if r.nr == selected_round_nr), None)

if current_round:
    st.info(f"**Schedule:** {current_round.start_date} to {current_round.end_date}")

    # Fetch matches for this specific round
    all_matches = client.list_matches()
    # Ensure we only display standard round-robin matches
    round_matches = [m for m in all_matches if getattr(m, 'round_id', None) == current_round.id and getattr(m, 'match_type', 'Round') == 'Round']
    
    # Get user mapping for names
    users = client.list_users()
    user_map = {u.id: u.username for u in users}

    if not round_matches:
        st.write("No matches scheduled for this round.")
    else:
        for i, m in enumerate(round_matches, 1):
            name_a = user_map.get(m.player_a, "Unknown")
            name_b = user_map.get(m.player_b, "Unknown")
            match_summary = compute_match_summary(m)
            
            # Authorization check: Admin or one of the two players
            can_edit = st.session_state.user.is_admin or st.session_state.user.id in [m.player_a, m.player_b]

            # If starting player is None, the game hasn't started/recorded yet (Red). 
            # Otherwise, it's considered in progress or finished (Green).
            status_flag = "🔴" if m.starting_player is None and m.games[0].winner is None and m.games[1].winner is None and m.games[2].winner is None else "🟢"
            with st.expander(f"{status_flag} Match {i}: {name_a} vs {name_b}"):
                # Display current match standing
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
                start_opts = [None, name_a, name_b]
                cs, ct = st.columns(2)

                starting_player = cs.selectbox("Starting player", start_opts, index=(start_opts.index(m.starting_player) if m.starting_player in start_opts else 0), key=f"start_{m.id}", disabled=not can_edit)
                            
                went_in_time = ct.checkbox("Went in time", value=bool(m.went_in_time), key=f"time_{m.id}", disabled=not can_edit)
                c1, c2, c3 = st.columns(3)
                
                g1_winner = c1.selectbox("Game 1 Winner", g_opts, index=g_opts.index(get_winner_name(m.games[0].winner if len(m.games) >= 1 else None)), key=f"g1_{m.id}", disabled=not can_edit)
                g2_winner = c2.selectbox("Game 2 Winner", g_opts, index=g_opts.index(get_winner_name(m.games[1].winner if len(m.games) >= 1 else None)), key=f"g2_{m.id}", disabled=not can_edit)
                g3_winner = c3.selectbox("Game 3 Winner", g_opts, index=g_opts.index(get_winner_name(m.games[2].winner if len(m.games) >= 3 else None)), key=f"g3_{m.id}", disabled=not can_edit)

                if can_edit:
                    match_link_val = st.text_input("Match Link", value=getattr(m, "match_link", "") or "", key=f"link_{m.id}")
                    if st.button("Save Result", key=f"save_{m.id}", use_container_width=True):
                        if starting_player is None:
                            st.error("Please select a starting player before saving.")
                        else:
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
                                match_type=getattr(m, 'match_type', 'Round'),
                                match_link=match_link_val
                            )
                            st.toast(f"Result for {name_a} vs {name_b} saved!")
                            st.rerun()


# Render Dropdown for matches with a match_link
all_matches = client.list_matches()
round_ids = {r.id for r in all_rounds}
linked_matches = [m for m in all_matches if m.round_id in round_ids and getattr(m, "match_link", None)]

if linked_matches:
    st.divider()
    users = client.list_users()
    user_map = {u.id: u.username for u in users}
    round_map = {r.id: r.nr for r in all_rounds}
    
    # Sort by week first, then by player_a's username
    def sort_key(m):
        m_type = getattr(m, "match_type", "Round")
        week = round_map.get(m.round_id, 9999) if m_type == "Round" else 9999
        p_a_name = user_map.get(m.player_a, "Unknown").lower()
        return (week, p_a_name)
        
    linked_matches.sort(key=sort_key)
    
    def format_linked_match(m):
        p_a = user_map.get(m.player_a, "Unknown")
        p_b = user_map.get(m.player_b, "Unknown")
        m_type = getattr(m, "match_type", "Round")
        if m_type == "Round":
            r_obj = next((r for r in all_rounds if r.id == m.round_id), None)
            week_str = f" (Week {r_obj.nr})" if r_obj else ""
            return f"{p_a} vs {p_b}{week_str}"
        else:
            return f"{m_type}: {p_a} vs {p_b}"
            
    selected_link_match = st.selectbox(
        "Streamed Matches",
        options=linked_matches,
        index=None,
        placeholder="Search or select a match...",
        format_func=format_linked_match,
        key="match_link_selector"
    )
    if selected_link_match:
        st.markdown(f"**Watch Match:** [Link]({selected_link_match.match_link})")
    