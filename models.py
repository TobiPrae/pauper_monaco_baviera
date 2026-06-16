from dataclasses import dataclass, field
from typing import List, Optional, Dict   


@dataclass
class User:
    id: str
    username: str
    password_hash: str
    is_admin: bool = False
    original_username: str = ""

@dataclass
class Deck:
    id: str
    deck_name: str
    deck_list_link: Optional[str] = None

@dataclass
class Game:
    game_index: int
    winner: Optional[str]  # 'A', 'B', or None

@dataclass
class Match:
    id: str
    player_a: str
    player_b: str
    round_id: int = None
    start_date: str = None
    end_date: str = None
    starting_player: Optional[str] = None
    games: List[Game] = field(default_factory=list)
    went_in_time: bool = False
    match_type: str = "Round" # "Round" or "PlayOffs"
    video_link: Optional[str] = None

@dataclass
class Round:
    id: str
    nr: int
    start_date: str
    end_date: str
    league_id: str

@dataclass
class League:
    id: str
    nr: int
    start_date: str
    end_date: str
    league_name: str = ""
    weeks_rounds: int = 0
    weeks_playoffs: int = 0
    round_robin_closed: bool = False
    playoffs_closed: bool = False
    delete_lock: bool = False

@dataclass
class LeaguePlayer:
    id: str
    league_id: str
    user_id: str
    deck_id: str

def compute_match_summary(match: Match) -> Dict:
    a_game_wins = sum(1 for g in match.games if g.winner == 'A')
    b_game_wins = sum(1 for g in match.games if g.winner == 'B')
    total_games = sum(1 for g in match.games if g.winner in ('A','B'))

    if a_game_wins > b_game_wins:
        result = 'A'
    elif b_game_wins > a_game_wins:
        result = 'B'
    else:
        result = 'D'  # draw

    # Points: win 3, draw 1, loss 0
    if result == 'A':
        points_a, points_b = 3, 0
    elif result == 'B':
        points_a, points_b = 0, 3
    else:
        points_a, points_b = 1, 1

    return {
        'player_a_game_wins': a_game_wins,
        'player_b_game_wins': b_game_wins,
        'total_games_played': total_games,
        'match_result': result,
        'points_a': points_a,
        'points_b': points_b,
    }
