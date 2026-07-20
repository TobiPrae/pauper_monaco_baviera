import streamlit as st
from datetime import date
from datastore_client import get_client
from auth import require_auth
from models import compute_match_summary
from utils import validate_video_link

st.set_page_config(page_title="Match Day")

require_auth()
client = get_client()

selected_league = st.session_state.get('current_league')
if not selected_league:
    st.info("No leagues found. Please create a league in League Management.")
    st.stop()

league_display_name = f"{selected_league.league_name} ({selected_league.nr})" if selected_league.league_name else f"League {selected_league.nr}"
st.title(league_display_name)

# Fetch rounds for the selected league
all_rounds = client.list_rounds(selected_league.id)

# Filter to only show round-robin match weeks (exclude playoff weeks)
league_rounds = [r for r in all_rounds if r.nr <= selected_league.weeks_rounds]
league_rounds.sort(key=lambda x: x.nr)

if not league_rounds:
    st.warning(f"No rounds found for League {selected_league.nr}.")
    st.stop()

# Determine the current week based on today's date
def _get_current_week_nr(rounds):
    today = date.today()
    for r in rounds:
        try:
            r_start = date.fromisoformat(r.start_date)
            r_end = date.fromisoformat(r.end_date)
            if r_start <= today <= r_end:
                return r.nr
        except (ValueError, TypeError):
            continue
    return rounds[0].nr

current_week_default = _get_current_week_nr(league_rounds)

# Fetch all matches once (reused below for the selected round)
all_matches = client.list_matches()

# Determine which rounds have open (unrecorded) matches
def _is_match_open(m):
    return (m.starting_player is None
            and m.games[0].winner is None
            and m.games[1].winner is None
            and m.games[2].winner is None)

round_id_to_nr = {r.id: r.nr for r in league_rounds}
weeks_with_open_games = set()
for m in all_matches:
    rid = getattr(m, 'round_id', None)
    if rid in round_id_to_nr and getattr(m, 'match_type', 'Round') == 'Round' and _is_match_open(m):
        weeks_with_open_games.add(round_id_to_nr[rid])

# Only warn about open games for weeks that have already ended
today = date.today()
past_week_nrs = set()
for r in league_rounds:
    try:
        if date.fromisoformat(r.end_date) < today:
            past_week_nrs.add(r.nr)
    except (ValueError, TypeError):
        pass
overdue_weeks = weeks_with_open_games & past_week_nrs

# Button-based navigation for selecting the Match Day
selected_round_nr = st.segmented_control(
    "Select Match Week",
    options=[r.nr for r in league_rounds],
    default=current_week_default,
    format_func=lambda x: f"🟠 Week {x}" if x in overdue_weeks else f"Week {x}",
    key=f"round_selector_{selected_league.id}"
)

# Find the specific round object
current_round = next((r for r in league_rounds if r.nr == selected_round_nr), None)

if current_round:
    st.info(f"**Schedule:** {current_round.start_date} to {current_round.end_date}")

    # Filter pre-fetched matches for this specific round
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

                # Map starting_player to ID if it's a legacy username
                username_to_id = {u.username: u.id for u in users}
                current_start_id = m.starting_player
                if current_start_id and current_start_id not in (m.player_a, m.player_b):
                    current_start_id = username_to_id.get(current_start_id, current_start_id)

                opts = [None, m.player_a, m.player_b]
                
                def format_player(uid):
                    if uid is None: return "Select..."
                    return user_map.get(uid, "Unknown")

                cs, ct = st.columns(2)

                starting_player = cs.selectbox(
                    "Starting player",
                    opts,
                    index=(opts.index(current_start_id) if current_start_id in opts else 0),
                    format_func=format_player,
                    key=f"start_{m.id}",
                    disabled=not can_edit
                )
                            
                went_in_time = ct.checkbox("Went in time", value=bool(m.went_in_time), key=f"time_{m.id}", disabled=not can_edit)
                c1, c2, c3 = st.columns(3)
                
                g1_winner_val = m.player_a if (len(m.games) >= 1 and m.games[0].winner == 'A') else (m.player_b if (len(m.games) >= 1 and m.games[0].winner == 'B') else None)
                g2_winner_val = m.player_a if (len(m.games) >= 2 and m.games[1].winner == 'A') else (m.player_b if (len(m.games) >= 2 and m.games[1].winner == 'B') else None)
                g3_winner_val = m.player_a if (len(m.games) >= 3 and m.games[2].winner == 'A') else (m.player_b if (len(m.games) >= 3 and m.games[2].winner == 'B') else None)

                g1_winner = c1.selectbox("Game 1 Winner", opts, index=opts.index(g1_winner_val) if g1_winner_val in opts else 0, format_func=format_player, key=f"g1_{m.id}", disabled=not can_edit)
                g2_winner = c2.selectbox("Game 2 Winner", opts, index=opts.index(g2_winner_val) if g2_winner_val in opts else 0, format_func=format_player, key=f"g2_{m.id}", disabled=not can_edit)
                g3_winner = c3.selectbox("Game 3 Winner", opts, index=opts.index(g3_winner_val) if g3_winner_val in opts else 0, format_func=format_player, key=f"g3_{m.id}", disabled=not can_edit)

                if can_edit:
                    video_link_val = st.text_input("Video Link", value=getattr(m, "video_link", "") or "", key=f"link_{m.id}")
                    if st.button("Save Result", key=f"save_{m.id}", use_container_width=True):
                        if starting_player is None:
                            st.error("Please select a starting player before saving.")
                        else:
                            is_valid_video_link, normalized_video_link, video_link_error = validate_video_link(video_link_val)
                            if not is_valid_video_link:
                                st.error(video_link_error)
                            else:
                                games_payload = [
                                    {'winner': 'A' if g1_winner == m.player_a else ('B' if g1_winner == m.player_b else None)},
                                    {'winner': 'A' if g2_winner == m.player_a else ('B' if g2_winner == m.player_b else None)},
                                    {'winner': 'A' if g3_winner == m.player_a else ('B' if g3_winner == m.player_b else None)},
                                ]
                                
                                client.update_match(
                                    m.id,
                                    games=games_payload,
                                    starting_player=starting_player,
                                    went_in_time=went_in_time,
                                    match_type=getattr(m, 'match_type', 'Round'),
                                    video_link=normalized_video_link
                                )
                                st.toast(f"Result for {name_a} vs {name_b} saved!")
                                st.rerun()
