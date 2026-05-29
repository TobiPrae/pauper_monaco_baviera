import streamlit as st
from dotenv import load_dotenv
from auth import require_auth

# Page config similar to your example
st.set_page_config(
    page_title="Pauper Monaco",
    page_icon="🍆",
    layout="centered",
    initial_sidebar_state="collapsed",
)

load_dotenv()

# Ensure session auth flag exists
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    require_auth()

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

league = st.Page("pages/League.py", title="League")
round_view = st.Page("pages/Round_View.py", title="Match Day")
playoffs = st.Page("pages/Playoffs.py", title="Playoffs")
player_management = st.Page("pages/Player_Management.py", title="Manage Players")
league_management = st.Page("pages/League_Management.py", title="Manage Leagues")
deck_management = st.Page("pages/Deck_Management.py", title="Manage Decks")

pg = st.navigation([league, round_view, playoffs, player_management, deck_management, league_management])

pg.run()
