from typing import List, Dict, Tuple
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
        if summ['total_games_played'] == 0:
            continue
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
            'player_name': s['player'].username,
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


def validate_password(password: str, confirm_password: str = None) -> Tuple[bool, str]:
    """Centralized password validation logic."""
    if not password:
        return False, "Password cannot be empty"
    if len(password) < 4:
        return False, "Password must be at least 4 characters long"
    if confirm_password is not None and password != confirm_password:
        return False, "Passwords do not match"
    return True, ""


def display_user_open_matches_warning(client, league_id: str) -> None:
    """
    Check for open matches of the current user in previous rounds and display warnings as toasts.
    Call this function at the top of each page to show warnings.
    
    Args:
        client: The datastore client
        league_id: The ID of the current league
    """
    import streamlit as st
    
    try:
        # Get current user
        current_user = st.session_state.get("user")
        if not current_user:
            return
        
        all_rounds = client.list_rounds(league_id)
        if not all_rounds:
            return
        
        # Find the current round
        from datetime import datetime
        today = datetime.now().date()
        current_round = None
        
        for r in all_rounds:
            try:
                start = datetime.strptime(r.start_date, '%Y-%m-%d').date()
                end = datetime.strptime(r.end_date, '%Y-%m-%d').date()
                if start <= today <= end:
                    current_round = r
                    break
            except (ValueError, TypeError):
                pass
        
        if not current_round:
            return
        
        # Get user mapping for opponent names
        all_users = client.list_users()
        user_map = {u.id: u.username for u in all_users}
        
        # Check for open matches of the current user in previous rounds
        all_matches = client.list_matches()
        previous_rounds = [r for r in all_rounds if r.nr < current_round.nr]
        open_user_matches = []  # List of tuples (week_nr, opponent_name)
        
        for prev_r in previous_rounds:
            prev_matches = [
                m for m in all_matches
                if getattr(m, 'round_id', None) == prev_r.id
                and getattr(m, 'match_type', 'Round') == 'Round'
            ]
            
            # Check if current user has an open match in this previous round
            for m in prev_matches:
                is_player_a = m.player_a == current_user.id
                is_player_b = m.player_b == current_user.id
                
                if (is_player_a or is_player_b):
                    # Check if match is open
                    is_open = (
                        m.starting_player is None
                        and m.games[0].winner is None
                        and m.games[1].winner is None
                        and m.games[2].winner is None
                    )
                    if is_open:
                        # Get opponent name
                        opponent_id = m.player_b if is_player_a else m.player_a
                        opponent_name = user_map.get(opponent_id, "Unknown")
                        open_user_matches.append((prev_r.nr, opponent_name))
                        break  # Only add this round once
        
        # Display warning toast if user has open matches
        if open_user_matches:
            match_list = ", ".join(f"Week {week} against {opponent}" for week, opponent in open_user_matches)
            st.toast(
                f"Please play your Match from {match_list}",
                icon="⚠️"
            )
    
    except Exception as e:
        # Silently fail to avoid breaking page load
        pass
