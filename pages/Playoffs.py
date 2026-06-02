import streamlit as st
from datastore_client import get_client
from utils import compute_standings
from auth import require_auth
from models import compute_match_summary

st.set_page_config(page_title="Playoffs", layout="wide")

require_auth()
client = get_client()

users = client.list_users()
matches = client.list_matches()

# If a league is selected, try to load persisted PlayOffs matches for that league
selected_league = st.session_state.get('current_league')
playoff_matches = []
league_round_matches = []
if selected_league:
    try:
        league_rounds = client.list_rounds(selected_league.id)
        round_ids = {r.id for r in league_rounds}
        playoff_types = ['QuarterFinal', 'SemiFinal', 'Final', 'MatchFor3rd']
        playoff_matches = [m for m in matches if getattr(m, 'match_type', '') in playoff_types and getattr(m, 'round_id', None) in round_ids]
        league_round_matches = [m for m in matches if getattr(m, 'round_id', None) in round_ids and getattr(m, 'match_type', 'Round') == 'Round']
    except Exception:
        playoff_matches = []

if not users:
    st.info("Add users first on User Management page.")
else:
    table = compute_standings(users, league_round_matches)
    
    # Determine if we are in a Top 4 or Top 8 scenario based on existing matches
    has_qf = any(getattr(m, 'match_type', '') == "QuarterFinal" for m in playoff_matches)
    top_n = 8 if has_qf else 4

    if len(table) < top_n:
        st.error(f"You need at least {top_n} players for the playoff bracket!")
    else:
        # Get top players based on the cut
        top_players = table[:top_n]
        top_4 = table[:4] # Still used for the simplified tree visualization
        
        # Initialize bracket in session state
        if 'bracket_initialized' not in st.session_state:
            st.session_state['bracket_initialized'] = True
            st.session_state['semifinals_winners'] = {}
            st.session_state['champion'] = None
        
        # Match result identification
        user_map = {u.id: u.username for u in users}
        # Find Semis by type
        sf_types = ["SemiFinal"]
        sf1_match = None
        sf2_match = None
        if len(top_4) >= 4:
            sf1_match = next((m for m in playoff_matches if getattr(m, 'match_type', '') in sf_types and {m.player_a, m.player_b} == {top_4[0]['player_id'], top_4[3]['player_id']}), None)
            sf2_match = next((m for m in playoff_matches if getattr(m, 'match_type', '') in sf_types and {m.player_a, m.player_b} == {top_4[1]['player_id'], top_4[2]['player_id']}), None)

        def get_winner_info(m):
            if not m: return None
            summ = compute_match_summary(m)
            if summ['match_result'] == 'A': return {'player_id': m.player_a, 'player_name': user_map.get(m.player_a, "Unknown")}
            if summ['match_result'] == 'B': return {'player_id': m.player_b, 'player_name': user_map.get(m.player_b, "Unknown")}
            return None

        def get_loser_info(m):
            if not m: return None
            summ = compute_match_summary(m)
            if summ['match_result'] == 'A': return {'player_id': m.player_b, 'player_name': user_map.get(m.player_b, "Unknown")}
            if summ['match_result'] == 'B': return {'player_id': m.player_a, 'player_name': user_map.get(m.player_a, "Unknown")}
            return None

        db_s1 = get_winner_info(sf1_match)
        db_s2 = get_winner_info(sf2_match)
        db_l1 = get_loser_info(sf1_match)
        db_l2 = get_loser_info(sf2_match)

        final_match = next((m for m in playoff_matches if getattr(m, 'match_type', '') == "Final"), None)
        if not final_match and db_s1 and db_s2: # fallback search
            final_match = next((m for m in playoff_matches if {m.player_a, m.player_b} == {db_s1['player_id'], db_s2['player_id']}), None)
        
        third_place_match = next((m for m in playoff_matches if getattr(m, 'match_type', '') == "MatchFor3rd"), None)
        db_champion = get_winner_info(final_match)

        tab_tree, tab_record = st.tabs(["Playoff Overview", "Record Match"])

        with tab_tree:
            if not playoff_matches:
                st.warning("Playoff overview is just a preview.")

            # Place semifinal winners if they exist (DB results override local session state)
            semi_1_winner = db_s1 or st.session_state['semifinals_winners'].get('semi_1')
            semi_2_winner = db_s2 or st.session_state['semifinals_winners'].get('semi_2')
            champion = db_champion or st.session_state['champion']

            # Render bracket HTML with SVG - responsive with viewBox
            bracket_html = '''
            <div style="display: flex; justify-content: center; align-items: center; margin: 20px 0; width: 100%;">
            <svg viewBox="0 0 1200 700" style="width: 100%; max-width: 100%; height: auto; aspect-ratio: 1200/700;">
            '''
            
            # Draw connector lines - straight lines that meet and no gaps
            # Semifinal 1 (left side): Platz 1 and 4 meet at (300, 350)
            bracket_html += '<line x1="150" y1="100" x2="150" y2="350" stroke="#999" stroke-width="2"/>'   # Platz 1 straight down
            bracket_html += '<line x1="150" y1="350" x2="300" y2="350" stroke="#999" stroke-width="2"/>'   # Horizontal to SF1 point
            bracket_html += '<line x1="150" y1="600" x2="150" y2="350" stroke="#999" stroke-width="2"/>'   # Platz 4 straight up
            
            # Semifinal 2 (right side): Platz 2 and 3 meet at (900, 350)
            bracket_html += '<line x1="1050" y1="100" x2="1050" y2="350" stroke="#999" stroke-width="2"/>'  # Platz 2 straight down
            bracket_html += '<line x1="1050" y1="350" x2="900" y2="350" stroke="#999" stroke-width="2"/>'   # Horizontal to SF2 point
            bracket_html += '<line x1="1050" y1="600" x2="1050" y2="350" stroke="#999" stroke-width="2"/>'  # Platz 3 straight up
            
            # From semifinals to champion - continuous line to meeting point
            bracket_html += '<line x1="300" y1="350" x2="900" y2="350" stroke="#999" stroke-width="2"/>'  # SF1 to SF2 (meeting point)
            
            # Helper function to create player box
            def create_player_box(x, y, name, rank, color="#e8f4f8"):
                return f'''<rect x="{x-80}" y="{y-25}" width="160" height="50" fill="{color}" stroke="#333" stroke-width="2" rx="5"/>
                          <text x="{x}" y="{y-5}" text-anchor="middle" font-size="12" font-weight="bold">{name[:20]}</text>
                          <text x="{x}" y="{y+10}" text-anchor="middle" font-size="10">{rank}</text>'''
            
            # Place top 4 players
            bracket_html += create_player_box(150, 100, top_4[0]['player_name'], 1)
            bracket_html += create_player_box(1050, 100, top_4[1]['player_name'], 2)
            bracket_html += create_player_box(1050, 600, top_4[2]['player_name'], 3)
            bracket_html += create_player_box(150, 600, top_4[3]['player_name'], 4)
            
            if semi_1_winner:
                bracket_html += create_player_box(300, 350, semi_1_winner['player_name'], "Semifinalist 1", "#90EE90")
            if semi_2_winner:
                bracket_html += create_player_box(900, 350, semi_2_winner['player_name'], "Semifinalist 2", "#90EE90")
            
            # Champion box - always drawn (centered at x=600)
            if champion:
                bracket_html += f'''<rect x="520" y="325" width="160" height="50" fill="#FFD700" stroke="#333" stroke-width="3" rx="5"/>
                                  <text x="600" y="350" text-anchor="middle" font-size="13" font-weight="bold">{champion['player_name']}</text>
                                  <text x="600" y="365" text-anchor="middle" font-size="10">🏆 CHAMPION</text>'''
            else:
                bracket_html += '''<rect x="520" y="325" width="160" height="50" fill="#f0f0f0" stroke="#999" stroke-width="2" stroke-dasharray="5,5" rx="5"/>
                                  <text x="600" y="355" text-anchor="middle" font-size="11" fill="#999">Champion</text>'''
            
            bracket_html += '</svg></div>'
            
            st.markdown(bracket_html, unsafe_allow_html=True)

        with tab_record:
            if not playoff_matches:
                st.warning("Playoffs were not generated yet.")
            def render_record_form(m, label):
                if not m:
                    st.info(f"No match record found for {label}.")
                    return
                name_a, name_b = user_map.get(m.player_a, "Unknown"), user_map.get(m.player_b, "Unknown")
                summ = compute_match_summary(m)
                can_edit = st.session_state.user.is_admin or st.session_state.user.id in [m.player_a, m.player_b]
                status = "🔴" if m.starting_player is None and not any(g.winner for g in m.games) else "🟢"
                
                with st.expander(f"{status} {label}: {name_a} vs {name_b}"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric(name_a, summ['player_a_game_wins'])
                    c3.metric(name_b, summ['player_b_game_wins'])
                    
                    g_opts = [None, name_a, name_b]
                    def get_winner_name(code):
                        return name_a if code == 'A' else (name_b if code == 'B' else None)
                    def name_to_code(name):
                        return 'A' if name == name_a else ('B' if name == name_b else None)
                    
                    gc1, gc2, gc3 = st.columns(3)
                    g1 = gc1.selectbox("Game 1 Winner", g_opts, index=g_opts.index(get_winner_name(m.games[0].winner if len(m.games) >= 1 else None)), key=f"r_g1_{m.id}", disabled=not can_edit)
                    g2 = gc2.selectbox("Game 2 Winner", g_opts, index=g_opts.index(get_winner_name(m.games[1].winner if len(m.games) >= 2 else None)), key=f"r_g2_{m.id}", disabled=not can_edit)
                    g3 = gc3.selectbox("Game 3 Winner", g_opts, index=g_opts.index(get_winner_name(m.games[2].winner if len(m.games) >= 3 else None)), key=f"r_g3_{m.id}", disabled=not can_edit)
                    
                    start_opts = [None, name_a, name_b]
                    start = st.selectbox("Starting player", start_opts, index=(start_opts.index(m.starting_player) if m.starting_player in start_opts else 0), key=f"r_start_{m.id}", disabled=not can_edit)
                    
                    if can_edit:
                        if st.button("Save Playoff Result", key=f"r_save_{m.id}", use_container_width=True):
                            payload = [{'winner': name_to_code(g1)}, {'winner': name_to_code(g2)}, {'winner': name_to_code(g3)}]
                            client.update_match(m.id, games=payload, starting_player=start, went_in_time=False, match_type=getattr(m, 'match_type', ''))
                            st.rerun()

            # Display matches grouped by their actual stage
            display_names = {
                "QuarterFinal": "Quarterfinals",
                "SemiFinal": "Semifinals",
                "Final": "Final",
                "MatchFor3rd": "Match for 3rd"
            }
            for m_type in ["QuarterFinal", "SemiFinal", "Final", "MatchFor3rd"]:
                type_matches = [m for m in playoff_matches if getattr(m, 'match_type', '') == m_type]
                if not type_matches: continue
                
                st.write(f"### {display_names.get(m_type, m_type)}")
                for m in type_matches:
                    label = display_names.get(m_type, m_type)
                    render_record_form(m, label)
            
            # Progression Logic
            qf_matches = [m for m in playoff_matches if getattr(m, 'match_type', '') == "QuarterFinal"]
            sf_matches = [m for m in playoff_matches if getattr(m, 'match_type', '') == "SemiFinal"]
            
            # 1. QF -> SF (For Top 8 cut)
            if qf_matches and not sf_matches and st.session_state.user.is_admin:
                all_qf_done = all(get_winner_info(m) is not None for m in qf_matches)
                if all_qf_done:
                    st.divider()
                    if st.button("Generate Semifinals", use_container_width=True, type="primary"):
                        # Logic: 1v8 winner plays 4v5 winner, 2v7 winner plays 3v6 winner
                        w1v8 = get_winner_info(next(m for m in qf_matches if {m.player_a, m.player_b} == {top_players[0]['player_id'], top_players[7]['player_id']}))
                        w4v5 = get_winner_info(next(m for m in qf_matches if {m.player_a, m.player_b} == {top_players[3]['player_id'], top_players[4]['player_id']}))
                        w2v7 = get_winner_info(next(m for m in qf_matches if {m.player_a, m.player_b} == {top_players[1]['player_id'], top_players[6]['player_id']}))
                        w3v6 = get_winner_info(next(m for m in qf_matches if {m.player_a, m.player_b} == {top_players[2]['player_id'], top_players[5]['player_id']}))
                        
                        round_id = qf_matches[0].round_id
                        client.add_match(player_a=w1v8['player_id'], player_b=w4v5['player_id'], round_id=round_id, match_type="SemiFinal", starting_player=None, games=[{'winner': None}, {'winner': None}, {'winner': None}], went_in_time=False)
                        client.add_match(player_a=w2v7['player_id'], player_b=w3v6['player_id'], round_id=round_id, match_type="SemiFinal", starting_player=None, games=[{'winner': None}, {'winner': None}, {'winner': None}], went_in_time=False)
                        st.rerun()

            # 2. SF -> Final/3rd (For all cuts)
            elif db_s1 and db_s2 and not final_match and st.session_state.user.is_admin:
                st.divider()
                if st.button("Generate Final & Match for 3rd", use_container_width=True, type="primary"):
                    # Create Final
                    client.add_match(
                        player_a=db_s1['player_id'], player_b=db_s2['player_id'], 
                        round_id=sf1_match.round_id, match_type="Final", 
                        starting_player=None, games=[{'winner': None}, {'winner': None}, {'winner': None}], went_in_time=False
                    )
                    # Create 3rd Place Match
                    if db_l1 and db_l2:
                        client.add_match(
                            player_a=db_l1['player_id'], player_b=db_l2['player_id'], 
                            round_id=sf1_match.round_id, match_type="MatchFor3rd", 
                            starting_player=None, games=[{'winner': None}, {'winner': None}, {'winner': None}], went_in_time=False
                        )
                    st.rerun()