import streamlit as st
from datastore_client import get_client
from auth import require_auth
from datetime import datetime

st.set_page_config(page_title="League Management")

require_auth()

client = get_client()

# --- ADD LEAGUE ---
st.subheader("Add League")
with st.form("add_league"):
    nr = st.number_input("League Number", min_value=1, step=1)
    start_date = st.date_input("Start Date", value=datetime.now())
    end_date = st.date_input("End Date", value=datetime.now())
    
    submitted = st.form_submit_button("Add League")
    if submitted:
        client.add_league(
            nr=nr,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        st.success(f"Added League {nr}")
        st.rerun()

st.header("Edit Leagues")
leagues = client.list_leagues()
leagues.sort(key=lambda x: x.nr, reverse=True)

if not leagues:
    st.info("No leagues found. Add leagues above.")
else:
    selected_league = st.selectbox(
        "Select a league to modify",
        options=leagues,
        format_func=lambda x: f"League {x.nr}"
    )

    if selected_league:
        with st.form(key=f"edit_league_form_{selected_league.id}"):
            new_nr = st.number_input("League Number", value=selected_league.nr, min_value=1, step=1)
            
            try:
                curr_start = datetime.strptime(selected_league.start_date, '%Y-%m-%d')
                curr_end = datetime.strptime(selected_league.end_date, '%Y-%m-%d')
            except:
                curr_start = datetime.now()
                curr_end = datetime.now()

            new_start = st.date_input("Start Date", value=curr_start)
            new_end = st.date_input("End Date", value=curr_end)
            
            rr_closed = st.checkbox("Round Robin Closed", value=selected_league.round_robin_closed)
            po_closed = st.checkbox("Playoffs Closed", value=selected_league.playoffs_closed)
            
            save = st.form_submit_button("Save Changes")
            #delete = st.form_submit_button("Delete League")
            
            if save:
                client.update_league(
                    selected_league.id,
                    nr=new_nr,
                    start_date=new_start.strftime('%Y-%m-%d'),
                    end_date=new_end.strftime('%Y-%m-%d'),
                    round_robin_closed=rr_closed,
                    playoffs_closed=po_closed
                )
                st.success("League updated")
                st.rerun()
            
            #if delete:
            #    confirm = st.checkbox("Confirm delete? This cannot be undone.", key=f"confirm_l_{selected_league.id}")
            #    if confirm:
            #        client.delete_league(selected_league.id)
            #        st.success("League deleted")
            #        st.rerun()
            #    else:
            #        st.warning("Please check the confirmation box and click 'Delete League' again.")