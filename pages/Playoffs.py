import streamlit as st
from datastore_client import get_client
from utils import compute_standings, seed_playoff
from auth import require_auth

st.set_page_config(page_title="Playoffs")

require_auth()
client = get_client()

st.title("Playoffs")
players = client.list_players()
matches = client.list_matches()

if not players:
    st.info("Add players first on Player Management page.")
else:
    table = compute_standings(players, matches)
    max_top = len(table)
    top_n = st.number_input("Top N playoffs", min_value=2, max_value=max_top, value=min(4, max_top), step=1)
    if st.button("Generate bracket"):
        bracket = seed_playoff(table, top_n)
        pairs = bracket.get('pairs', [])
        bye = bracket.get('bye')
        st.subheader("First round")
        # store bracket in session state for subsequent rounds
        st.session_state['playoff_round_1'] = {'pairs': pairs, 'bye': bye}

    # Show current round if present
    round_keys = [k for k in st.session_state.keys() if k.startswith('playoff_round_')]
    if round_keys:
        curr = sorted(round_keys)[-1]
        data = st.session_state[curr]
        pairs = data.get('pairs', [])
        bye = data.get('bye')
        winners = []
        for i, p in enumerate(pairs, start=1):
            col1, col2, col3 = st.columns([4,1,4])
            a = p['player_a']
            b = p['player_b']
            st.write(f"Match {i}: {a['player_name']} (Seed {p['seed_a']}) vs {b['player_name']} (Seed {p['seed_b']})")
            winner = st.selectbox(f"Winner of match {i}", [None, a['player_name'], b['player_name']], key=f"playoff_winner_{curr}_{i}")
            winners.append({'match': p, 'winner': winner})

        if bye:
            st.info(f"Bye: {bye['player_name']}")

        if st.button("Advance winners to next round"):
            # build next round players list
            next_players = []
            if bye:
                next_players.append(bye)
            for w in winners:
                winner_name = w['winner']
                if not winner_name:
                    st.error("Please select all winners before advancing")
                    break
                # find player dict
                if winner_name == w['match']['player_a']['player_name']:
                    next_players.append(w['match']['player_a'])
                else:
                    next_players.append(w['match']['player_b'])
            else:
                # create pairs for next round
                # sort next_players by original seed if available
                next_players_sorted = next_players
                n = len(next_players_sorted)
                pairs = []
                for i in range(n//2):
                    top = next_players_sorted[i]
                    bottom = next_players_sorted[n - 1 - i]
                    pairs.append({'seed_a': i+1, 'player_a': top, 'seed_b': n - i, 'player_b': bottom})
                new_round = f'playoff_round_{len(round_keys)+1}'
                st.session_state[new_round] = {'pairs': pairs, 'bye': None}
                st.rerun()
*** End Patch