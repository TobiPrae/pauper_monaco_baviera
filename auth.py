import os
import warnings
warnings.filterwarnings("ignore")

try:
    import bcrypt
    _HAS_BCRYPT = True
except Exception:
    import hashlib
    _HAS_BCRYPT = False

def hash_password(plain: str) -> str:
    if _HAS_BCRYPT:
        return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    else:
        return hashlib.sha256(plain.encode('utf-8')).hexdigest()

def check_password(plain: str, stored: str) -> bool:
    if _HAS_BCRYPT:
        try:
            return bcrypt.checkpw(plain.encode('utf-8'), stored.encode('utf-8'))
        except Exception:
            return False
    else:
        return hashlib.sha256(plain.encode('utf-8')).hexdigest() == stored

def require_auth():
    """Require authentication before accessing the page. Must be called at the top of each page (before st.set_page_config)."""
    import streamlit as st
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Initialize session state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    # If not authenticated, show login and stop execution
    if not st.session_state.authenticated:
        st.title("MTG Tournament Tracker — Login")
        
        def check_login():
            """Callback für Login-Check (Enter oder Button)"""
            pwd = st.session_state.login_password
            env_hash = os.environ.get("STREAMLIT_PASSWORD_HASH")
            env_plain = os.environ.get("STREAMLIT_PASSWORD")
            
            valid = False
            if env_hash:
                valid = check_password(pwd, env_hash)
            elif env_plain:
                valid = (pwd == env_plain)
            else:
                st.error("❌ Passwort nicht konfiguriert. Setze STREAMLIT_PASSWORD oder STREAMLIT_PASSWORD_HASH als Umgebungsvariable.")
                st.stop()
            
            if valid:
                st.session_state.authenticated = True
            else:
                st.error("❌ Falsches Passwort!")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("Passwort eingeben:", type="password", key="login_password", on_change=check_login)
            st.button("Anmelden", use_container_width=True, on_click=check_login)
        
        st.stop()  # Stop execution if not authenticated
