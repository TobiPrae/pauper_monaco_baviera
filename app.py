import os
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from auth import check_password

load_dotenv()

# Support either a plain password (`STREAMLIT_PASSWORD`) or a hashed password (`STREAMLIT_PASSWORD_HASH`).
PLAIN_PASSWORD = os.environ.get("STREAMLIT_PASSWORD")
HASHED_PASSWORD = os.environ.get("STREAMLIT_PASSWORD_HASH")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("MTG Tournament Tracker — Login")
    pwd = st.text_input("Password", type="password")
    if st.button("Enter"):
        # Prefer hashed password if provided
        env_hash = HASHED_PASSWORD or (st.secrets.get("password_hash") if "password_hash" in st.secrets else None)
        env_plain = PLAIN_PASSWORD or (st.secrets.get("password") if "password" in st.secrets else None)
        valid = False
        if env_hash:
            valid = check_password(pwd, env_hash)
        elif env_plain:
            valid = (pwd == env_plain)

        if valid:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid password. Set STREAMLIT_PASSWORD or STREAMLIT_PASSWORD_HASH env or secrets.")
else:
    st.title("MTG Tournament Tracker")
    st.write("Use the pages menu to navigate: Player Management, League, Record Game, Edit Game.")
    st.write("If you don't see pages, ensure files exist in the `pages/` folder.")
