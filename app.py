import streamlit as st
from dotenv import load_dotenv

# Load environment variables before importing data clients
load_dotenv()

from auth import require_auth
from datastore_client import get_client

# Page config similar to your example
st.set_page_config(
    page_title="Pauper Monaco",
    page_icon="🍆",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Unified authentication check
require_auth()

client = get_client()

is_admin = st.session_state.user.is_admin if st.session_state.user else False

# This places the image at the top of the sidebar
#st.sidebar.image("assets/logo.png", use_container_width=True)
st.logo("assets/logo.png")

# 3. Inject "Heavy" CSS to force the size
st.markdown(
    """
    <style>
        /* This targets the container that Streamlit uses for the logo */
        [data-testid="stSidebarHeader"] img {
            max-height: 120px !important;  /* Adjust this value as needed */
            width: auto !important;
            height: auto !important;
        }
        
        /* Optional: This reduces the padding around the logo to give it more room */
        [data-testid="stSidebarHeader"] {
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.divider()

with st.sidebar:
    # Global League Selection
    leagues = client.list_leagues()
    if leagues:
        leagues.sort(key=lambda x: x.nr, reverse=True)
        if "selected_league_id" not in st.session_state:
            st.session_state.selected_league_id = leagues[0].id

        idx = next((i for i, l in enumerate(leagues) if l.id == st.session_state.selected_league_id), 0)
        sel_league = st.selectbox(
            "Select League", 
            leagues, 
            index=idx, 
            format_func=lambda x: f"{x.league_name} ({x.nr})" if x.league_name else f"League {x.nr}",
            key="global_league_selector"
        )
        # Ensure current_league is always set before any potential rerun
        st.session_state.current_league = sel_league
        if sel_league.id != st.session_state.selected_league_id:
            st.session_state.selected_league_id = sel_league.id
            st.rerun()
    st.divider()
    st.caption(f"👤 Logged in as: **{st.session_state.user.username}**")
    if st.button("Logout", use_container_width=True, type="secondary"):
        st.session_state.user = None
        st.rerun()

league = st.Page("pages/League.py", title="League")
round_view = st.Page("pages/Round_View.py", title="Match Day")
playoffs = st.Page("pages/Playoffs.py", title="Playoffs")
player_management = st.Page("pages/Player_Management.py", title="Manage Users")
league_management = st.Page("pages/League_Management.py", title="Manage Leagues")
deck_management = st.Page("pages/Deck_Management.py", title="Manage Decks")
rules = st.Page("pages/Rules.py", title="Rules")
profile = st.Page("pages/Profile.py", title="Profile")

# Build navigation based on roles
pages = [rules, league, round_view, playoffs, profile, deck_management]
if is_admin:
    pages.extend([player_management, league_management])

pg = st.navigation(pages)



pg.run()
    
