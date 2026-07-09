import html as html_mod
from collections import defaultdict

import streamlit as st
import pandas as pd

from auth import require_auth
from datastore_client import get_client
from models import compute_match_summary
from streamlit.components.v1 import html
from utils import compute_standings

st.set_page_config(page_title="Data Analyzer", layout="wide")
require_auth()
client = get_client()

leagues = client.list_leagues()
if not leagues:
    st.info("Keine Ligen gefunden. Bitte erstelle eine Liga im League Management.")
    st.stop()

league_options = sorted(leagues, key=lambda l: l.nr, reverse=True)
selected_leagues = st.multiselect(
    "Ligen auswählen, deren Daten in der Tabelle erscheinen sollen:",
    options=league_options,
    default=league_options,
    format_func=lambda l: f"{l.league_name or 'League'} ({l.nr})"
)

if not selected_leagues:
    st.warning("Bitte wähle mindestens eine Liga aus.")
    st.stop()

st.title("Data Analyzer")
st.write("Hier siehst du alle Daten der ausgewählten Ligen in einer einzigen Tabelle.")

all_matches = client.list_matches()
all_users = client.list_users()
user_map = {u.id: u.username for u in all_users}
all_decks = client.list_decks()
deck_lookup = {d.id: d for d in all_decks}

# Build selected league round and member state once.
selected_round_ids = set()
round_map = {}
round_to_league_id = {}
league_membership_deck = {}
for league in selected_leagues:
    rounds = client.list_rounds(league.id)
    for round_obj in rounds:
        selected_round_ids.add(round_obj.id)
        round_map[round_obj.id] = round_obj
        round_to_league_id[round_obj.id] = league.id

    memberships = client.list_league_players(league.id)
    league_membership_deck[league.id] = {
        membership.user_id: (
            deck_lookup.get(getattr(membership, 'deck_id', None)).deck_name
            if deck_lookup.get(getattr(membership, 'deck_id', None))
            else "No Deck"
        )
        for membership in memberships
    }

selected_matches = [m for m in all_matches if getattr(m, 'round_id', None) in selected_round_ids]

rows = []
for match in selected_matches:
    league_id = round_to_league_id.get(match.round_id)
    league = next((l for l in selected_leagues if l.id == league_id), None)
    if not league:
        continue

    summary = compute_match_summary(match)
    player_a = user_map.get(match.player_a, f"Spieler {match.player_a}")
    player_b = user_map.get(match.player_b, f"Spieler {match.player_b}")
    deck_a = league_membership_deck.get(league_id, {}).get(match.player_a)
    deck_b = league_membership_deck.get(league_id, {}).get(match.player_b)
    round_info = round_map.get(match.round_id)

    if summary['match_result'] == 'A':
        result = f"{player_a} gewinnt"
    elif summary['match_result'] == 'B':
        result = f"{player_b} gewinnt"
    else:
        result = "Unentschieden"

    rows.append(
        {
            'League Name': league.league_name or f"League {league.nr}",
            'League Number': league.nr,
            'League ID': league.id,
            'Round Number': round_info.nr if round_info else None,
            'Round Start': round_info.start_date if round_info else None,
            'Round End': round_info.end_date if round_info else None,
            'Match ID': match.id,
            'Match Type': getattr(match, 'match_type', 'Round'),
            'Player A': player_a,
            'Deck A': deck_a,
            'Player B': player_b,
            'Deck B': deck_b,
            'Starting Player': user_map.get(match.starting_player) if match.starting_player else None,
            'Match Result': result,
            'Points A': summary['points_a'],
            'Points B': summary['points_b'],
            'Total Games': summary['total_games_played'],
            'Video Link': getattr(match, 'video_link', None),
        }
    )

league_df = pd.DataFrame(rows)
if league_df.empty:
    st.info("Für die ausgewählten Ligen wurden keine Matchdaten gefunden.")
