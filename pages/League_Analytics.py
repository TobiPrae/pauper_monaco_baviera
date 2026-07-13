import html as html_mod
from collections import defaultdict

import streamlit as st
import pandas as pd

from auth import require_auth
from datastore_client import get_client
from models import compute_match_summary
from streamlit.components.v1 import html
from utils import compute_standings

@st.cache_data
def build_head_to_head_matrix(match_records, filter_option):
    def _is_playoff(match_type):
        return match_type is not None and match_type != 'Round'

    def _include_record(match_type):
        if filter_option == 'Regular Season':
            return match_type == 'Round'
        if filter_option == 'Playoffs Only':
            return _is_playoff(match_type)
        return True

    filtered = [
        {
            'league_name': rec[0],
            'round_number': rec[1],
            'match_type': rec[2],
            'date': rec[3],
            'player_a': rec[4],
            'deck_a': rec[5],
            'player_b': rec[6],
            'deck_b': rec[7],
            'match_result': rec[8],
            'total_games': rec[9],
            'player_a_game_wins': rec[12],
            'player_b_game_wins': rec[13],
            'video_link': rec[10],
            'match_id': rec[11],
        }
        for rec in match_records
        if _include_record(rec[2])
    ]

    players = sorted({rec['player_a'] for rec in filtered} | {rec['player_b'] for rec in filtered})
    matrix_df = pd.DataFrame('', index=players, columns=players)
    tooltip_df = pd.DataFrame('', index=players, columns=players)

    row_stats = defaultdict(lambda: {
        'wins': 0,
        'losses': 0,
        'draws': 0,
        'matches': 0,
        'games': 0,
        'game_wins': 0,
        'last_date': None,
    })
    pair_stats = {}
    details = []

    for rec in filtered:
        player_a = rec['player_a']
        player_b = rec['player_b']
        if player_a == player_b:
            continue

        outcome = rec['match_result']
        total_games = rec['total_games']
        a_game_wins = rec['player_a_game_wins']
        b_game_wins = rec['player_b_game_wins']
        date = rec['date']

        if outcome == 'A':
            row_stats[(player_a, player_b)]['wins'] += 1
            row_stats[(player_a, player_b)]['losses'] += 0
            row_stats[(player_b, player_a)]['losses'] += 1
            row_stats[(player_b, player_a)]['wins'] += 0
        elif outcome == 'B':
            row_stats[(player_a, player_b)]['losses'] += 1
            row_stats[(player_b, player_a)]['wins'] += 1
        else:
            row_stats[(player_a, player_b)]['draws'] += 1
            row_stats[(player_b, player_a)]['draws'] += 1

        for key, row_wins, opp_wins in [
            ((player_a, player_b), a_game_wins, b_game_wins),
            ((player_b, player_a), b_game_wins, a_game_wins),
        ]:
            row_stats[key]['matches'] += 1
            row_stats[key]['games'] += total_games
            row_stats[key]['game_wins'] += row_wins
            last_date = pd.to_datetime(row_stats[key]['last_date'], errors='coerce') if row_stats[key]['last_date'] is not None else None
            current_date = pd.to_datetime(date, errors='coerce')
            if pd.notna(current_date) and (last_date is None or current_date >= last_date):
                row_stats[key]['last_date'] = date

        pair_key = tuple(sorted([player_a, player_b]))
        if pair_key not in pair_stats:
            pair_stats[pair_key] = {
                'matches': 0,
                'wins_a': 0,
                'wins_b': 0,
                'draws': 0,
                'games': 0,
                'last_date': None,
            }

        key_stats = pair_stats[pair_key]
        key_stats['matches'] += 1
        key_stats['games'] += total_games
        if outcome == 'A':
            if player_a == pair_key[0]:
                key_stats['wins_a'] += 1
            else:
                key_stats['wins_b'] += 1
        elif outcome == 'B':
            if player_b == pair_key[0]:
                key_stats['wins_a'] += 1
            else:
                key_stats['wins_b'] += 1
        else:
            key_stats['draws'] += 1

        current_date = pd.to_datetime(date, errors='coerce')
        last_date = pd.to_datetime(key_stats['last_date'], errors='coerce') if key_stats['last_date'] is not None else None
        if pd.notna(current_date) and (last_date is None or current_date >= last_date):
            key_stats['last_date'] = date

        result_text = 'Draw' if outcome == 'D' else ('Player A wins' if outcome == 'A' else 'Player B wins')
        details.append({
            'League': rec['league_name'],
            'Round': rec['round_number'],
            'Match Type': rec['match_type'],
            'Date': rec['date'],
            'Player A': player_a,
            'Deck A': rec['deck_a'],
            'Player B': player_b,
            'Deck B': rec['deck_b'],
            'Result': result_text,
            'Games': total_games,
            'Video Link': rec['video_link'],
            'match_id': rec['match_id'],
        })

    def _format_tooltip(stats, opponent):
        if stats['matches'] == 0:
            return ''
        decisions = stats['wins'] + stats['losses']
        match_win_rate = f"{(stats['wins'] / decisions * 100):.1f}%" if decisions > 0 else '-'
        game_win_rate = f"{(stats['game_wins'] / stats['games'] * 100):.1f}%" if stats['games'] > 0 else '-'
        return (
            f"Opponent: {opponent}\n"
            f"Matches Played: {stats['matches']}\n"
            f"Wins: {stats['wins']}\n"
            f"Losses: {stats['losses']}\n"
            f"Draws: {stats['draws']}\n"
            f"Match Win Rate: {match_win_rate}\n"
            f"Game Win Rate: {game_win_rate}\n"
            f"Total Games: {stats['games']}\n"
            f"Last Match: {stats['last_date'] or '-'}"
        )

    for row_player in players:
        for col_player in players:
            if row_player == col_player:
                continue
            stats = row_stats[(row_player, col_player)]
            if stats['matches'] == 0:
                matrix_df.loc[row_player, col_player] = ''
                tooltip_df.loc[row_player, col_player] = ''
                continue
            matrix_df.loc[row_player, col_player] = f"{stats['wins']}-{stats['losses']}-{stats['draws']}"
            tooltip_df.loc[row_player, col_player] = _format_tooltip(stats, col_player)

    def _color_cell(value):
        if not value:
            return 'background-color: #e0e0e0;'
        wins, losses, draws = [int(x) for x in value.split('-')]
        if wins + losses == 0:
            return 'background-color: #d0d0d0;'
        score = (wins - losses) / (wins + losses)
        if score > 0:
            green = 220
            red = int(255 * (1 - score))
        elif score < 0:
            red = 220
            green = int(255 * (1 + score))
        else:
            return 'background-color: #b8b8b8;'
        return f'background-color: rgb({red},{green},0);'

    def _apply_colors(df):
        return df.map(_color_cell)

    summary = {
        'closest': None,
        'biggest_nemesis': None,
    }

    if pair_stats:
        closest = min(
            (pair for pair in pair_stats.items() if pair[1]['matches'] > 0),
            key=lambda pair: abs(pair[1]['wins_a'] - pair[1]['wins_b']),
            default=None,
        )
        if closest is not None:
            diff = abs(closest[1]['wins_a'] - closest[1]['wins_b'])
            summary['closest'] = {
                'pair': f"{closest[0][0]} vs {closest[0][1]}",
                'difference': diff,
                'matches': closest[1]['matches'],
            }

        nemesis_candidates = []
        for (player, opponent), stats in row_stats.items():
            decisions = stats['wins'] + stats['losses']
            if decisions == 0:
                continue
            win_rate = stats['wins'] / decisions
            nemesis_candidates.append((win_rate, player, opponent, decisions))
        if nemesis_candidates:
            worst = min(nemesis_candidates, key=lambda item: (item[0], -item[3]))
            summary['biggest_nemesis'] = {
                'pair': f"{worst[1]} vs {worst[2]}",
                'rate': worst[0],
                'matches': worst[3],
            }

    details_df = pd.DataFrame(details).sort_values(by=['Date', 'League', 'Round'], ascending=[False, True, True])

    return matrix_df, tooltip_df, summary, details_df


