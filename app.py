import os
import streamlit as st
from dotenv import load_dotenv
from auth import require_auth

st.set_page_config(page_title="MTG Tournament Tracker", layout="wide")

load_dotenv()

# Bevor require_auth() aufgerufen wird, prüfen wir ob authentifiziert
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    # LOGIN SEITE - nur Login wird angezeigt
    require_auth()
else:
    # HAUPTSEITE nach erfolgreichem Login
    st.title("MTG Tournament Tracker")
    st.write("✅ Erfolgreich authentifiziert!")
    
    st.subheader("📖 Navigation")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("👥 Player Management", use_container_width=True):
            st.switch_page("pages/Player_Management.py")
        if st.button("📊 League", use_container_width=True):
            st.switch_page("pages/League.py")
    
    with col2:
        if st.button("📝 Record Game", use_container_width=True):
            st.switch_page("pages/Record_Game.py")
        if st.button("✏️ Edit Game", use_container_width=True):
            st.switch_page("pages/Edit_Game.py")
    
    with col3:
        if st.button("🏆 Playoffs", use_container_width=True):
            st.switch_page("pages/Playoffs.py")
    
    st.divider()
    st.info("Nutze die Buttons oben oder die Seiten-Navigation oben links um zwischen Seiten zu wechseln.")
