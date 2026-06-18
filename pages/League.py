import streamlit as st
from datastore_client import get_client
from utils import compute_standings, seed_playoff
from auth import require_auth
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="League")

require_auth()

client = get_client()

selected_league = st.session_state.get('current_league')
if not selected_league:
    st.info("No leagues found. Please create a league in League Management.")
    st.stop()

# Filter players and matches for the selected league
league_rounds = client.list_rounds(selected_league.id)
round_ids = {r.id for r in league_rounds}
all_matches = client.list_matches()
league_matches = [m for m in all_matches if getattr(m, 'round_id', None) in round_ids and getattr(m, 'match_type', 'Round') == 'Round']

# Render Dropdown for matches with a video_link
linked_videos = [m for m in all_matches if m.round_id in round_ids and getattr(m, "video_link", None)]

memberships = client.list_league_players(selected_league.id)
member_ids = {m.user_id for m in memberships}
all_users = client.list_users()
league_players = [u for u in all_users if u.id in member_ids]

table = compute_standings(league_players, league_matches)

# Informationen über Decks aus den League-Mitgliedschaften hinzufügen
all_decks = client.list_decks()
deck_lookup = {d.id: d for d in all_decks}
player_to_deck = {m.user_id: deck_lookup.get(m.deck_id) for m in memberships}

playoffs_generated = getattr(selected_league, 'playoffs_closed', False)

for row in table:
    deck = player_to_deck.get(row['player_id'])
    row['deck_name'] = deck.deck_name if deck else "Kein Deck"
    row['deck_link'] = deck.deck_list_link if (deck and playoffs_generated) else None

# --- Decklist submission traffic light ---
total_players = len(memberships)
user_id_to_name = {u.id: u.username for u in all_users}
submitted_count = sum(
    1 for m in memberships
    if "moxfield" in (getattr(deck_lookup.get(getattr(m, 'deck_id', None)), 'deck_list_link', '') or '').lower()
)
missing_users = [
    user_id_to_name.get(m.user_id, f"User {m.user_id}")
    for m in memberships
    if "moxfield" not in (getattr(deck_lookup.get(getattr(m, 'deck_id', None)), 'deck_list_link', '') or '').lower()
]
all_submitted = submitted_count == total_players and total_players > 0
light_color = "#2ecc71" if all_submitted else "#e74c3c"
light_emoji = "🟢" if all_submitted else "🔴"
st.markdown(
    f"""
    <div style="
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: {'rgba(46,204,113,0.12)' if all_submitted else 'rgba(231,76,60,0.12)'};
        border: 1.5px solid {light_color};
        border-radius: 20px;
        padding: 6px 16px;
        margin-bottom: 4px;
        font-size: 0.97em;
        font-weight: 500;
        color: {light_color};
    ">
        <span style="font-size:1.1em;">{light_emoji}</span>
        {submitted_count} out of {total_players} decks submitted
    </div>
    """,
    unsafe_allow_html=True
)
if missing_users:
    st.caption("Missing decklists: " + ", ".join(missing_users))
