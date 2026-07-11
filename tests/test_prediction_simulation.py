import numpy as np

from prediction.simulation import build_simulation_base, run_monte_carlo
from prediction.types import CompletedMatchSnapshot


def test_simulation_without_remaining_matches_is_deterministic():
    completed = [
        CompletedMatchSnapshot(
            match_id="m1",
            round_id="r1",
            round_nr=1,
            round_start_date="2026-01-01",
            player_a_id="a",
            player_a_name="A",
            player_a_deck="DeckA",
            player_b_id="b",
            player_b_name="B",
            player_b_deck="DeckB",
            match_type="Round",
            result="A",
            points_a=3,
            points_b=0,
            game_wins_a=2,
            game_wins_b=1,
            total_games=3,
        )
    ]
    base = build_simulation_base(["a", "b"], completed, [])
    outcomes, ranks, points, game_wins, total_games = run_monte_carlo(
        simulations=100,
        random_seed=42,
        match_probabilities=np.zeros((0, 3)),
        base=base,
        matches=[],
    )
    assert outcomes.shape == (100, 0)
    assert ranks.shape == (100, 2)
    assert np.all(ranks[:, 0] == 0)
    assert np.all(points[:, 0] == 3)
    assert np.all(points[:, 1] == 0)
    assert np.all(game_wins[:, 0] == 2)
    assert np.all(total_games[:, 0] == 3)
