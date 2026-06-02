import streamlit as st
from datastore_client import get_client
from utils import compute_standings, seed_playoff
from auth import require_auth
from datetime import datetime, timedelta

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

memberships = client.list_league_players(selected_league.id)
member_ids = {m.user_id for m in memberships}
all_users = client.list_users()
league_players = [u for u in all_users if u.id in member_ids]

table = compute_standings(league_players, league_matches)

# Informationen über Decks aus den League-Mitgliedschaften hinzufügen
all_decks = client.list_decks()
deck_lookup = {d.id: d for d in all_decks}
player_to_deck = {m.user_id: deck_lookup.get(m.deck_id) for m in memberships}

for row in table:
    deck = player_to_deck.get(row['player_id'])
    row['deck_name'] = deck.deck_name if deck else "Kein Deck"
    row['deck_link'] = deck.deck_list_link if deck else None

import pandas as pd
if table:
    df = pd.DataFrame(table)

    # Mapping internal keys to display names
    col_mapping = {
        'player_name': 'Player',
        'deck_name': 'Deck',
        'deck_link': 'Decklist',
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
    # Detect if the user is on a mobile device using the User-Agent header
    ua = st.context.headers.get("User-Agent", "")
    is_mobile = any(x in ua for x in ["Mobile", "Android", "iPhone", "iPad"])

    all_display_cols = ['Rank'] + list(col_mapping.values())
    
    if is_mobile:
        # Show a compact view for mobile users
        default_cols = ['Rank', 'Player', 'Points+GWR', 'Total Matches']
    else:
        # Show a more detailed view for desktop users
        default_cols = ['Rank', 'Player', 'Points+GWR', 'Total Matches', 'Deck', 'Decklist']

    selected_cols = st.multiselect("Select columns to display:", options=all_display_cols, default=default_cols)

    if selected_cols:
        st.dataframe(
            df[selected_cols], 
            use_container_width=True, 
            hide_index=True,
            column_config={"Decklist": st.column_config.LinkColumn("Decklist", display_text="🔗 Link")}
        )
    else:
        st.info("Select at least one column to display the table.")

    # Top-n playoffs control (admin only)
    max_top = len(df)
    top_n = st.number_input("Top N Player Playoffs", min_value=2, max_value=max_top, value=min(4, max_top), step=1)
    st.caption("Playoff seeding: best vs worst, 2nd best vs 2nd worst, etc.")

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

                for p in pairs:
                    a = p['player_a']
                    b = p['player_b']
                    player_a_id = a.get('player_id')
                    player_b_id = b.get('player_id')
                    # Persist a PlayOffs match (games are empty placeholders)
                    client.add_match(
                        player_a=player_a_id,
                        player_b=player_b_id,
                        round_id=new_round.id,
                        starting_player=None,
                        games=[{'winner': None}, {'winner': None}, {'winner': None}],
                        went_in_time=False,
                        match_type="PlayOffs"
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
            st.rerun()

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
