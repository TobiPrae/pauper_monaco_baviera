import streamlit as st
from datastore_client import get_client
from auth import require_auth

st.set_page_config(page_title="Player Management")

require_auth()

client = get_client()

st.subheader("Add player")
with st.form("add_player"):
    name = st.text_input("Player name", key="add_name")
    submitted = st.form_submit_button("Add player")
    if submitted:
        if not name:
            st.error("Player name is required")
        else:
            p = client.add_player(player_name=name)
            st.success(f"Added {p.player_name}")
            st.rerun()


st.header("Edit Players")
players = client.list_players()
players.sort(key=lambda x: x.player_name.lower())

if not players:
    st.info("No players found. Add players above.")
else:
    selected_player = st.selectbox(
        "Select a player to modify",
        options=players,
        format_func=lambda x: x.player_name
    )

    if selected_player:
        with st.form(key=f"edit_player_form_{selected_player.id}"):
            new_name = st.text_input("Player name", value=selected_player.player_name, key=f"new_name_{selected_player.id}")
            save = st.form_submit_button("Save Changes")
            #delete = st.form_submit_button("Delete Player")
            
            if save:
                client.update_player(selected_player.id, player_name=new_name)
                st.success("Player updated")
                st.rerun()
            
            #if delete:
            #    confirm = st.checkbox("Confirm delete? This cannot be undone.", key=f"confirm_{selected_player.id}")
            #    if confirm:
            #        client.delete_player(selected_player.id)
            #        st.success("Player deleted")
            #        st.rerun()
            #    else:
            #        st.warning("Please check the confirmation box and click 'Delete Player' again.")
