import streamlit as st
from datastore_client import get_client
from auth import require_admin
from datetime import datetime, timedelta
from itertools import combinations

st.set_page_config(page_title="League Management")

require_admin()

client = get_client()

# Display success message from previous run if it exists
if "success_msg" in st.session_state:
    st.success(st.session_state.success_msg)
    del st.session_state.success_msg

users = client.list_users()
deck_format = lambda x: x.deck_name if x else "No Deck Selected"

# --- ADD LEAGUE ---
st.subheader("Add League")
with st.form("add_league"):
    nr = st.number_input("League Number", min_value=1, step=1)
    league_name = st.text_input("League Name", placeholder="e.g. Season 1")
    start_date = st.date_input("Start Date", value=datetime.now())
    weeks_rounds = st.number_input("Weeks for Rounds", min_value=1, value=6, step=1)
    weeks_playoffs = st.number_input("Weeks for Playoffs", min_value=1, value=2, step=1)
    
    st.write("---")
    st.write("**Initial Roster**")
    roster_selections = {}
    for u in users:
        is_selected = st.checkbox(u.username, key=f"add_u_{u.id}")
        if is_selected:
            roster_selections[u.id] = u.username
    
    submitted = st.form_submit_button("Add League")
    if submitted:
        calc_end = start_date + timedelta(weeks=weeks_rounds + weeks_playoffs)
        new_league = client.add_league(
            nr=nr,
            start_date=start_date.strftime('%Y-%m-%d'),
            weeks_rounds=weeks_rounds,
            weeks_playoffs=weeks_playoffs,
            end_date=calc_end.strftime('%Y-%m-%d'),
            league_name=league_name
        )

        # Automatically generate Rounds based on weeks_rounds
        created_rounds = []
        current_round_start = start_date
        for i in range(1, weeks_rounds + 1):
            # A round lasts 7 days (e.g., Mon to Sun)
            round_end = current_round_start + timedelta(days=6)
            new_round = client.add_round(
                league_id=new_league.id,
                nr=i,
                start_date=current_round_start.strftime('%Y-%m-%d'),
                end_date=round_end.strftime('%Y-%m-%d')
            )
            created_rounds.append(new_round)
            # Next round starts exactly one week later
            current_round_start += timedelta(days=7)

        for uid, u_name in roster_selections.items():
            # Create a default deck for each user and add them to the league
            default_deck = client.add_deck(deck_name=f"{u_name}'s Deck")
            client.add_user_to_league(new_league.id, uid, default_deck.id)
            
        # Automatically generate Round Robin matches using the Circle Method to avoid double-playing
        user_ids = list(roster_selections.keys())
        if len(user_ids) % 2 != 0:
            user_ids.append(None) # Add a 'Bye' user if odd number of users

        n = len(user_ids)
        pairing_groups = []
        temp_users = list(user_ids)

        # Generate groups where each user plays once (or has a bye)
        for _ in range(n - 1):
            group = []
            for i in range(n // 2):
                u1, u2 = temp_users[i], temp_users[n - 1 - i]
                if u1 is not None and u2 is not None:
                    group.append((u1, u2))
            pairing_groups.append(group)
            # Rotate users: fixed the first one, shift the rest
            temp_users = [temp_users[0]] + [temp_users[-1]] + temp_users[1:-1]

        num_rounds = len(created_rounds)
        if num_rounds > 0:
            for g_idx, group in enumerate(pairing_groups):
                # Distribute groups across the available league weeks
                assigned_round = created_rounds[g_idx % num_rounds]
                for u1_id, u2_id in group:
                    client.add_match(
                        player_a=u1_id,
                        player_b=u2_id,
                        round_id=assigned_round.id,
                        match_type="Round",
                        starting_player=None,
                        games=[{'winner': None}, {'winner': None}, {'winner': None}],
                        went_in_time=False
                    )
        st.session_state.success_msg = f"Added League {nr}"
        st.rerun()

# --- DELETE LEAGUE ---
st.divider()
st.subheader("Delete League")

leagues = client.list_leagues()
leagues.sort(key=lambda x: x.nr, reverse=True)

if not leagues:
    st.info("No leagues found.")
else:
    del_league = st.selectbox(
        "Select a league to delete",
        options=leagues,
        format_func=lambda x: f"{x.league_name} ({x.nr})" if x.league_name else f"League {x.nr}",
        key="delete_league_selector"
    )

    if del_league:
        is_locked = getattr(del_league, 'locked', False)

        if is_locked:
            st.warning(f"League {del_league.nr} is **locked** and cannot be deleted. Remove the lock first.")

        confirm = st.checkbox(
            "I understand this will permanently delete all matches, rounds, decks, roster entries, and the league itself.",
            key=f"confirm_delete_{del_league.id}",
            disabled=is_locked
        )

        if st.button("Delete League", type="primary", disabled=is_locked or not confirm, key="btn_delete_league"):
            league_id = del_league.id

            # 1. Gather related data
            rounds = client.list_rounds(league_id)
            round_ids = {r.id for r in rounds}
            league_players = client.list_league_players(league_id)
            deck_ids = {m.deck_id for m in league_players if m.deck_id}

            # 2. Delete matches belonging to this league's rounds
            all_matches = client.list_matches()
            league_matches = [m for m in all_matches if getattr(m, 'round_id', None) in round_ids]
            for m in league_matches:
                client.delete_match(m.id)

            # 3. Delete rounds
            for r in rounds:
                client.delete_round(r.id)

            # 4. Delete decks
            for did in deck_ids:
                client.delete_deck(did)

            # 5. Delete league players
            for lp in league_players:
                client.remove_player_from_league(lp.id)

            # 6. Delete the league itself
            client.delete_league(league_id)

            st.session_state.success_msg = f"League {del_league.nr} and all its data have been deleted."
            # Clear the selected league if it was the one deleted
            if st.session_state.get('selected_league_id') == league_id:
                remaining = [l for l in leagues if l.id != league_id]
                if remaining:
                    st.session_state.selected_league_id = remaining[0].id
                    st.session_state.current_league = remaining[0]
                else:
                    st.session_state.pop('selected_league_id', None)
                    st.session_state.pop('current_league', None)
            st.rerun()