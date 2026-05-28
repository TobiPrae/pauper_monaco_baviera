import streamlit as st
from dotenv import load_dotenv
from auth import require_auth
from components import show_logo

# Page config similar to your example
st.set_page_config(
    page_title="MTG Tournament Tracker",
    page_icon="assets/logo.jpg",
    layout="centered",
    initial_sidebar_state="collapsed",
)

load_dotenv()
show_logo()

# Ensure session auth flag exists
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    require_auth()
else:
    #st.title("MTG Tournament Tracker")
    #st.write("✅ Erfolgreich authentifiziert!")
    pass

st.set_page_config(
    page_title="B+T", 
    page_icon="assets/logo.png", 
    layout="centered",
    initial_sidebar_state="collapsed"
    )

league = st.Page("pages/League.py", title="League")
player_management = st.Page("pages/Player_Management.py", title="Manage Players")
playoffs = st.Page("pages/Playoffs.py", title="Playoffs")
record_game = st.Page("pages/Record_Game.py", title="Record Game")
edit_game = st.Page("pages/Edit_Game.py", title="Edit Game")

pg = st.navigation([league, player_management, playoffs, record_game, edit_game])

pg.run()