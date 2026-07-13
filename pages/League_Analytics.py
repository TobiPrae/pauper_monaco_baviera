import html as html_mod
from collections import defaultdict

import streamlit as st
import pandas as pd

from auth import require_auth
from datastore_client import get_client
from models import compute_match_summary
from streamlit.components.v1 import html


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
