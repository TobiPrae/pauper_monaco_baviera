from models import Game, Match, compute_match_summary


def test_compute_match_summary_2_0():
    m = Match(id='m1', player_a='pA', player_b='pB', games=[Game(1, 'A'), Game(2, 'A')])
    s = compute_match_summary(m)
    assert s['player_a_game_wins'] == 2
    assert s['player_b_game_wins'] == 0
    assert s['match_result'] == 'A'
    assert s['points_a'] == 3 and s['points_b'] == 0


def test_compute_match_summary_1_1_draw():
    m = Match(id='m2', player_a='pA', player_b='pB', games=[Game(1, 'A'), Game(2, 'B')])
    s = compute_match_summary(m)
    assert s['player_a_game_wins'] == 1
    assert s['player_b_game_wins'] == 1
    assert s['match_result'] == 'D'
    assert s['points_a'] == 1 and s['points_b'] == 1


def test_compute_match_summary_single_game_win():
    m = Match(id='m3', player_a='pA', player_b='pB', games=[Game(1, 'A')])
    s = compute_match_summary(m)
    assert s['player_a_game_wins'] == 1
    assert s['player_b_game_wins'] == 0
    assert s['match_result'] == 'A'
    assert s['points_a'] == 3 and s['points_b'] == 0
