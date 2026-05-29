import streamlit as st
from datastore_client import get_client
from auth import require_auth

st.set_page_config(page_title="Deck Management")

require_auth()

client = get_client()

# Display success message from previous run if it exists
if "success_msg" in st.session_state:
    st.success(st.session_state.success_msg)
    del st.session_state.success_msg

st.subheader("Add deck")
with st.form("add_deck"):
    name = st.text_input("Deck name", key="add_deck_name")
    link = st.text_input("Deck list link (URL)", key="add_deck_link")
    submitted = st.form_submit_button("Add deck")
    if submitted:
        if not name:
            st.error("Deck name is required")
        else:
            d = client.add_deck(deck_name=name, deck_list_link=link)
            st.session_state.success_msg = f"Added {d.deck_name}"
            st.rerun()


st.subheader("Edit Decks")
decks = client.list_decks()
decks.sort(key=lambda x: x.deck_name.lower())

if not decks:
    st.info("No decks found. Add decks above.")
else:
    selected_deck = st.selectbox(
        "Select a deck to modify",
        options=decks,
        format_func=lambda x: x.deck_name
    )

    if selected_deck:
        with st.form(key=f"edit_deck_form_{selected_deck.id}"):
            new_name = st.text_input("Deck name", value=selected_deck.deck_name, key=f"new_name_{selected_deck.id}")
            new_link = st.text_input("Deck list link", value=selected_deck.deck_list_link or "", key=f"new_link_{selected_deck.id}")
            save = st.form_submit_button("Save Changes")
            #delete = st.form_submit_button("Delete Deck")
            
            if save:
                client.update_deck(selected_deck.id, deck_name=new_name, deck_list_link=new_link)
                st.session_state.success_msg = "Deck updated"
                st.rerun()
            
            #if delete:
            #    confirm = st.checkbox("Confirm delete? This cannot be undone.", key=f"confirm_d_{selected_deck.id}")
            #    if confirm:
            #        client.delete_deck(selected_deck.id)
            #        st.success("Deck deleted")
            #        st.rerun()
            #    else:
            #        st.warning("Please check the confirmation box and click 'Delete Deck' again.")