else:
    league_df = league_df.sort_values(by=['League Number', 'Round Number', 'Match ID'], ascending=[False, True, True])
    visible_columns = [
        'League Name',
        'League Number',
        'Round Number',
        'Match Type',
        'Player A',
        'Deck A',
        'Player B',
        'Deck B',
        'Starting Player',
        'Match Result',
        'Points A',
        'Points B',
        'Total Games',
        'Video Link',
    ]
    st.dataframe(league_df[visible_columns], use_container_width=True)

    st.markdown("## Meta Stats")

    deck_stats = {}
    deck_leagues = defaultdict(set)
    for match in selected_matches:
        summary = compute_match_summary(match)
        if summary['total_games_played'] == 0:
            continue

        league_id = round_to_league_id.get(match.round_id)
        deck_map = league_membership_deck.get(league_id, {})
        deck_a = deck_map.get(match.player_a, "No Deck")
        deck_b = deck_map.get(match.player_b, "No Deck")

        for deck_name in [deck_a, deck_b]:
            if deck_name not in deck_stats:
                deck_stats[deck_name] = {'Deck': deck_name, 'Matches': 0, 'Wins': 0, 'Draws': 0}
            if league_id:
                deck_leagues[deck_name].add(league_id)

        deck_stats[deck_a]['Matches'] += 1
        deck_stats[deck_b]['Matches'] += 1

        if summary['match_result'] == 'D':
            deck_stats[deck_a]['Draws'] += 1
            deck_stats[deck_b]['Draws'] += 1
        elif summary['match_result'] == 'A':
            deck_stats[deck_a]['Wins'] += 1
        elif summary['match_result'] == 'B':
            deck_stats[deck_b]['Wins'] += 1

    deck_df = pd.DataFrame(deck_stats.values())
    if deck_df.empty:
        st.info("Keine Deckdaten für die ausgewählten Ligen gefunden.")
    else:
        deck_df['Leagues'] = deck_df['Deck'].map(lambda name: len(deck_leagues.get(name, set())))
        deck_df['WinRateValue'] = deck_df.apply(
            lambda row: (row['Wins'] / row['Matches']) if row['Matches'] > 0 else 0,
            axis=1,
        )
        deck_df['Win Rate'] = deck_df.apply(
            lambda row: f"{(row['WinRateValue'] * 100):.1f}%" if row['Matches'] > 0 else "-",
            axis=1,
        )
        deck_df['WinRateInclDrawValue'] = deck_df.apply(
            lambda row: ((row['Wins'] + 0.5 * row['Draws']) / row['Matches']) if row['Matches'] > 0 else 0,
            axis=1,
        )
        deck_df['Winrate (incl Draw)'] = deck_df.apply(
            lambda row: f"{(row['WinRateInclDrawValue'] * 100):.1f}%" if row['Matches'] > 0 else "-",
            axis=1,
        )
        deck_df = deck_df.sort_values(by=['WinRateInclDrawValue', 'WinRateValue', 'Wins'], ascending=[False, False, False]).reset_index(drop=True)
        st.dataframe(deck_df[['Deck', 'Wins', 'Draws', 'Leagues', 'Win Rate', 'Winrate (incl Draw)']], use_container_width=True)

    st.markdown("## Career Timeline")

    match_events = []
    for match in selected_matches:
        summary = compute_match_summary(match)
        if summary['total_games_played'] == 0:
            continue

        league_id = round_to_league_id.get(match.round_id)
        league = next((l for l in selected_leagues if l.id == league_id), None)
        round_info = round_map.get(match.round_id)
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
                result_label = 'Unentschieden'

            player_name = user_map.get(player_id, f"Spieler {player_id}")
            opponent_name = user_map.get(opponent_id, f"Spieler {opponent_id}")
            player_deck = league_membership_deck.get(league_id, {}).get(player_id, "No Deck")
            opponent_deck = league_membership_deck.get(league_id, {}).get(opponent_id, "No Deck")

            match_events.append(
                {
                    'player_id': player_id,
                    'player_name': player_name,
                    'opponent': opponent_name,
                    'season': league.league_name or f"League {league.nr}",
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
                }
            )

    match_type_order = {
        'Round': 0,
        'QuarterFinal': 1,
        'SemiFinal': 2,
        'Final': 3,
        'MatchFor3rd': 4,
    }

    player_timelines = defaultdict(list)
    for event in sorted(
        match_events,
        key=lambda item: (
            pd.to_datetime(item['date'], errors='coerce') if item['date'] else pd.Timestamp.min,
            item['season_number'],
            item['round_number'],
            match_type_order.get(item.get('match_type', 'Round'), 0),
            item['match_id'],
        ),
        reverse=False,
    ):
        player_timelines[event['player_id']].append(event)

    if not player_timelines:
        st.info('Keine Timeline-Daten für die ausgewählten Ligen vorhanden.')
    else:
        timeline_html = '<div class="timeline-board">'
        for player_id, events in player_timelines.items():
            summary_total = len(events)
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
                f"Win Rate: {win_rate} | Aktuelle Serie: {html_mod.escape(current_series)} | "
                f"Längste Siegesserie: {longest_win} | Gesamtbilanz: {record}</div>"
            )
            timeline_html += f'<div class="player-row">{header_html}<div class="player-timeline">'
            previous_season = None
            for event in events:
                if previous_season is not None and event['season'] != previous_season:
                    timeline_html += '<div class="season-separator" title="Neue Saison"></div>'
                tooltip = (
                    f"Gegner: {event['opponent']}\n"
                    f"Saison: {event['season']}\n"
                    f"Runde: {event['round_number']}\n"
                    f"Eigenes Deck: {event['own_deck']}\n"
                    f"Gegnerdeck: {event['opponent_deck']}\n"
                    f"Ergebnis: {event['score']}"
                )
                timeline_html += (
                    f'<div class="timeline-square" title="{html_mod.escape(tooltip)}" '
                    f'style="background:{event["color"]};"></div>'
                )
                previous_season = event['season']
            timeline_html += '</div></div>'
        timeline_html += '</div>'

        style = '''
        <style>
            .timeline-board { display: flex; flex-direction: column; gap: 18px; }
            .player-row { display: flex; flex-direction: column; gap: 6px; }
            .player-row-header { font-size: 0.95rem; color: #222; }
            .player-timeline { display: flex; align-items: center; gap: 4px; overflow-x: auto; padding: 8px 0; }
            .timeline-square { width: 18px; height: 18px; min-width: 18px; border-radius: 3px; border: 1px solid #999; }
            .season-separator { width: 2px; height: 24px; background: #444; margin: 0 6px; }
            .player-timeline::-webkit-scrollbar { height: 8px; }
            .player-timeline::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.2); border-radius: 999px; }
        </style>
        '''
        html(style + timeline_html, height=320 + len(player_timelines) * 42)

    st.markdown("## Hall of Fame")

    def _parse_date(date_str):
        dt = pd.to_datetime(date_str, errors='coerce')
        return dt if not pd.isna(dt) else None

    today = pd.Timestamp.today().normalize()

    def _is_current_league(league):
        if not getattr(league, 'league_name', '') or 'monaco' not in league.league_name.lower():
            return False
        start = _parse_date(getattr(league, 'start_date', None))
        end = _parse_date(getattr(league, 'end_date', None))
        if start is None or end is None:
            return False
        return start <= today <= end

    hall_rows = []
    for league in sorted(leagues, key=lambda l: _parse_date(getattr(l, 'end_date', None)) or pd.Timestamp.min, reverse=True):
        if not getattr(league, 'league_name', '') or 'monaco' not in league.league_name.lower():
            continue
        if _is_current_league(league):
            continue

        league_rounds = client.list_rounds(league.id)
        league_round_map = {r.id: r for r in league_rounds}
        league_round_ids = set(league_round_map.keys())

        league_matches = [
            m for m in all_matches if getattr(m, 'round_id', None) in league_round_ids
        ]

        winner_player_id = None
        if league_matches:
            final_matches = [
                m for m in league_matches if getattr(m, 'match_type', 'Round') == 'Final'
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
                league_players = [
                    u for u in all_users if u.id in league_player_ids
                ]
                round_matches = [
                    m for m in league_matches if getattr(m, 'match_type', 'Round') == 'Round'
                ]
                standings = compute_standings(league_players, round_matches)
                if standings:
                    winner_player_id = standings[0]['player_id']

        if winner_player_id:
            winner_name = user_map.get(winner_player_id, f"Spieler {winner_player_id}")
            league_memberships = client.list_league_players(league.id)
            deck_name = None
            for membership in league_memberships:
                if membership.user_id == winner_player_id:
                    deck = deck_lookup.get(getattr(membership, 'deck_id', None))
                    deck_name = deck.deck_name if deck else "No Deck"
                    break
            hall_rows.append(
                {
                    'League': league.league_name or f"League {league.nr}",
                    'Player': winner_name,
                    'Deck': deck_name,
                    'End Date': _parse_date(getattr(league, 'end_date', None)),
                }
            )

    hall_df = pd.DataFrame(hall_rows)
    if hall_df.empty:
        st.info("Keine Hall of Fame-Daten gefunden.")
    else:
        hall_df = hall_df.sort_values(by=['End Date'], ascending=False).drop(columns=['End Date'])
        st.dataframe(hall_df, use_container_width=True)
