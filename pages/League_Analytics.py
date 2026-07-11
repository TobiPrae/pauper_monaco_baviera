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
        return df.applymap(_color_cell)

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


@st.cache_data
def build_deck_matchup_matrix(matches):
    included_match_types = {'Round', 'SemiFinal', 'Final', 'MatchFor3rd'}
    normalized_matches = []
    for rec in matches:
        if len(rec) < 17:
            continue
        match_type = rec[2]
        total_games = rec[9]
        if match_type not in included_match_types or total_games == 0:
            continue
        normalized_matches.append({
            'league_name': rec[0],
            'round_number': rec[1],
            'match_type': rec[2],
            'date': rec[3],
            'player_a_name': rec[4],
            'deck_a': rec[5] or 'No Deck',
            'player_b_name': rec[6],
            'deck_b': rec[7] or 'No Deck',
            'match_result': rec[8],
            'total_games': rec[9],
            'video_link': rec[10],
            'match_id': rec[11],
            'player_a_game_wins': rec[12],
            'player_b_game_wins': rec[13],
            'league_id': rec[14],
            'player_a_id': rec[15],
            'player_b_id': rec[16],
        })

    if not normalized_matches:
        empty_df = pd.DataFrame()
        return empty_df, {}, empty_df, {'rankings_df': empty_df}

    ordered_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'draws': 0, 'matches': 0, 'games': 0, 'game_wins': 0})
    pair_stats = defaultdict(lambda: {'wins_a': 0, 'wins_b': 0, 'draws': 0, 'matches': 0})
    deck_totals = defaultdict(lambda: {'wins': 0, 'losses': 0, 'draws': 0, 'matches': 0, 'games': 0, 'game_wins': 0})
    details = []

    player_names = {}
    player_decks_by_league = {}
    round_player_stats = defaultdict(lambda: {'points': 0, 'game_wins': 0, 'total_games': 0})
    finals_counts = defaultdict(int)
    title_counts = defaultdict(int)
    final_match_by_league = {}

    for match in normalized_matches:
        deck_a = match['deck_a']
        deck_b = match['deck_b']
        result = match['match_result']
        games = match['total_games']
        a_game_wins = match['player_a_game_wins']
        b_game_wins = match['player_b_game_wins']
        league_id = match['league_id']
        player_a_id = match['player_a_id']
        player_b_id = match['player_b_id']
        player_names[player_a_id] = match['player_a_name']
        player_names[player_b_id] = match['player_b_name']
        player_decks_by_league[(league_id, player_a_id)] = deck_a
        player_decks_by_league[(league_id, player_b_id)] = deck_b

        ordered_stats[(deck_a, deck_b)]['matches'] += 1
        ordered_stats[(deck_a, deck_b)]['games'] += games
        ordered_stats[(deck_a, deck_b)]['game_wins'] += a_game_wins
        ordered_stats[(deck_b, deck_a)]['matches'] += 1
        ordered_stats[(deck_b, deck_a)]['games'] += games
        ordered_stats[(deck_b, deck_a)]['game_wins'] += b_game_wins

        deck_totals[deck_a]['matches'] += 1
        deck_totals[deck_b]['matches'] += 1
        deck_totals[deck_a]['games'] += games
        deck_totals[deck_b]['games'] += games
        deck_totals[deck_a]['game_wins'] += a_game_wins
        deck_totals[deck_b]['game_wins'] += b_game_wins

        pair_key = tuple(sorted([deck_a, deck_b]))
        pair_stats[pair_key]['matches'] += 1

        if result == 'A':
            ordered_stats[(deck_a, deck_b)]['wins'] += 1
            ordered_stats[(deck_b, deck_a)]['losses'] += 1
            deck_totals[deck_a]['wins'] += 1
            deck_totals[deck_b]['losses'] += 1
            if pair_key[0] == deck_a:
                pair_stats[pair_key]['wins_a'] += 1
            else:
                pair_stats[pair_key]['wins_b'] += 1
            winner = match['player_a_name']
        elif result == 'B':
            ordered_stats[(deck_a, deck_b)]['losses'] += 1
            ordered_stats[(deck_b, deck_a)]['wins'] += 1
            deck_totals[deck_a]['losses'] += 1
            deck_totals[deck_b]['wins'] += 1
            if pair_key[0] == deck_b:
                pair_stats[pair_key]['wins_a'] += 1
            else:
                pair_stats[pair_key]['wins_b'] += 1
            winner = match['player_b_name']
        else:
            ordered_stats[(deck_a, deck_b)]['draws'] += 1
            ordered_stats[(deck_b, deck_a)]['draws'] += 1
            deck_totals[deck_a]['draws'] += 1
            deck_totals[deck_b]['draws'] += 1
            pair_stats[pair_key]['draws'] += 1
            winner = 'Draw'

        if match['match_type'] == 'Round':
            if result == 'A':
                round_player_stats[(league_id, player_a_id)]['points'] += 3
            elif result == 'B':
                round_player_stats[(league_id, player_b_id)]['points'] += 3
            else:
                round_player_stats[(league_id, player_a_id)]['points'] += 1
                round_player_stats[(league_id, player_b_id)]['points'] += 1

            round_player_stats[(league_id, player_a_id)]['game_wins'] += a_game_wins
            round_player_stats[(league_id, player_b_id)]['game_wins'] += b_game_wins
            round_player_stats[(league_id, player_a_id)]['total_games'] += games
            round_player_stats[(league_id, player_b_id)]['total_games'] += games

        if match['match_type'] == 'Final':
            finals_counts[deck_a] += 1
            finals_counts[deck_b] += 1
            current_final = final_match_by_league.get(league_id)
            current_key = (match['round_number'] or 0, str(match['match_id']))
            existing_key = (current_final['round_number'] or 0, str(current_final['match_id'])) if current_final else None
            if existing_key is None or current_key >= existing_key:
                final_match_by_league[league_id] = match

        details.append({
            'League': match['league_name'],
            'Round': match['round_number'],
            'Date': match['date'],
            'Player A': match['player_a_name'],
            'Deck A': deck_a,
            'Player B': match['player_b_name'],
            'Deck B': deck_b,
            'Result': 'Draw' if result == 'D' else ('Player A wins' if result == 'A' else 'Player B wins'),
            'Games': games,
            'Winner': winner,
            'Video Link': match['video_link'],
        })

    for final_match in final_match_by_league.values():
        if final_match['match_result'] == 'A':
            title_counts[final_match['deck_a']] += 1
        elif final_match['match_result'] == 'B':
            title_counts[final_match['deck_b']] += 1

    placement_by_deck = defaultdict(list)
    round_players_by_league = defaultdict(set)
    for league_id, player_id in round_player_stats:
        round_players_by_league[league_id].add(player_id)
    for league_id, player_ids in round_players_by_league.items():
        standings_rows = []
        for player_id in player_ids:
            stats = round_player_stats[(league_id, player_id)]
            game_win_rate = (stats['game_wins'] / stats['total_games']) if stats['total_games'] > 0 else 0
            standings_rows.append({
                'player_id': player_id,
                'points': stats['points'],
                'points_plus': stats['points'] + game_win_rate,
            })
        standings_rows.sort(key=lambda row: (row['points_plus'], row['points']), reverse=True)
        if league_id not in final_match_by_league and standings_rows:
            winner_deck = player_decks_by_league.get((league_id, standings_rows[0]['player_id']))
            if winner_deck:
                title_counts[winner_deck] += 1
        for index, row in enumerate(standings_rows, start=1):
            deck_name = player_decks_by_league.get((league_id, row['player_id']))
            if deck_name:
                placement_by_deck[deck_name].append(index)

    def _decision_win_rate(stats):
        decisions = stats['wins'] + stats['losses']
        return (stats['wins'] / decisions) if decisions > 0 else None

    def _pair_record(pair_key):
        pair = pair_stats[pair_key]
        return f"{pair_key[0]} vs {pair_key[1]}", pair

    decks = sorted(
        deck_totals.keys(),
        key=lambda deck: (
            -((_decision_win_rate(deck_totals[deck]) or 0)),
            -(deck_totals[deck]['wins'] + 0.5 * deck_totals[deck]['draws']),
            deck,
        ),
    )
    matrix_df = pd.DataFrame('', index=decks, columns=decks)
    for row_deck in decks:
        for col_deck in decks:
            stats = ordered_stats[(row_deck, col_deck)]
            if stats['matches'] > 0:
                matrix_df.loc[row_deck, col_deck] = f"{stats['wins']}-{stats['losses']}-{stats['draws']}"

    summary = {}
    if pair_stats:
        most_played_pair = max(pair_stats.items(), key=lambda item: item[1]['matches'])
        summary['most_played_matchup'] = {'label': f"{most_played_pair[0][0]} vs {most_played_pair[0][1]}", 'matches': most_played_pair[1]['matches']}

        most_balanced_pair = min(
            pair_stats.items(),
            key=lambda item: (abs(item[1]['wins_a'] - item[1]['wins_b']), -item[1]['matches']),
        )
        summary['most_balanced_matchup'] = {'label': f"{most_balanced_pair[0][0]} vs {most_balanced_pair[0][1]}", 'matches': most_balanced_pair[1]['matches']}

        largest_sample_pair = max(pair_stats.items(), key=lambda item: item[1]['matches'])
        summary['largest_sample_size'] = {'label': f"{largest_sample_pair[0][0]} vs {largest_sample_pair[0][1]}", 'matches': largest_sample_pair[1]['matches']}

    ordered_with_decisions = [
        ((row_deck, col_deck), stats, _decision_win_rate(stats))
        for (row_deck, col_deck), stats in ordered_stats.items()
        if row_deck != col_deck and _decision_win_rate(stats) is not None
    ]
    if ordered_with_decisions:
        best = max(ordered_with_decisions, key=lambda item: (item[2], item[1]['matches']))
        worst = min(ordered_with_decisions, key=lambda item: (item[2], -item[1]['matches']))
        summary['highest_winrate_matchup'] = {
            'label': f"{best[0][0]} vs {best[0][1]}",
            'rate': best[2],
            'matches': best[1]['matches'],
        }
        summary['worst_matchup'] = {
            'label': f"{worst[0][0]} vs {worst[0][1]}",
            'rate': worst[2],
            'matches': worst[1]['matches'],
        }

    most_played_deck = max(deck_totals.items(), key=lambda item: item[1]['matches'])
    best_overall_deck = max(deck_totals.items(), key=lambda item: ((_decision_win_rate(item[1]) or 0), item[1]['matches']))
    worst_overall_deck = min(deck_totals.items(), key=lambda item: ((_decision_win_rate(item[1]) if _decision_win_rate(item[1]) is not None else 1), -item[1]['matches']))
    most_successful_deck = max(deck_totals.items(), key=lambda item: (title_counts[item[0]], (_decision_win_rate(item[1]) or 0), item[1]['matches']))

    polarizing_candidates = []
    for pair_key, pair in pair_stats.items():
        decisions = pair['wins_a'] + pair['wins_b']
        if decisions < 5:
            continue
        dominant_rate = max(pair['wins_a'], pair['wins_b']) / decisions if decisions > 0 else 0
        if dominant_rate >= 0.8:
            dominant_deck = pair_key[0] if pair['wins_a'] >= pair['wins_b'] else pair_key[1]
            underdog_deck = pair_key[1] if dominant_deck == pair_key[0] else pair_key[0]
            polarizing_candidates.append((dominant_rate, pair['matches'], f"{dominant_deck} vs {underdog_deck}"))
    most_polarizing = max(polarizing_candidates, default=None)

    best_counter = None
    best_counter_rate = -1
    for (row_deck, col_deck), stats in ordered_stats.items():
        if row_deck == col_deck:
            continue
        rate = _decision_win_rate(stats)
        if rate is None:
            continue
        if rate > best_counter_rate and stats['matches'] >= 3:
            best_counter_rate = rate
            best_counter = f"{row_deck} vs {col_deck}"

    ranking_rows = []
    for deck in decks:
        totals = deck_totals[deck]
        decisions = totals['wins'] + totals['losses']
        overall_win_rate = (totals['wins'] / decisions) if decisions > 0 else 0
        overall_win_rate_incl_draw = ((totals['wins'] + 0.5 * totals['draws']) / totals['matches']) if totals['matches'] > 0 else 0
        opponents = [op for op in decks if op != deck and ordered_stats[(deck, op)]['matches'] > 0]
        best_matchup = '-'
        worst_matchup = '-'
        if opponents:
            best_opponent = max(
                opponents,
                key=lambda op: ((_decision_win_rate(ordered_stats[(deck, op)]) or -1), ordered_stats[(deck, op)]['matches'])
            )
            worst_opponent = min(
                opponents,
                key=lambda op: ((_decision_win_rate(ordered_stats[(deck, op)]) if _decision_win_rate(ordered_stats[(deck, op)]) is not None else 1), -ordered_stats[(deck, op)]['matches'])
            )
            best_matchup = f"{best_opponent} ({(_decision_win_rate(ordered_stats[(deck, best_opponent)]) or 0):.1%})"
            worst_matchup = f"{worst_opponent} ({(_decision_win_rate(ordered_stats[(deck, worst_opponent)]) or 0):.1%})"
        ranking_rows.append({
            'Deck': deck,
            'Overall Win Rate': round(overall_win_rate * 100, 2),
            'Overall Win Rate (incl Draw)': round(overall_win_rate_incl_draw * 100, 2),
            'Matches': totals['matches'],
            'Wins': totals['wins'],
            'Losses': totals['losses'],
            'Draws': totals['draws'],
            'Titles': title_counts[deck],
            'Finals': finals_counts[deck],
            'Best Matchup': best_matchup,
            'Worst Matchup': worst_matchup,
        })
    rankings_df = pd.DataFrame(ranking_rows)

    details_df = pd.DataFrame(details).sort_values(by=['Date', 'League', 'Round'], ascending=[False, True, True])
    meta_statistics = {
        'best_overall_deck': f"{best_overall_deck[0]} ({(_decision_win_rate(best_overall_deck[1]) or 0):.1%})",
        'worst_overall_deck': f"{worst_overall_deck[0]} ({(_decision_win_rate(worst_overall_deck[1]) or 0):.1%})",
        'best_counter_deck': best_counter or '-',
        'most_played_deck': f"{most_played_deck[0]} ({most_played_deck[1]['matches']} matches)",
        'most_successful_deck': f"{most_successful_deck[0]} ({title_counts[most_successful_deck[0]]} titles)",
        'most_played_matchup': summary.get('most_played_matchup', {}).get('label', '-'),
        'most_polarizing_matchup': most_polarizing[2] if most_polarizing else '-',
        'rankings_df': rankings_df.sort_values(by=['Overall Win Rate', 'Matches'], ascending=[False, False]),
    }
    return matrix_df, summary, details_df, meta_statistics

