import streamlit as st
from datastore_client import get_client
from utils import compute_standings
from auth import require_auth

st.set_page_config(page_title="Playoffs", layout="wide")

require_auth()
client = get_client()

players = client.list_players()
matches = client.list_matches()

if not players:
    st.info("Add players first on Player Management page.")
else:
    table = compute_standings(players, matches)
    
    if len(table) < 4:
        st.error("You need at least 4 players for the playoff bracket!")
    else:
        # Get top 4 players
        top_4 = table[:4]
        
        # Initialize bracket in session state
        if 'bracket_initialized' not in st.session_state:
            st.session_state['bracket_initialized'] = True
            st.session_state['semifinals_winners'] = {}
            st.session_state['champion'] = None
        
        st.divider()
        
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
                      <text x="{x}" y="{y+10}" text-anchor="middle" font-size="10">Rank {rank}</text>'''
        
        # Place top 4 players
        bracket_html += create_player_box(150, 100, top_4[0]['player_name'], 1)
        bracket_html += create_player_box(1050, 100, top_4[1]['player_name'], 2)
        bracket_html += create_player_box(1050, 600, top_4[2]['player_name'], 3)
        bracket_html += create_player_box(150, 600, top_4[3]['player_name'], 4)
        
        # Place semifinal winners if they exist
        semi_1_winner = st.session_state['semifinals_winners'].get('semi_1')
        semi_2_winner = st.session_state['semifinals_winners'].get('semi_2')
        
        if semi_1_winner:
            bracket_html += create_player_box(300, 350, semi_1_winner['player_name'], "SF1", "#90EE90")
        if semi_2_winner:
            bracket_html += create_player_box(900, 350, semi_2_winner['player_name'], "SF2", "#90EE90")
        
        # Champion box - always drawn (centered at x=600)
        if st.session_state['champion']:
            champion = st.session_state['champion']
            bracket_html += f'''<rect x="520" y="325" width="160" height="50" fill="#FFD700" stroke="#333" stroke-width="3" rx="5"/>
                              <text x="600" y="350" text-anchor="middle" font-size="13" font-weight="bold">{champion['player_name']}</text>
                              <text x="600" y="365" text-anchor="middle" font-size="10">🏆 CHAMPION</text>'''
        else:
            bracket_html += '''<rect x="520" y="325" width="160" height="50" fill="#f0f0f0" stroke="#999" stroke-width="2" stroke-dasharray="5,5" rx="5"/>
                              <text x="600" y="355" text-anchor="middle" font-size="11" fill="#999">Champion</text>'''
        
        bracket_html += '</svg></div>'
        
        st.markdown(bracket_html, unsafe_allow_html=True)
        
        st.divider()
        
        # Semifinal 1: Platz 1 vs Platz 4
        if not semi_1_winner:
            st.subheader("⚔️ Semifinal 1: Rank 1 vs Rank 4")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(f"✅ {top_4[0]['player_name']} wins", key="semi1_p1", use_container_width=True):
                    st.session_state['semifinals_winners']['semi_1'] = top_4[0]
                    st.rerun()
            
            with col2:
                if st.button(f"✅ {top_4[3]['player_name']} wins", key="semi1_p4", use_container_width=True):
                    st.session_state['semifinals_winners']['semi_1'] = top_4[3]
                    st.rerun()
            
            st.write("")
        
        # Semifinal 2: Platz 2 vs Platz 3
        if not semi_2_winner and semi_1_winner:
            st.subheader("⚔️ Semifinal 2: Rank 2 vs Rank 3")
            col3, col4 = st.columns(2)
            
            with col3:
                if st.button(f"✅ {top_4[1]['player_name']} wins", key="semi2_p2", use_container_width=True):
                    st.session_state['semifinals_winners']['semi_2'] = top_4[1]
                    st.rerun()
            
            with col4:
                if st.button(f"✅ {top_4[2]['player_name']} wins", key="semi2_p3", use_container_width=True):
                    st.session_state['semifinals_winners']['semi_2'] = top_4[2]
                    st.rerun()
        
        # Final
        if semi_1_winner and semi_2_winner and not st.session_state['champion']:
            st.divider()
            st.subheader("🏆 FINAL")
            
            col_final_1, col_final_2 = st.columns(2)
            
            with col_final_1:
                if st.button(f"👑 {semi_1_winner['player_name']} is Champion!", key="final_1", use_container_width=True):
                    st.session_state['champion'] = semi_1_winner
                    st.rerun()
            
            with col_final_2:
                if st.button(f"👑 {semi_2_winner['player_name']} is Champion!", key="final_2", use_container_width=True):
                    st.session_state['champion'] = semi_2_winner
                    st.rerun()
        
        # Show champion
        if st.session_state['champion']:
            st.divider()
            st.balloons()
            
            if st.button("🔄 New Tournament", use_container_width=True):
                st.session_state['bracket_initialized'] = False
                st.session_state['semifinals_winners'] = {}
                st.session_state['champion'] = None
                st.rerun()