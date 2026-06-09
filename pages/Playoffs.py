import streamlit as st
from datastore_client import get_client
from utils import compute_standings
from auth import require_auth
from models import compute_match_summary

st.set_page_config(page_title="Playoffs", layout="wide")

require_auth()
client = get_client()

all_users = client.list_users()
matches = client.list_matches()

# If a league is selected, try to load persisted PlayOffs matches for that league
selected_league = st.session_state.get('current_league')
if not selected_league:
    st.info("No leagues found. Please create a league in League Management.")
    st.stop()

memberships = client.list_league_players(selected_league.id)
member_ids = {m.user_id for m in memberships}
league_players = [u for u in all_users if u.id in member_ids]

playoff_matches = []
league_round_matches = []
try:
    league_rounds = client.list_rounds(selected_league.id)
    round_ids = {r.id for r in league_rounds}
    playoff_types = ['QuarterFinal', 'SemiFinal', 'Final', 'MatchFor3rd']
    playoff_matches = [m for m in matches if getattr(m, 'match_type', '') in playoff_types and getattr(m, 'round_id', None) in round_ids]
    league_round_matches = [m for m in matches if getattr(m, 'round_id', None) in round_ids and m.match_type == 'Round']
except Exception:
    playoff_matches = []

if not league_players:
    st.info("No players found for this league. Add players in League Management.")
