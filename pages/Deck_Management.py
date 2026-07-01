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

selected_league = st.session_state.get('current_league')
if not selected_league:
    st.info("No leagues found. Decks are managed per league.")
    st.stop()



with st.expander("Edit Decks", expanded=False):
    all_decks = client.list_decks()
    # Mitglieder der ausgewählten Liga laden
    memberships = client.list_league_players(selected_league.id)
    league_deck_ids = {m.deck_id for m in memberships}
    
    # Decks filtern: Admins sehen alle Decks der Liga, User nur ihr eigenes in dieser Liga
    if st.session_state.user.is_admin:
        decks = [d for d in all_decks if d.id in league_deck_ids]
    else:
        user_league_deck_ids = {m.deck_id for m in memberships if m.user_id == st.session_state.user.id}
        decks = [d for d in all_decks if d.id in user_league_deck_ids]

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
            deck_owners = {m.user_id for m in memberships if m.deck_id == selected_deck.id}
            
            # Authorization logic: Current user must be an admin OR in the owners list
            can_edit = st.session_state.user.is_admin or st.session_state.user.id in deck_owners
            
            # Resolve modifier username
            users = client.list_users()
            
            if can_edit:
                with st.form(key=f"edit_deck_form_{selected_deck.id}"):
                    new_name = st.text_input("Deck name", value=selected_deck.deck_name, key=f"new_name_{selected_deck.id}")
                    new_link = st.text_input("Deck list link", value=selected_deck.deck_list_link or "", key=f"new_link_{selected_deck.id}")
                    
                    if getattr(selected_deck, "modified_by", None) or getattr(selected_deck, "modified_at", None):
                        modified_by_val = getattr(selected_deck, "modified_by", None)
                        modified_at_val = getattr(selected_deck, "modified_at", None)
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

                    save = st.form_submit_button("Save Changes")
                    
                    if save:
                        client.update_deck(selected_deck.id, deck_name=new_name, deck_list_link=new_link)
                        st.session_state.success_msg = "Deck updated"
                        st.rerun()
            else:
                st.warning("🔒 This deck belongs to another player. Only the owner or an administrator can modify it.")
                st.text_input("Deck name", value=selected_deck.deck_name, disabled=True)
                st.text_input("Deck list link", value=selected_deck.deck_list_link or "", disabled=True)
                
                if getattr(selected_deck, "modified_by", None) or getattr(selected_deck, "modified_at", None):
                    modified_by_val = getattr(selected_deck, "modified_by", None)
                    modified_at_val = getattr(selected_deck, "modified_at", None)
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
            
            #if delete:
            #    confirm = st.checkbox("Confirm delete? This cannot be undone.", key=f"confirm_d_{selected_deck.id}")
            #    if confirm:
            #        client.delete_deck(selected_deck.id)
            #        st.success("Deck deleted")
            #        st.rerun()
            #    else:
            #        st.warning("Please check the confirmation box and click 'Delete Deck' again.")