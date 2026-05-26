from models import Player, Game, Match
from utils import compute_standings, seed_playoff


def make_player(pid, name):
    return Player(id=pid, player_name=name)


def test_compute_standings_simple():
    p1 = make_player('p1', 'Alice')
    p2 = make_player('p2', 'Bob')
    # Alice beats Bob 2-0
    m = Match(id='m1', player_a='p1', player_b='p2', games=[Game(1, 'A'), Game(2, 'A')])
    table = compute_standings([p1, p2], [m])
    # Alice should have 3 points, Bob 0
    alice = next(r for r in table if r['player_id'] == 'p1')
    bob = next(r for r in table if r['player_id'] == 'p2')
    assert alice['points'] == 3
    assert bob['points'] == 0
    assert alice['game_wins'] == 2
    assert bob['game_losses'] == 2


def test_seed_playoff_even_and_odd():
    # create 5 dummy players sorted by descending strength
    players = [{'player_name': f'P{i}'} for i in range(5, 0, -1)]
    res_even = seed_playoff(players, 4)
    assert isinstance(res_even, dict)
    assert 'pairs' in res_even
    assert len(res_even['pairs']) == 2

    res_odd = seed_playoff(players, 5)
    assert isinstance(res_odd, dict)
    assert 'bye' in res_odd and res_odd['bye'] is not None
    assert len(res_odd['pairs']) == 2