else:
    table = compute_standings(league_players, league_round_matches)
    user_map = {u.id: u.username for u in all_users}
    
    # --- Helpers ---
    def get_info(m, role='winner'):
        if not m: return None
        summ = compute_match_summary(m)
        res = summ['match_result']
        p_id = m.player_a if (role == 'winner' and res == 'A') or (role == 'loser' and res == 'B') else m.player_b
        return {'id': p_id, 'name': user_map.get(p_id, "Unknown")} if res in ('A', 'B') else None

    def get_pair_names(m, p1_id=None):
        if not m: return ("TBD", "TBD")
        if p1_id and m.player_b == p1_id: return (user_map.get(m.player_b, "Unknown"), user_map.get(m.player_a, "Unknown"))
        return (user_map.get(m.player_a, "Unknown"), user_map.get(m.player_b, "Unknown"))

    # --- Slot Mapping ---
    qf_pool = [m for m in playoff_matches if m.match_type == "QuarterFinal"]
    sf_pool = [m for m in playoff_matches if m.match_type == "SemiFinal"]
    top_n = 8 if qf_pool else 4
    top_players = table[:top_n]

    def pop_match(p_id, pool):
        for i, m in enumerate(pool):
            if p_id in (m.player_a, m.player_b): return pool.pop(i)
        return None

    s = {} # Slots
    if top_n == 8:
        s.update({f'qf{i+1}': pop_match(top_players[idx]['player_id'], qf_pool) for i, idx in enumerate([0, 3, 1, 2])})
        w = {k: get_info(v) for k, v in s.items()}
        s['sf1'] = pop_match(w['qf1']['id'] if w['qf1'] else None, sf_pool) or pop_match(w['qf2']['id'] if w['qf2'] else None, sf_pool)
        s['sf2'] = pop_match(w['qf3']['id'] if w['qf3'] else None, sf_pool) or pop_match(w['qf4']['id'] if w['qf4'] else None, sf_pool)
    else:
        s.update({f'sf{i+1}': pop_match(top_players[i]['player_id'], sf_pool) for i in range(2)})

    final_match = next((m for m in playoff_matches if m.match_type == "Final"), None)
    db_champ, db_s1, db_s2 = get_info(final_match), get_info(s.get('sf1')), get_info(s.get('sf2'))

    # --- Rendering ---
    tab_tree, tab_record = st.tabs(["Playoff Overview", "Record Match"])

    with tab_tree:
        svg = '<div style="display: flex; justify-content: center; margin: 20px 0;"><svg viewBox="0 0 1200 700" style="width: 100%; max-width: 1200px; height: auto;">'
        def box(x, y, name, label, color="#e8f4f8"):
            return f'<rect x="{x-90}" y="{y-30}" width="180" height="60" fill="{color}" stroke="#333" stroke-width="3" rx="5"/><text x="{x}" y="{y-5}" text-anchor="middle" font-size="16" font-weight="bold">{name[:20]}</text><text x="{x}" y="{y+15}" text-anchor="middle" font-size="12">{label}</text>'

        if top_n == 8:
            for side, x, ids, y_off in [('L', 100, [0, 7, 3, 4], 0), ('R', 1100, [1, 6, 2, 5], 0)]:
                svg += f'<line x1="{x}" y1="100" x2="{x}" y2="200" stroke="#999" stroke-width="3"/><line x1="{x}" y1="600" x2="{x}" y2="500" stroke="#999" stroke-width="3"/><line x1="{x}" y1="200" x2="{x + (200 if side=="L" else -200)}" y2="200" stroke="#999" stroke-width="3"/><line x1="{x}" y1="500" x2="{x + (200 if side=="L" else -200)}" y2="500" stroke="#999" stroke-width="3"/><line x1="{x + (200 if side=="L" else -200)}" y1="200" x2="{x + (200 if side=="L" else -200)}" y2="350" stroke="#999" stroke-width="3"/><line x1="{x + (200 if side=="L" else -200)}" y1="500" x2="{x + (200 if side=="L" else -200)}" y2="350" stroke="#999" stroke-width="3"/>'
                for i, idx in enumerate(ids):
                    m = s.get(f'qf{1 if idx in (0,7) else (2 if idx in (3,4) else (3 if idx in (1,6) else 4))}')
                    names = get_pair_names(m, top_players[idx]['player_id'])
                    svg += box(x, 70 if i==0 else (130 if i==1 else (570 if i==2 else 630)), names[0], f"Seed {idx+1}")
            for i, k in enumerate(['qf1', 'qf2', 'qf3', 'qf4']):
                info = get_info(s.get(k))
                if info: svg += box(300 if i < 2 else 900, 200 if i % 2 == 0 else 500, info['name'], f"QF {i+1} Winner", "#e1f5fe")
        else:
            for side, x, ids in [('L', 150, [0, 3]), ('R', 1050, [1, 2])]:
                svg += f'<line x1="{x}" y1="100" x2="{x}" y2="350" stroke="#999" stroke-width="3"/><line x1="{x}" y1="600" x2="{x}" y2="350" stroke="#999" stroke-width="3"/><line x1="{x}" y1="350" x2="{300 if side=="L" else 900}" y2="350" stroke="#999" stroke-width="3"/>'
                m = s.get('sf1' if side == 'L' else 'sf2')
                p1, p2 = get_pair_names(m, top_players[ids[0]]['player_id'])
                svg += box(x, 100, p1 if m else top_players[ids[0]]['player_name'], f"Seed {ids[0]+1}")
                svg += box(x, 600, p2 if m else top_players[ids[1]]['player_name'], f"Seed {ids[1]+1}")

        svg += '<line x1="300" y1="350" x2="900" y2="350" stroke="#999" stroke-width="3"/>'
        if db_s1: svg += box(300, 350, db_s1['name'], "Semi 1", "#90EE90")
        if db_s2: svg += box(900, 350, db_s2['name'], "Semi 2", "#90EE90")
        if db_champ: svg += box(600, 350, db_champ['name'], "🏆 CHAMPION", "#FFD700")
        else: svg += f'<rect x="510" y="320" width="180" height="60" fill="#f0f0f0" stroke="#999" stroke-width="3" stroke-dasharray="5,5" rx="5"/><text x="600" y="355" text-anchor="middle" fill="#999" font-size="14">Champion</text>'
        st.markdown(svg + "</svg></div>", unsafe_allow_html=True)

    with tab_record:
        def record_form(m, label):
            if not m: return st.info(f"No match record for {label}")
            p1, p2 = user_map.get(m.player_a, "U"), user_map.get(m.player_b, "U")
            summ = compute_match_summary(m)
            can_edit = st.session_state.user.is_admin or st.session_state.user.id in (m.player_a, m.player_b)
            with st.expander(f"{'🔴' if not any(g.winner for g in m.games) else '🟢'} {label}: {p1} vs {p2}"):
                c = st.columns(3); c[0].metric(p1, summ['player_a_game_wins']); c[2].metric(p2, summ['player_b_game_wins'])
                opts = [None, p1, p2]
                gc = st.columns(3)
                g1 = gc[0].selectbox("G1", opts, index=opts.index(p1 if m.games[0].winner=='A' else (p2 if m.games[0].winner=='B' else None)), key=f"p_g1_{m.id}", disabled=not can_edit)
                g2 = gc[1].selectbox("G2", opts, index=opts.index(p1 if m.games[1].winner=='A' else (p2 if m.games[1].winner=='B' else None)), key=f"p_g2_{m.id}", disabled=not can_edit)
                g3 = gc[2].selectbox("G3", opts, index=opts.index(p1 if m.games[2].winner=='A' else (p2 if m.games[2].winner=='B' else None)), key=f"p_g3_{m.id}", disabled=not can_edit)
                start = st.selectbox("Start", opts, index=opts.index(m.starting_player), key=f"p_s_{m.id}", disabled=not can_edit)
                if can_edit and st.button("Save", key=f"p_save_{m.id}", use_container_width=True):
                    client.update_match(m.id, games=[{'winner': 'A' if g==p1 else ('B' if g==p2 else None)} for g in (g1,g2,g3)], starting_player=start, match_type=m.match_type)
                    st.rerun()

        for mt, label in [("QuarterFinal", "Quarterfinals"), ("SemiFinal", "Semifinals"), ("Final", "Final"), ("MatchFor3rd", "3rd Place")]:
            ms = [m for m in playoff_matches if m.match_type == mt]
            if ms: 
                st.write(f"### {label}")
                for m in ms: record_form(m, label)

        if st.session_state.user.is_admin:
            qfs, sfs = [m for m in playoff_matches if m.match_type == "QuarterFinal"], [m for m in playoff_matches if m.match_type == "SemiFinal"]
            if qfs and not sfs and all(get_info(m) for m in qfs):
                if st.button("Generate Semifinals", use_container_width=True, type="primary"):
                    w = {k: get_info(v) for k, v in s.items() if k.startswith('qf')}
                    for p_a, p_b in [(w['qf1'], w['qf2']), (w['qf3'], w['qf4'])]:
                        client.add_match(player_a=p_a['id'], player_b=p_b['id'], round_id=qfs[0].round_id, match_type="SemiFinal", starting_player=None, games=[{'winner':None}]*3)
                    st.rerun()
            elif db_s1 and db_s2 and not final_match:
                if st.button("Generate Final & 3rd Place", use_container_width=True, type="primary"):
                    l1, l2 = get_info(s['sf1'], 'loser'), get_info(s['sf2'], 'loser')
                    client.add_match(player_a=db_s1['id'], player_b=db_s2['id'], round_id=s['sf1'].round_id, match_type="Final", starting_player=None, games=[{'winner':None}]*3)
                    if l1 and l2: client.add_match(player_a=l1['id'], player_b=l2['id'], round_id=s['sf1'].round_id, match_type="MatchFor3rd", starting_player=None, games=[{'winner':None}]*3)
                    st.rerun()