# --- End traffic light ---
if table:
    df = pd.DataFrame(table)

    # Mapping internal keys to display names
    col_mapping = {
        'player_name': 'Player',
        'deck_name': 'Deck',
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
    if playoffs_generated:
        col_mapping['deck_link'] = 'Decklist'

    # Sort by the primary metric and apply name mapping
    df.insert(0, 'Rank', range(1, len(df) + 1))
    df = df.sort_values(by='Rank', ascending=True).reset_index(drop=True)
    df = df.rename(columns=col_mapping)

    # Configuration for dynamic columns
    # Detect if the user is on a mobile device using the User-Agent header
    ua = st.context.headers.get("User-Agent", "")
    is_mobile = any(x in ua for x in ["Mobile", "Android", "iPhone", "iPad"])

    all_display_cols = ['Rank'] + list(col_mapping.values())
    
    if is_mobile:
        # Show a compact view for mobile users
        default_cols = ['Rank', 'Player', 'Points+GWR', 'Total Matches']
    else:
        # Show a more detailed view for desktop users
        default_cols = ['Rank', 'Player', 'Points+GWR', 'Total Matches', 'Deck']
        if playoffs_generated:
            default_cols.append('Decklist')

    selected_cols = st.multiselect("Select columns to display:", options=all_display_cols, default=default_cols)

    if selected_cols:
        col_config = {}
        if playoffs_generated:
            col_config["Decklist"] = st.column_config.LinkColumn("Decklist", display_text="🔗 Link")
        st.dataframe(
            df[selected_cols], 
            use_container_width=True, 
            hide_index=True,
            column_config=col_config
        )
    else:
        st.info("Select at least one column to display the table.")

    # Top-n playoffs control (admin only)
    max_top = len(df)
    playoff_options = [2]
    if max_top >= 4:
        playoff_options.append(4)
    if max_top >= 8:
        playoff_options.append(8)
    top_n = st.selectbox("Top N Player Playoffs", options=playoff_options, index=min(1, len(playoff_options)-1))

    def generate_playoffs_action():
        # Prevent double submission and indicate progress
        st.session_state['generating_playoffs'] = True

        # Check if playoffs already generated for this league
        if getattr(selected_league, 'playoffs_closed', False):
            st.warning("Playoffs already generated for this league.")
            st.session_state['generating_playoffs'] = False
            return

        # Check there are enough players
        if not league_players or len(league_players) < 2:
            st.error("Not enough players in the league to generate playoffs.")
            st.session_state['generating_playoffs'] = False
            return

        bracket = seed_playoff(table, top_n)
        pairs = bracket.get('pairs', [])
        bye = bracket.get('bye')

        if not pairs:
            st.error("No playoff pairs generated. Adjust Top N and try again.")
            st.session_state['generating_playoffs'] = False
            return

        # Create a new playoff round and persist matches
        try:
            with st.spinner("Generating playoff matches..."):
                league_rounds = client.list_rounds(selected_league.id)
                max_nr = max((r.nr for r in league_rounds), default=0)

                new_nr = max_nr + 1
                today = datetime.now().date()
                new_round = client.add_round(
                    league_id=selected_league.id,
                    nr=new_nr,
                    start_date=today.strftime('%Y-%m-%d'),
                    end_date=(today + timedelta(days=6)).strftime('%Y-%m-%d')
                )

                if top_n == 2:
                    initial_type = "Final"
                elif top_n == 4:
                    initial_type = "SemiFinal"
                else:
                    initial_type = "QuarterFinal"

                for p in pairs:
                    a = p['player_a']
                    b = p['player_b']
                    player_a_id = a.get('player_id')
                    player_b_id = b.get('player_id')
                    client.add_match(
                        player_a=player_a_id,
                        player_b=player_b_id,
                        round_id=new_round.id,
                        starting_player=None,
                        games=[{'winner': None}, {'winner': None}, {'winner': None}],
                        went_in_time=False,
                        match_type=initial_type
                    )

                # Mark playoffs as generated for the league
                client.update_league(selected_league.id, playoffs_closed=True)

                if bye:
                    st.info(f"Top seed gets a bye: {bye['player_name']}")

                st.success("Playoff matches generated and saved.")
        except Exception as e:
            st.error(f"Failed to generate playoffs: {e}")
        finally:
            # ensure generating flag is cleared; playoffs_closed will keep button disabled
            st.session_state['generating_playoffs'] = False

    # Show the Generate Playoffs control only for admins
    is_admin = getattr(st.session_state.get('user'), 'is_admin', False)
    disabled = getattr(selected_league, 'playoffs_closed', False)
    if is_admin:
        col1, col2 = st.columns([1, 3])
        with col1:
            st.button(
                "Generate Playoffs",
                disabled=disabled or st.session_state.get('generating_playoffs', False),
                on_click=generate_playoffs_action
            )
        with col2:
            if disabled:
                st.info("Playoffs already generated for this league. Generate Playoffs is disabled.")
            else:
                # Show bracket preview for admins before generation
                if st.button("Preview Bracket"):
                    bracket = seed_playoff(table, top_n)
                    pairs = bracket.get('pairs', [])
                    bye = bracket.get('bye')
                    st.subheader("Playoff Bracket Preview")
                    for p in pairs:
                        a = p['player_a']
                        b = p['player_b']
                        st.write(f"Seed {p['seed_a']} — {a['player_name']}  vs  Seed {p['seed_b']} — {b['player_name']}")
                    if bye:
                        st.info(f"Top seed gets a bye: {bye['player_name']}")
    else:
        # Non-admin users can still preview the bracket but not generate it
        if st.button("Preview Bracket"):
            bracket = seed_playoff(table, top_n)
            pairs = bracket.get('pairs', [])
            bye = bracket.get('bye')
            st.subheader("Playoff Bracket Preview")
            for p in pairs:
                a = p['player_a']
                b = p['player_b']
                st.write(f"Seed {p['seed_a']} — {a['player_name']}  vs  Seed {p['seed_b']} — {b['player_name']}")
            if bye:
                st.info(f"Top seed gets a bye: {bye['player_name']}")
else:
    st.info("No players or matches yet.")


if linked_videos:
    st.divider()  
    users = client.list_users()
    user_map = {u.id: u.username for u in users}
    round_map = {r.id: r.nr for r in league_rounds}
    
    # Sort by week first, then by player_a's username
    def sort_key(m):
        m_type = getattr(m, "match_type", "Round")
        week = round_map.get(m.round_id, 9999) if m_type == "Round" else 9999
        p_a_name = user_map.get(m.player_a, "Unknown").lower()
        return (week, p_a_name)
        
    linked_videos.sort(key=sort_key)
    
    def format_linked_match(m):
        p_a = user_map.get(m.player_a, "Unknown")
        p_b = user_map.get(m.player_b, "Unknown")
        m_type = getattr(m, "match_type", "Round")
        if m_type == "Round":
            r_obj = next((r for r in league_rounds if r.id == m.round_id), None)
            week_str = f" (Week {r_obj.nr})" if r_obj else ""
            return f"{p_a} vs {p_b}{week_str}"
        else:
            return f"{p_a} vs {p_b} ({m_type})"
            
    selected_link_match = st.selectbox(
        "Replay Streamed Matches",
        options=linked_videos,
        index=None,
        placeholder="Search or select a match...",
        format_func=format_linked_match,
        key="video_link_selector"
    )
    if selected_link_match:
        st.markdown(f"[🔗 {format_linked_match(selected_link_match)}]({selected_link_match.video_link})")

  