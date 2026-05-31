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

#st.subheader("Add Deck")
#with st.form("add_deck"):
#    name = st.text_input("Deck name", key="add_deck_name")
#    link = st.text_input("Deck list link (URL)", key="add_deck_link")
#    submitted = st.form_submit_button("Add Deck")
#    if submitted:
#        if not name:
#            st.error("Deck name is required")
 #       else:
#            d = client.add_deck(deck_name=name, deck_list_link=link)
#            st.session_state.success_msg = f"Added {d.deck_name}"
#            st.rerun()


with st.expander("Edit Decks", expanded=False):
    all_decks = client.list_decks()
    
    # Filter decks based on role: Admins see all, Users see only their own
    if st.session_state.user.is_admin:
        decks = all_decks
    else:
        memberships = client.list_league_players()
        user_deck_ids = {m.deck_id for m in memberships if m.user_id == st.session_state.user.id}
        decks = [d for d in all_decks if d.id in user_deck_ids]

    decks.sort(key=lambda x: x.deck_name.lower())

    if not decks:
        st.info("No decks found. Decks are assigned when you are added to a League.")
    else:
        selected_deck = st.selectbox(
            "Select a deck to modify",
            options=decks,
            format_func=lambda x: x.deck_name
        )

        if selected_deck:
            # Ownership check: find users associated with this deck across all leagues
            memberships = client.list_league_players()
            deck_owners = {m.user_id for m in memberships if m.deck_id == selected_deck.id}
            
            # Authorization logic: Current user must be an admin OR in the owners list
            can_edit = st.session_state.user.is_admin or st.session_state.user.id in deck_owners
            
            if can_edit:
                with st.form(key=f"edit_deck_form_{selected_deck.id}"):
                    new_name = st.text_input("Deck name", value=selected_deck.deck_name, key=f"new_name_{selected_deck.id}")
                    new_link = st.text_input("Deck list link", value=selected_deck.deck_list_link or "", key=f"new_link_{selected_deck.id}")
                    save = st.form_submit_button("Save Changes")
                    
                    if save:
                        client.update_deck(selected_deck.id, deck_name=new_name, deck_list_link=new_link)
                        st.session_state.success_msg = "Deck updated"
                        st.rerun()
            else:
                st.warning("🔒 This deck belongs to another player. Only the owner or an administrator can modify it.")
                st.text_input("Deck name", value=selected_deck.deck_name, disabled=True)
                st.text_input("Deck list link", value=selected_deck.deck_list_link or "", disabled=True)
            
            #if delete:
            #    confirm = st.checkbox("Confirm delete? This cannot be undone.", key=f"confirm_d_{selected_deck.id}")
            #    if confirm:
            #        client.delete_deck(selected_deck.id)
            #        st.success("Deck deleted")
            #        st.rerun()
            #    else:
            #        st.warning("Please check the confirmation box and click 'Delete Deck' again.")