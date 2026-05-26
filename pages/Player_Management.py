import streamlit as st
from datastore_client import get_client

st.set_page_config(page_title="Player Management")

client = get_client()

st.title("Player Management")

st.subheader("Add player")
with st.form("add_player"):
    name = st.text_input("Player name", key="add_name")
    deck = st.text_input("Deck name", key="add_deck")
    link = st.text_input("Deck list URL", key="add_link")
    submitted = st.form_submit_button("Add player")
    if submitted:
        if not name:
            st.error("Player name is required")
        else:
            p = client.add_player(player_name=name, deck_name=deck or None, deck_list_link=link or None)
            st.success(f"Added {p.player_name}")
            st.rerun()


st.header("Players")
players = client.list_players()

q = st.text_input("Search players (by name)")
if q:
    players = [p for p in players if q.lower() in p.player_name.lower()]

sort_by = st.selectbox("Sort by", ["Name", "Deck name"], index=0)
if sort_by == "Name":
    players.sort(key=lambda x: x.player_name.lower())
else:
    players.sort(key=lambda x: (x.deck_name or "").lower())

if not players:
    st.info("No players found. Add players above.")
else:
    for p in players:
        with st.expander(p.player_name, expanded=False):
            cols = st.columns([3,2])
            cols[0].markdown(f"**Deck:** {p.deck_name or '-'}")
            cols[1].markdown(f"**Deck list:** {p.deck_list_link or '-'}")
            # Edit form
            with st.form(key=f"edit_{p.id}"):
                new_name = st.text_input("Player name", value=p.player_name, key=f"name_{p.id}")
                new_deck = st.text_input("Deck name", value=p.deck_name or "", key=f"deck_{p.id}")
                new_link = st.text_input("Deck list URL", value=p.deck_list_link or "", key=f"link_{p.id}")
                save = st.form_submit_button("Save")
                delete = st.form_submit_button("Delete player")
                if save:
                    client.update_player(p.id, player_name=new_name, deck_name=new_deck or None, deck_list_link=new_link or None)
                    st.success("Player updated")
                    st.rerun()
                if delete:
                    confirm = st.checkbox("Confirm delete? This cannot be undone.", key=f"confirm_{p.id}")
                    if confirm:
                        client.delete_player(p.id)
                        st.success("Player deleted")
                        st.rerun()
