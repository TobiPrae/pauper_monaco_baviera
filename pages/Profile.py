import streamlit as st
from datastore_client import get_client
from auth import require_auth, hash_password
from utils import validate_password

st.set_page_config(page_title="Profile")

require_auth()
client = get_client()
user = st.session_state.user

st.title("My Profile")
st.write(f"Account created as: **{user.original_username}**")

users = client.list_users()
if getattr(user, "modified_by", None) or getattr(user, "modified_at", None):
    modified_by_val = getattr(user, "modified_by", None)
    modified_at_val = getattr(user, "modified_at", None)
    modifier = next((u for u in users if u.id == modified_by_val), None) if modified_by_val else None
    modifier_display = modifier.username if modifier else (modified_by_val or "Unknown")
    if modified_at_val:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(modified_at_val)
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            formatted_time = modified_at_val
        st.caption(f"Last modified by: **{modifier_display}** on **{formatted_time}**")
    else:
        st.caption(f"Last modified by: **{modifier_display}**")

st.divider()

with st.form("change_username"):
    st.subheader("Update Display Name")
    st.caption("This will change how your name appears in standings and matches as well as your Login Companion.")
    new_username = st.text_input("New Companion", value=user.username)
    submit_username = st.form_submit_button("Save Companion")
    
    if submit_username:
        if not new_username:
            st.error("Companion cannot be empty")
        elif new_username == user.username:
            st.info("Companion is the same, no changes made.")
        else:
            existing_user = client.get_user_by_username(new_username)
            if existing_user and existing_user.id != user.id:
                st.error("This username is already taken. Please choose a different one.")
            else:
                updated_user = client.update_user(user.id, username=new_username)
                if updated_user:
                    st.session_state.user = updated_user
                    st.success("Companion updated!")
                    st.rerun()

st.divider()

with st.form("change_password"):
    st.subheader("Change Password")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm New Password", type="password")
    submit_password = st.form_submit_button("Update Password")
    
    if submit_password:
        is_valid, error_msg = validate_password(new_password, confirm_password)
        if not is_valid:
            st.error(error_msg)
        else:
            hashed_pw = hash_password(new_password)
            updated_user = client.update_user(user.id, password_hash=hashed_pw)
            if updated_user:
                st.session_state.user = updated_user
                st.success("Password updated successfully!")
            else:
                st.error("Failed to update password.")

st.divider()

leagues = client.list_leagues()
if leagues:
    leagues.sort(key=lambda x: x.nr, reverse=True)
    with st.form("default_league"):
        st.subheader("Set Default League")
        st.caption("Choose which league should be pre-selected when you log in.")
        
        options = [None] + leagues
        
        def format_option(opt):
            if opt is None:
                return "None (Latest League)"
            return f"{opt.league_name} ({opt.nr})" if opt.league_name else f"League {opt.nr}"
        
        current_default_id = getattr(user, "default_league_id", None)
        default_index = 0
        if current_default_id:
            for idx, l in enumerate(leagues):
                if l.id == current_default_id:
                    default_index = idx + 1
                    break
        
        selected_default = st.selectbox(
            "Default League",
            options=options,
            index=default_index,
            format_func=format_option
        )
        
        submit_default = st.form_submit_button("Save Default League")
        if submit_default:
            new_default_id = selected_default.id if selected_default else None
            updated_user = client.update_user(user.id, default_league_id=new_default_id)
            if updated_user:
                st.session_state.user = updated_user
                st.session_state.selected_league_id = new_default_id if new_default_id else leagues[0].id
                st.session_state.current_league = selected_default if selected_default else leagues[0]
                st.success("Default league preference updated!")
                st.rerun()
            else:
                st.error("Failed to update default league preference.")