st.set_page_config(page_title="League Analytics", layout="wide")
require_auth()
client = get_client()


leagues = client.list_leagues()
if not leagues:
    st.info("No leagues found. Please create a league in League Management.")
    st.stop()

league_options = sorted(leagues, key=lambda l: l.nr, reverse=True)

default_leagues = [
    league for league in league_options
    if 'monaco' in (getattr(league, 'league_name', '') or '').lower()
]
if not default_leagues:
    default_leagues = league_options

all_matches = client.list_matches()
all_users = client.list_users()
user_map = {u.id: u.username for u in all_users}
all_decks = client.list_decks()
deck_lookup = {d.id: d for d in all_decks}

monaco_league_ids = {
    league.id
    for league in league_options
    if 'monaco' in (getattr(league, 'league_name', '') or '').lower()
}
monaco_leagues = [league for league in league_options if league.id in monaco_league_ids]
all_round_map = {}
all_round_to_league_id = {}
all_league_membership_deck = {}
for league in league_options:
    if league.id not in monaco_league_ids:
        continue

    rounds = client.list_rounds(league.id)
    for round_obj in rounds:
        all_round_map[round_obj.id] = round_obj
        all_round_to_league_id[round_obj.id] = league.id

    memberships = client.list_league_players(league.id)
    all_league_membership_deck[league.id] = {
        membership.user_id: (
            deck_lookup.get(getattr(membership, 'deck_id', None)).deck_name
            if deck_lookup.get(getattr(membership, 'deck_id', None))
            else "No Deck"
        )
        for membership in memberships
    }
 
