import numpy as np

from prediction.scenario_explorer import build_scenario_report
from prediction.types import (
    FeatureContribution,
    MatchProbability,
    MatchSnapshot,
    PlayerPrediction,
    SimulationArtifacts,
)


def _player(player_id: str, name: str, playoff_probability: float, expected_finish: float) -> PlayerPrediction:
    return PlayerPrediction(
        player_id=player_id,
        player_name=name,
        current_rank=1,
        most_likely_finish=1,
        best_possible_finish=1,
        worst_possible_finish=3,
        expected_finish=expected_finish,
        playoff_probability=playoff_probability,
        champion_probability=0.33,
        remaining_strength_of_schedule=0.5,
        fate_control=True,
        required_results=[f"Win vs {name} Rival"],
        helpful_results=[f"{name} Rival draws"],
        eliminating_results=[],
        feature_contributions=[
            FeatureContribution("historical_match_win_rate", 0.1, 0.8, "Historical edge"),
            FeatureContribution("current_form", -0.03, 0.7, "Recent form"),
        ],
        positive_drivers=[FeatureContribution("historical_match_win_rate", 0.1, 0.8, "Historical edge")],
        negative_drivers=[FeatureContribution("current_form", -0.03, 0.7, "Recent form")],
        confidence=0.75,
    )


def test_build_scenario_report_creates_three_scenarios():
    players = [
        _player("a", "Alice", 0.82, 1.3),
        _player("b", "Bob", 0.56, 2.0),
        _player("c", "Charlie", 0.31, 2.7),
    ]
    remaining_match = MatchSnapshot(
        match_id="m1",
        round_id="r1",
        round_nr=2,
        round_start_date="2026-07-11",
        player_a_id="a",
        player_a_name="Alice",
        player_a_deck="DeckA",
        player_b_id="b",
        player_b_name="Bob",
        player_b_deck="DeckB",
        match_type="Round",
    )
    artifacts = SimulationArtifacts(
        player_order=["a", "b", "c"],
        completed_matches=[],
        remaining_matches=[remaining_match],
        outcome_matrix=np.array([[0], [0], [2], [1]], dtype=np.int8),
        rank_matrix=np.array(
            [
                [0, 1, 2],
                [0, 1, 2],
                [1, 0, 2],
                [2, 0, 1],
            ],
            dtype=np.int16,
        ),
        points_matrix=np.array(
            [
                [21.0, 18.0, 12.0],
                [21.0, 18.0, 12.0],
                [18.0, 21.0, 12.0],
                [17.0, 16.0, 19.0],
            ],
            dtype=np.float64,
        ),
        game_wins_matrix=np.array(
            [
                [14.0, 12.0, 8.0],
                [14.0, 12.0, 8.0],
                [12.0, 14.0, 8.0],
                [11.0, 10.0, 13.0],
            ],
            dtype=np.float64,
        ),
        total_games_matrix=np.array(
            [
                [24.0, 24.0, 24.0],
                [24.0, 24.0, 24.0],
                [24.0, 24.0, 24.0],
                [24.0, 24.0, 24.0],
            ],
            dtype=np.float64,
        ),
    )
    match_probabilities = [
        MatchProbability(
            match_id="m1",
            round_nr=2,
            player_a_id="a",
            player_a_name="Alice",
            player_b_id="b",
            player_b_name="Bob",
            player_a_win_probability=0.62,
            draw_probability=0.13,
            player_b_win_probability=0.25,
            baseline_probability=0.44,
            confidence=0.8,
            feature_contributions=[
                FeatureContribution("historical_match_win_rate", 0.11, 0.85, "Historical edge"),
                FeatureContribution("head_to_head", -0.02, 0.6, "Head-to-head"),
            ],
        )
    ]

    scenarios = build_scenario_report(
        artifacts=artifacts,
        player_predictions=players,
        match_probabilities=match_probabilities,
        critical_matches=[],
        playoff_cut=2,
    )

    assert len(scenarios) == 3
    assert [scenario.scenario_type for scenario in scenarios] == ["most_likely", "bubble_race", "chaos"]
    assert all(0.0 <= scenario.scenario_probability <= 1.0 for scenario in scenarios)
    assert scenarios[0].champion == "Alice"
