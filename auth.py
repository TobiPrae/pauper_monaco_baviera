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
    from datastore_client import get_client
    
    # Initialize session state
    if "user" not in st.session_state:
        st.session_state.user = None
    
    # If not authenticated, show login and stop execution
    if st.session_state.user is None:
        st.image("assets/logo.png", width="stretch")
        
        def check_login():
            """Callback für Login-Check (Enter oder Button)"""
            username = st.session_state.login_username
            pwd = st.session_state.login_password
            
            client = get_client()
            users = client.list_users()
            
            # Find user by username
            user = next((u for u in users if u.username == username), None)
            
            if user and check_password(pwd, user.password_hash):
                st.session_state.user = user
                # Clear sensitive temporary state
                del st.session_state.login_password
            else:
                st.error("❌ Invalid username or password!")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("Username", key="login_username")
            st.text_input(
                "Speak, friend, and enter.", 
                type="password", 
                key="login_password", 
                on_change=check_login
            )
            st.button("Mellon", use_container_width=True, on_click=check_login)
        
        st.stop()  # Stop execution if not authenticated

def require_admin():
    """Require admin privileges. Calls require_auth() first."""
    require_auth()
    import streamlit as st
    if not st.session_state.user.is_admin:
        st.error("⛔ Access Denied: Administrator privileges required.")
        st.stop()