h2h_match_records = []
for match in all_matches:
    summary = compute_match_summary(match)
    if summary['total_games_played'] == 0:
        continue

    league_id = all_round_to_league_id.get(match.round_id)
    if league_id not in monaco_league_ids:
        continue
    league = next((l for l in league_options if l.id == league_id), None)
    round_info = all_round_map.get(match.round_id)
    if not league or not round_info:
        continue

    player_a = user_map.get(match.player_a, f"Spieler {match.player_a}")
    player_b = user_map.get(match.player_b, f"Spieler {match.player_b}")
    deck_a = all_league_membership_deck.get(league_id, {}).get(match.player_a, "No Deck")
    deck_b = all_league_membership_deck.get(league_id, {}).get(match.player_b, "No Deck")

    h2h_match_records.append((
        league.league_name or f"League {league.nr}",
        round_info.nr,
        getattr(match, 'match_type', 'Round'),
        round_info.start_date or '',
        player_a,
        deck_a,
        player_b,
        deck_b,
        summary['match_result'],
        summary['total_games_played'],
        getattr(match, 'video_link', None),
        match.id,
        summary['player_a_game_wins'],
        summary['player_b_game_wins'],
        league.id,
        match.player_a,
        match.player_b,
    ))


st.markdown("## Career Timeline")

timeline_default_leagues = [league for league in default_leagues if league.id in monaco_league_ids]
if not timeline_default_leagues:
    timeline_default_leagues = monaco_leagues

timeline_selected_leagues = st.multiselect(
    "Select leagues for Career Timeline:",
    options=monaco_leagues,
    default=timeline_default_leagues,
    format_func=lambda l: f"{l.league_name or 'League'} ({l.nr})",
    key="league_analytics_timeline_selected_leagues",
)
timeline_selected_league_ids = {league.id for league in timeline_selected_leagues}

match_events = []
for match in all_matches:
    summary = compute_match_summary(match)
    if summary['total_games_played'] == 0:
        continue

    league_id = all_round_to_league_id.get(match.round_id)
    if league_id not in timeline_selected_league_ids:
        continue
    league = next((l for l in monaco_leagues if l.id == league_id), None)
    round_info = all_round_map.get(match.round_id)
    if not league or not round_info:
        continue

    for player_id, opponent_id, own_label in [
        (match.player_a, match.player_b, 'A'),
        (match.player_b, match.player_a, 'B'),
    ]:
        if own_label == 'A':
            outcome_code = summary['match_result']
            own_games = summary['player_a_game_wins']
            opp_games = summary['player_b_game_wins']
        else:
            outcome_code = 'A' if summary['match_result'] == 'B' else ('B' if summary['match_result'] == 'A' else 'D')
            own_games = summary['player_b_game_wins']
            opp_games = summary['player_a_game_wins']

        if outcome_code == 'A':
            outcome = 'W'
            color = '#2ecc71'
            result_label = 'Win'
        elif outcome_code == 'B':
            outcome = 'L'
            color = '#e74c3c'
            result_label = 'Loss'
        else:
            outcome = 'D'
            color = '#f1c40f'
            result_label = 'Draw'

        player_name = user_map.get(player_id, f"Spieler {player_id}")
        opponent_name = user_map.get(opponent_id, f"Spieler {opponent_id}")
        player_deck = all_league_membership_deck.get(league_id, {}).get(player_id, "No Deck")
        opponent_deck = all_league_membership_deck.get(league_id, {}).get(opponent_id, "No Deck")

        match_events.append({
            'player_id': player_id,
            'player_name': player_name,
            'opponent': opponent_name,
            'season': league.league_name or f"League {league.nr}",
            'season_id': league.id,
            'season_number': league.nr,
            'round_number': round_info.nr,
            'match_type': getattr(match, 'match_type', 'Round'),
            'own_deck': player_deck,
            'opponent_deck': opponent_deck,
            'result': result_label,
            'score': f"{own_games}:{opp_games}",
            'outcome': outcome,
            'color': color,
            'date': round_info.start_date or '',
            'match_id': match.id,
        })