st.set_page_config(page_title="League Analytics", layout="wide")
require_auth()
client = get_client()

_img_left, _img_center, _img_right = st.columns([1, 2, 1])
with _img_center:
    st.image("assets/logo_analytics.png", width=630)

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

st.markdown("## Deck vs Deck Analytics")
deck_matrix_df, deck_summary, deck_details_df, deck_meta_stats = build_deck_matchup_matrix(tuple(h2h_match_records))

if deck_matrix_df.empty:
    st.info("No deck-vs-deck data available.")
else:
    most_played = deck_summary.get('most_played_matchup', {'label': '-', 'matches': 0})

    def _deck_cell_color(value):
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

    def _deck_styles(df):
        return df.applymap(_deck_cell_color)

    deck_matrix_styler = deck_matrix_df.style.apply(_deck_styles, axis=None)
    deck_matrix_styler = deck_matrix_styler.set_table_styles([
        {
            'selector': 'th, td',
            'props': [
                ('text-align', 'center'),
                ('font-size', '0.68rem'),
                ('padding', '2px'),
                ('white-space', 'nowrap'),
                ('line-height', '1.1'),
            ],
        },
        {
            'selector': 'td',
            'props': [
                ('width', '36px'),
                ('height', '36px'),
                ('min-width', '36px'),
                ('max-width', '36px'),
                ('min-height', '36px'),
                ('max-height', '36px'),
                ('overflow', 'hidden'),
            ],
        },
        {
            'selector': 'th',
            'props': [
                ('min-width', '72px'),
                ('max-width', '96px'),
                ('font-size', '0.66rem'),
                ('padding', '2px 3px'),
            ],
        },
    ]).set_properties(**{
        'text-align': 'center',
        'font-size': '0.68rem',
    })
    deck_matrix_html = deck_matrix_styler.to_html()
    scrollable_deck_matrix_html = f"""
    <style>
      .deck-matrix-scroll {{
        width: 100%;
        height: 680px;
        overflow: auto;
      }}
      .deck-matrix-scroll table thead th {{
        position: sticky;
        top: 0;
        z-index: 2;
        background: #ffffff;
      }}
      .deck-matrix-scroll table th.row_heading {{
        position: sticky;
        left: 0;
        z-index: 3;
        background: #f7f7f7;
      }}
      .deck-matrix-scroll table th.blank {{
        position: sticky;
        left: 0;
        top: 0;
        z-index: 4;
        background: #ffffff;
      }}
    </style>
    <div class="deck-matrix-scroll">
      {deck_matrix_html}
    </div>
    """
    html(scrollable_deck_matrix_html, height=720)

    with st.expander("Deck Matchup Details"):
        all_decks = list(deck_matrix_df.index)
        default_deck_a = all_decks[0]
        default_deck_b = all_decks[0]
        if most_played['label'] != '-' and ' vs ' in most_played['label']:
            default_deck_a, default_deck_b = most_played['label'].split(' vs ', 1)
            if default_deck_a not in all_decks:
                default_deck_a = all_decks[0]
            if default_deck_b not in all_decks:
                default_deck_b = all_decks[0]

        if 'deck_matchup_detail_deck' not in st.session_state or st.session_state.deck_matchup_detail_deck not in all_decks:
            st.session_state.deck_matchup_detail_deck = default_deck_a

        selected_deck_a = st.selectbox("Deck", all_decks, key="deck_matchup_detail_deck")
        opponent_options = [d for d in all_decks if d != selected_deck_a]
        if default_deck_b not in opponent_options:
            default_deck_b = opponent_options[0]
        if 'deck_matchup_detail_opponent' not in st.session_state or st.session_state.deck_matchup_detail_opponent not in opponent_options:
            st.session_state.deck_matchup_detail_opponent = default_deck_b
        selected_deck_b = st.selectbox(
            "Opponent",
            opponent_options,
            index=0,
            key="deck_matchup_detail_opponent",
        )

        matchup_details = deck_details_df[
            ((deck_details_df['Deck A'] == selected_deck_a) & (deck_details_df['Deck B'] == selected_deck_b)) |
            ((deck_details_df['Deck A'] == selected_deck_b) & (deck_details_df['Deck B'] == selected_deck_a))
        ]
        if matchup_details.empty:
            st.info("No historical matches found for this deck matchup.")
        else:
            st.dataframe(
                matchup_details[
                    [
                        'League',
                        'Round',
                        'Date',
                        'Player A',
                        'Deck A',
                        'Player B',
                        'Deck B',
                        'Result',
                        'Games',
                        'Winner',
                        'Video Link',
                    ]
                ],
                use_container_width=True,
                column_config={
                    'Video Link': st.column_config.LinkColumn('Video Link', display_text='🔗 Open'),
                },
            )

    st.markdown("### Deck Matchup Rankings")
    st.dataframe(deck_meta_stats.get('rankings_df', pd.DataFrame()), use_container_width=True)

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
        return df.applymap(_h2h_color_cell)

    matrix_styler = matrix_df.style.apply(_h2h_styles, axis=None)
    matrix_styler = matrix_styler.set_table_styles([
        {
            'selector': 'th, td',
            'props': [
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
    html(matrix_html, height=matrix_height)

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
