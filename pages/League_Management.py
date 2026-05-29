import streamlit as st
from datastore_client import get_client
from auth import require_auth
from datetime import datetime, timedelta
from itertools import combinations

st.set_page_config(page_title="League Management")

require_auth()

client = get_client()

# Display success message from previous run if it exists
if "success_msg" in st.session_state:
    st.success(st.session_state.success_msg)
    del st.session_state.success_msg

players = client.list_players()
deck_format = lambda x: x.deck_name if x else "No Deck Selected"

# --- ADD LEAGUE ---
st.subheader("Add League")
with st.form("add_league"):
    nr = st.number_input("League Number", min_value=1, step=1)
    start_date = st.date_input("Start Date", value=datetime.now())
    weeks_rounds = st.number_input("Weeks for Rounds", min_value=1, value=6, step=1)
    weeks_playoffs = st.number_input("Weeks for Playoffs", min_value=1, value=2, step=1)
    
    st.write("---")
    st.write("**Initial Roster**")
    roster_selections = {}
    for p in players:
        is_selected = st.checkbox(p.player_name, key=f"add_p_{p.id}")
        if is_selected:
            roster_selections[p.id] = p.player_name
    
    submitted = st.form_submit_button("Add League")
    if submitted:
        calc_end = start_date + timedelta(weeks=weeks_rounds + weeks_playoffs)
        new_league = client.add_league(
            nr=nr,
            start_date=start_date.strftime('%Y-%m-%d'),
            weeks_rounds=weeks_rounds,
            weeks_playoffs=weeks_playoffs,
            end_date=calc_end.strftime('%Y-%m-%d')
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

        for pid, p_name in roster_selections.items():
            # Create a default deck for each player and add them to the league
            default_deck = client.add_deck(deck_name=f"{p_name}'s Deck")
            client.add_player_to_league(new_league.id, pid, default_deck.id)
            
        # Automatically generate Round Robin matches using the Circle Method to avoid double-playing
        player_ids = list(roster_selections.keys())
        if len(player_ids) % 2 != 0:
            player_ids.append(None) # Add a 'Bye' player if odd number of players

        n = len(player_ids)
        pairing_groups = []
        temp_players = list(player_ids)

        # Generate groups where each player plays once (or has a bye)
        for _ in range(n - 1):
            group = []
            for i in range(n // 2):
                p1, p2 = temp_players[i], temp_players[n - 1 - i]
                if p1 is not None and p2 is not None:
                    group.append((p1, p2))
            pairing_groups.append(group)
            # Rotate players: fixed the first one, shift the rest
            temp_players = [temp_players[0]] + [temp_players[-1]] + temp_players[1:-1]

        num_rounds = len(created_rounds)
        if num_rounds > 0:
            for g_idx, group in enumerate(pairing_groups):
                # Distribute groups across the available league weeks
                assigned_round = created_rounds[g_idx % num_rounds]
                for p1_id, p2_id in group:
                    client.add_match(
                        player_a=p1_id,
                        player_b=p2_id,
                        round_id=assigned_round.id,
                        match_type="Round",
                        starting_player=None,
                        games=[{'winner': None}, {'winner': None}, {'winner': None}],
                        went_in_time=False
                    )
        st.session_state.success_msg = f"Added League {nr}"
        st.rerun()

#with st.expander("Edit Leagues", expanded=False):
#    leagues = client.list_leagues()
#    leagues.sort(key=lambda x: x.nr, reverse=True)
#
#    if not leagues:
#        st.info("No leagues found. Add leagues above.")
#    else:
#        selected_league = st.selectbox(
#            "Select a league to modify",
#            options=leagues,
#            format_func=lambda x: f"League {x.nr}"
#        )
#
#        if selected_league:
#            current_memberships = client.list_league_players(selected_league.id)
#            member_ids = {m.player_id for m in current_memberships}
#            membership_map = {m.player_id: m for m in current_memberships}
#            default_players = [p for p in players if p.id in member_ids]
#
#            with st.form(key=f"edit_league_form_{selected_league.id}"):
#                new_nr = st.number_input("League Number", value=selected_league.nr, min_value=1, step=1)
#                
#                try:
#                    curr_start = datetime.strptime(selected_league.start_date, '%Y-%m-%d')
#                    curr_end = datetime.strptime(selected_league.end_date, '%Y-%m-%d')
#                except:
#                    curr_start = datetime.now()
#                    curr_end = datetime.now()
#
#                new_start = st.date_input("Start Date", value=curr_start, key=f"edit_start_{selected_league.id}")
#                new_weeks_rounds = st.number_input("Weeks for Rounds", value=getattr(selected_league, 'weeks_rounds', 6), min_value=1, step=1, key=f"edit_wr_{selected_league.id}")
#                new_weeks_playoffs = st.number_input("Weeks for Playoffs", value=getattr(selected_league, 'weeks_playoffs', 2), min_value=1, step=1, key=f"edit_wp_{selected_league.id}")
#                
#                st.write("---")
#                st.write("**Manage Roster & Decks**")
#                updated_roster = {}
#                for p in players:
#                    col1, col2 = st.columns([1, 2])
#                    in_league = col1.checkbox(p.player_name, value=(p.id in member_ids), key=f"edit_p_{p.id}")
#                    
#                    # Determine default deck index
#                    current_deck_id = membership_map[p.id].deck_id if p.id in member_ids else ""
#                    default_deck_idx = next((i for i, d in enumerate(deck_options) if d and d.id == current_deck_id), 0)
#                    
#                    sel_deck = col2.selectbox(f"Deck for {p.player_name}", options=deck_options, index=default_deck_idx, format_func=deck_format, key=f"edit_d_{p.id}", label_visibility="collapsed")
#                    if in_league: updated_roster[p.id] = sel_deck.id if sel_deck else ""
#
#                rr_closed = st.checkbox("Round Robin Closed", value=selected_league.round_robin_closed)
#                po_closed = st.checkbox("Playoffs Closed", value=selected_league.playoffs_closed)
#                
#                save = st.form_submit_button("Save Changes")
#                #delete = st.form_submit_button("Delete League")
#                
#                if save:
#                    calc_end = new_start + timedelta(weeks=new_weeks_rounds + new_weeks_playoffs)
#                    client.update_league(
#                        selected_league.id,
#                        nr=new_nr,
#                        start_date=new_start.strftime('%Y-%m-%d'),
#                        weeks_rounds=new_weeks_rounds,
#                        weeks_playoffs=new_weeks_playoffs,
#                        end_date=calc_end.strftime('%Y-%m-%d'),
#                        round_robin_closed=rr_closed,
#                        playoffs_closed=po_closed
#                    )
#                    
#                    # Remove players no longer selected
#                    for lp in current_memberships:
#                        if lp.player_id not in updated_roster:
#                            client.remove_player_from_league(lp.id)
#                    
#                    # Add or update players
#                    for pid, did in updated_roster.items():
#                        if pid not in member_ids:
#                            client.add_player_to_league(selected_league.id, pid, did)
#                        else:
#                            # Update deck if it changed
#                            if membership_map[pid].deck_id != did:
#                                client.update_league_player(membership_map[pid].id, deck_id=did)
#
#                    st.session_state.success_msg = "League updated"
#                    st.rerun()
            
            #if delete:
            #    confirm = st.checkbox("Confirm delete? This cannot be undone.", key=f"confirm_l_{selected_league.id}")
            #    if confirm:
            #        client.delete_league(selected_league.id)
            #        st.success("League deleted")
            #        st.rerun()
            #    else:
            #        st.warning("Please check the confirmation box and click 'Delete League' again.")