match_type_order = {
    'Round': 0,
    'QuarterFinal': 1,
    'SemiFinal': 2,
    'Final': 3,
    'MatchFor3rd': 4,
}

player_timelines = defaultdict(list)

def _timeline_sort_key(item):
    return (
        item['season_number'] if item.get('season_number') is not None else 0,
        pd.to_datetime(item['date'], errors='coerce') if item['date'] else pd.Timestamp.min,
        item['round_number'] if item.get('round_number') is not None else 0,
        match_type_order.get(item.get('match_type', 'Round'), 0),
        item['match_id'],
    )

for event in sorted(match_events, key=_timeline_sort_key):
    player_timelines[event['player_id']].append(event)

if not player_timelines:
    st.info('No timeline data available for the selected leagues.')
else:
    player_ranking = []
    for player_id, events in player_timelines.items():
        total_matches = len(events)
        wins = sum(1 for e in events if e['outcome'] == 'W')
        winrate = wins / total_matches if total_matches > 0 else 0
        player_ranking.append((player_id, winrate, total_matches, events))

    player_ranking.sort(key=lambda item: (-item[1], -item[2], item[3][0]['player_name']))

    timeline_html = '<div class="timeline-board">'
    for player_id, winrate, total_matches, events in player_ranking:
        summary_total = total_matches
        wins = sum(1 for e in events if e['outcome'] == 'W')
        draws = sum(1 for e in events if e['outcome'] == 'D')
        losses = sum(1 for e in events if e['outcome'] == 'L')
        win_rate = f"{(wins / summary_total * 100):.1f}%" if summary_total else '0.0%'
        recent_outcomes = [e['outcome'] for e in events[-8:]]
        current_series = '-'.join(recent_outcomes)
        longest_win = 0
        current_win = 0
        for e in events:
            if e['outcome'] == 'W':
                current_win += 1
                longest_win = max(longest_win, current_win)
            else:
                current_win = 0
        record = f"{wins}-{draws}-{losses}"
        header_html = (
            f"<div class=\"player-row-header\"><strong>{html_mod.escape(events[0]['player_name'])}</strong> | "
            f"Win Rate: {win_rate} | Current Streak: {html_mod.escape(current_series)} | "
            f"Longest Win Streak: {longest_win} | Record: {record}</div>"
        )
        timeline_html += f'<div class="player-row">{header_html}<div class="player-timeline">'
        previous_season = None
        for event in events:
            if previous_season is not None and event['season_id'] != previous_season:
                timeline_html += '<div class="season-separator" title="New Season"></div>'
            tooltip = (
                f"Opponent: {event['opponent']}\n"
                f"Season: {event['season']}\n"
                f"Round: {event['round_number']}\n"
                f"Own Deck: {event['own_deck']}\n"
                f"Opponent Deck: {event['opponent_deck']}\n"
                f"Result: {event['score']}"
            )
            timeline_html += (
                f'<div class="timeline-square" title="{html_mod.escape(tooltip)}" '
                f'style="background:{event["color"]};"></div>'
            )
            previous_season = event['season_id']
        timeline_html += '</div></div>'
    timeline_html += '</div>'

    style = '''
    <style>
        body {
            font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        .timeline-board { display: flex; flex-direction: column; gap: 18px; }
        .player-row { display: flex; flex-direction: column; gap: 6px; }
        .player-row-header { font-size: 0.95rem; color: #222; font-family: inherit; }
        .player-timeline { display: flex; align-items: center; gap: 4px; overflow-x: auto; padding: 8px 0; }
        .timeline-square { width: 18px; height: 18px; min-width: 18px; border-radius: 3px; border: 1px solid #999; }
        .season-separator { width: 2px; height: 24px; background: #444; margin: 0 6px; }
        .player-timeline::-webkit-scrollbar { height: 8px; }
        .player-timeline::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.2); border-radius: 999px; }
    </style>
    '''
    html(style + timeline_html, height=320 + len(player_timelines) * 42)

