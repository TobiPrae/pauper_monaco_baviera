from typing import List, Dict
from models import Match


def compute_standings(players: List, matches: List[Match]) -> List[Dict]:
    # Initialize stats
    stats = {p.id: {
        'player': p,
        'points': 0,
        'game_wins': 0,
        'game_losses': 0,
        'total_games': 0,
        'match_wins': 0,
        'match_losses': 0,
        'match_draws': 0,
        'total_matches': 0,
    } for p in players}

    for m in matches:
        from models import compute_match_summary
        summ = compute_match_summary(m)
        a = m.player_a
        b = m.player_b
        stats[a]['points'] += summ['points_a']
        stats[b]['points'] += summ['points_b']
        stats[a]['game_wins'] += summ['player_a_game_wins']
        stats[b]['game_wins'] += summ['player_b_game_wins']
        stats[a]['game_losses'] += summ['player_b_game_wins']
        stats[b]['game_losses'] += summ['player_a_game_wins']
        stats[a]['total_games'] += summ['total_games_played']
        stats[b]['total_games'] += summ['total_games_played']
        stats[a]['total_matches'] += 1
        stats[b]['total_matches'] += 1
        if summ['match_result'] == 'A':
            stats[a]['match_wins'] += 1
            stats[b]['match_losses'] += 1
        elif summ['match_result'] == 'B':
            stats[b]['match_wins'] += 1
            stats[a]['match_losses'] += 1
        else:
            stats[a]['match_draws'] += 1
            stats[b]['match_draws'] += 1

    # Build table list
    table = []
    for pid, s in stats.items():
        gw = s['game_wins']
        tg = s['total_games']
        gw_rate = (gw / tg) if tg > 0 else 0
        primary_metric = s['points'] + gw_rate
        table.append({
            'player_id': pid,
            'player_name': s['player'].player_name,
            'points': s['points'],
            'points_plus': primary_metric,
            'match_wins': s['match_wins'],
            'match_losses': s['match_losses'],
            'match_draws': s['match_draws'],
            'total_matches': s['total_matches'],
            'game_wins': s['game_wins'],
            'game_losses': s['game_losses'],
            'total_games': s['total_games'],
            'game_win_rate': gw_rate,
        })

    # Default sort: points_plus desc
    table.sort(key=lambda r: (r['points_plus'], r['points']), reverse=True)
    return table


def seed_playoff(sorted_players: List[Dict], n: int) -> List[Dict]:
    # Assumes sorted_players is descending by rank (best first)
    selected = sorted_players[:n]
    pairs = []
    bye = None
    # If odd n, give the top seed a bye into next round
    if n % 2 == 1:
        bye = selected[0]
        # seed the remaining players (exclude top seed)
        selected = selected[1:]
        n = len(selected)

    for i in range(n//2):
        top = selected[i]
        bottom = selected[n - 1 - i]
        pairs.append({'seed_a': i+1 + (1 if bye else 0), 'player_a': top, 'seed_b': n - i + (1 if bye else 0), 'player_b': bottom})

    return {'pairs': pairs, 'bye': bye}
