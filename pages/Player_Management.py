import streamlit as st
from datastore_client import get_client
from auth import require_admin, hash_password

st.set_page_config(page_title="Player Management")

require_admin()

client = get_client()

# Display success message from previous run if it exists
if "success_msg" in st.session_state:
    st.success(st.session_state.success_msg)
    del st.session_state.success_msg

st.subheader("Add New User")
with st.form("add_user"):
    username = st.text_input("Username", key="add_username")
    email = st.text_input("Email (Optional)", key="add_email")
    password = st.text_input("Initial Password", type="password", key="add_password")
    is_admin = st.checkbox("Grant Admin Privileges", key="add_is_admin")
    
    submitted = st.form_submit_button("Create User")
    if submitted:
        if not username or not password:
            st.error("Username and Password are required")
        else:
            # Hash the password before storage
            hashed_pw = hash_password(password)
            u = client.add_user(
                username=username, 
                email=email, 
                password_hash=hashed_pw, 
                is_admin=is_admin
            )
            st.session_state.success_msg = f"Successfully created user: {u.username}"
            st.rerun()


with st.expander("Edit Users", expanded=False):
    users = client.list_users()
    users.sort(key=lambda x: x.username.lower())

    if not users:
        st.info("No users found. Create one above.")
    else:
        selected_user = st.selectbox(
            "Select a user to modify",
            options=users,
            format_func=lambda x: f"{x.username} ({'Admin' if x.is_admin else 'Player'})"
        )

        if selected_user:
            with st.form(key=f"edit_user_form_{selected_user.id}"):
                new_username = st.text_input("Username", value=selected_user.username, key=f"new_uname_{selected_user.id}")
                new_email = st.text_input("Email", value=selected_user.email, key=f"new_email_{selected_user.id}")
                new_is_admin = st.checkbox("Is Admin?", value=selected_user.is_admin, key=f"new_admin_{selected_user.id}")
                
                save = st.form_submit_button("Save Changes")
                
                if save:
                    client.update_user(
                        selected_user.id, 
                        username=new_username, 
                        email=new_email, 
                        is_admin=new_is_admin
                    )
                    st.session_state.success_msg = f"User '{new_username}' updated successfully"
                    st.rerun()