st.divider()
st.markdown("## Head-to-Head Analytics")
match_filter = st.selectbox(
    "Select match subset for Head-to-Head Analytics",
    ["All Matches", "Regular Season", "Playoffs Only"],
    key="data_analyzer_h2h_filter",
)

matrix_df, tooltip_df, h2h_summary, details_df = build_head_to_head_matrix(tuple(h2h_match_records), match_filter)

summary_cols = st.columns(2)

if h2h_summary['closest']:
    summary_cols[0].metric(
        "Closest Rivalry",
        h2h_summary['closest']['pair'],
        f"{h2h_summary['closest']['difference']} difference",
    )
else:
    summary_cols[0].metric("Closest Rivalry", "-", "No data")

if h2h_summary['biggest_nemesis']:
    summary_cols[1].metric(
        "Biggest Nemesis",
        h2h_summary['biggest_nemesis']['pair'],
        f"{h2h_summary['biggest_nemesis']['rate']:.1%} win rate",
    )
else:
    summary_cols[1].metric("Biggest Nemesis", "-", "No data")

if matrix_df.empty:
    st.info("No head-to-head data available for the selected matches.")
else:
    def _h2h_color_cell(value):
        if not value:
            return 'background-color: #e0e0e0;'
        wins, losses, draws = [int(x) for x in value.split('-')]
        if wins + losses == 0:
            return 'background-color: #d0d0d0;'
        score = (wins - losses) / (wins + losses)
        if score > 0:
            red = int(255 * (1 - score))
            green = 220
        elif score < 0:
            red = 220
            green = int(255 * (1 + score))
        else:
            return 'background-color: #b8b8b8;'
        return f'background-color: rgb({red},{green},0);'

    def _h2h_styles(df):
        return df.map(_h2h_color_cell)

    matrix_styler = matrix_df.style.apply(_h2h_styles, axis=None)
    matrix_styler = matrix_styler.set_table_styles([
        {
            'selector': 'th, td',
            'props': [
                ('font-family', '"Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'),
                ('text-align', 'center'),
                ('font-size', '0.75rem'),
                ('padding', '4px'),
                ('white-space', 'nowrap'),
                ('line-height', '1.1'),
            ],
        },
        {
            'selector': 'td',
            'props': [
                ('width', '58px'),
                ('height', '58px'),
                ('min-width', '58px'),
                ('max-width', '58px'),
            ],
        },
        {
            'selector': 'th',
            'props': [
                ('min-width', '90px'),
                ('max-width', '120px'),
                ('font-size', '0.75rem'),
                ('padding', '3px 4px'),
            ],
        },
    ]).set_properties(**{
        'text-align': 'center',
        'font-size': '0.75rem',
    })
    if tooltip_df.values.any():
        matrix_styler = matrix_styler.set_tooltips(tooltip_df)
    matrix_html = matrix_styler.to_html()
    matrix_height = min(900, 140 + len(matrix_df.index) * 60)
    scroll_height = matrix_height - 40
    scrollable_matrix_html = f"""
    <style>
        .matrix-scroll {{
            width: 100%;
            height: {scroll_height}px;
            overflow: auto;
            -webkit-overflow-scrolling: touch;
        }}
        table {{
            border-collapse: collapse;
            font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        /* Sticky headers */
        .matrix-scroll table thead th {{
            position: sticky;
            top: 0;
            z-index: 2;
            background: #ffffff;
        }}
        .matrix-scroll table th.row_heading {{
            position: sticky;
            left: 0;
            z-index: 3;
            background: #f7f7f7;
        }}
        .matrix-scroll table th.blank {{
            position: sticky;
            left: 0;
            top: 0;
            z-index: 4;
            background: #ffffff;
        }}
    </style>
    <div class="matrix-scroll">
        {matrix_html}
    </div>
    """
    html(scrollable_matrix_html, height=matrix_height)

    with st.expander("Head-to-Head Match Details"):
        players = list(matrix_df.index)
        if len(players) < 2:
            st.info("Not enough players for head-to-head details.")
        else:
            closest_player_a = None
            closest_player_b = None
            if h2h_summary['closest']:
                closest_pair = h2h_summary['closest']['pair'].split(' vs ', 1)
                if len(closest_pair) == 2 and closest_pair[0] in players and closest_pair[1] in players:
                    closest_player_a, closest_player_b = closest_pair

            if 'h2h_detail_player' not in st.session_state or st.session_state.h2h_detail_player not in players:
                st.session_state.h2h_detail_player = closest_player_a or players[0]

            selected_player = st.selectbox("Player", players, key="h2h_detail_player")
            opponent_options = [p for p in players if p != selected_player]
            preferred_opponent = None
            if closest_player_a and closest_player_b:
                if selected_player == closest_player_a and closest_player_b in opponent_options:
                    preferred_opponent = closest_player_b
                elif selected_player == closest_player_b and closest_player_a in opponent_options:
                    preferred_opponent = closest_player_a

            if 'h2h_detail_opponent' not in st.session_state or st.session_state.h2h_detail_opponent not in opponent_options:
                st.session_state.h2h_detail_opponent = preferred_opponent or opponent_options[0]
            selected_opponent = st.selectbox(
                "Opponent",
                opponent_options,
                index=0,
                key="h2h_detail_opponent",
            )
            pair_matches = details_df[
                ((details_df['Player A'] == selected_player) & (details_df['Player B'] == selected_opponent)) |
                ((details_df['Player A'] == selected_opponent) & (details_df['Player B'] == selected_player))
            ]
            if pair_matches.empty:
                st.info("No historical matches found for this rivalry.")
            else:
                st.dataframe(
                    pair_matches[
                        [
                            'League',
                            'Round',
                            'Match Type',
                            'Date',
                            'Player A',
                            'Deck A',
                            'Player B',
                            'Deck B',
                            'Result',
                            'Games',
                            'Video Link',
                        ]
                    ],
                    use_container_width=True,
                    column_config={
                        'Video Link': st.column_config.LinkColumn('Video Link', display_text='🔗 Open'),
                    },
                )

st.divider()
st.markdown("## Hall of Fame")

def _parse_date(date_str):
    dt = pd.to_datetime(date_str, errors='coerce')
    return dt if not pd.isna(dt) else None

hall_rows = []
completed_monaco_leagues = [
    league for league in monaco_leagues
    if getattr(league, 'playoffs_closed', False) or getattr(league, 'nr', None) == 1
]

for league in sorted(completed_monaco_leagues, key=lambda l: _parse_date(getattr(l, 'end_date', None)) or pd.Timestamp.min, reverse=True):
    league_rounds = client.list_rounds(league.id)
    league_round_map = {r.id: r for r in league_rounds}
    league_round_ids = set(league_round_map.keys())

    league_matches = [
        m for m in all_matches
        if getattr(m, 'round_id', None) in league_round_ids
    ]

    winner_player_id = None
    if league_matches:
        final_matches = [
            m for m in league_matches
            if getattr(m, 'match_type', 'Round') == 'Final'
        ]
        if final_matches:
            final_match = sorted(
                final_matches,
                key=lambda m: (
                    league_round_map.get(m.round_id).nr if league_round_map.get(m.round_id) else 0,
                    m.id,
                ),
            )[-1]
            final_summary = compute_match_summary(final_match)
            if final_summary['match_result'] == 'A':
                winner_player_id = final_match.player_a
            elif final_summary['match_result'] == 'B':
                winner_player_id = final_match.player_b
        else:
            league_player_ids = {m.user_id for m in client.list_league_players(league.id)}
            league_players = [u for u in all_users if u.id in league_player_ids]
            round_matches = [
                m for m in league_matches
                if getattr(m, 'match_type', 'Round') == 'Round'
            ]
            standings = compute_standings(league_players, round_matches)
            if standings:
                winner_player_id = standings[0]['player_id']

    if winner_player_id:
        winner_name = user_map.get(winner_player_id, f"Spieler {winner_player_id}")
        deck_name = all_league_membership_deck.get(league.id, {}).get(winner_player_id, "No Deck")
        hall_rows.append({
            'League': league.league_name or f"League {league.nr}",
            'Player': winner_name,
            'Deck': deck_name,
            'End Date': _parse_date(getattr(league, 'end_date', None)),
        })

hall_df = pd.DataFrame(hall_rows)
if hall_df.empty:
    st.info("No Hall of Fame data found for Monaco leagues.")
else:
    hall_df = hall_df.sort_values(by=['End Date'], ascending=False).drop(columns=['End Date'])
    st.dataframe(hall_df, use_container_width=True)
