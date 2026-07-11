from prediction.explainability_engine import PredictionExplainabilityEngine
from prediction.types import FeatureContribution, MatchProbability, PlayerPrediction


def test_match_contributions_reconstruct_probability_delta():
    engine = PredictionExplainabilityEngine()
    match = MatchProbability(
        match_id="m1",
        round_nr=1,
        player_a_id="a",
        player_a_name="Alice",
        player_b_id="b",
        player_b_name="Bob",
        player_a_win_probability=0.72,
        draw_probability=0.12,
        player_b_win_probability=0.16,
        baseline_probability=0.44,
        confidence=0.8,
        feature_contributions=[
            FeatureContribution("historical_match_win_rate", 0.0, 0.9, "Hist", weighted_score=0.28),
            FeatureContribution("head_to_head", 0.0, 0.6, "H2H", weighted_score=-0.07),
            FeatureContribution("deck_matchup", 0.0, 0.7, "Deck", weighted_score=0.14),
        ],
    )

    contributions = engine.compute_match_feature_contributions(match)
    reconstructed = match.baseline_probability + sum(item.contribution for item in contributions)
    assert abs(reconstructed - match.player_a_win_probability) < 1e-9


def test_player_contributions_reconstruct_playoff_probability():
    engine = PredictionExplainabilityEngine()
    players = [
        PlayerPrediction(
            player_id="a",
            player_name="Alice",
            current_rank=1,
            most_likely_finish=1,
            best_possible_finish=1,
            worst_possible_finish=4,
            expected_finish=1.8,
            playoff_probability=0.75,
            champion_probability=0.4,
            remaining_strength_of_schedule=0.45,
            fate_control=True,
            required_results=[],
            helpful_results=[],
            eliminating_results=[],
            feature_contributions=[],
            positive_drivers=[],
            negative_drivers=[],
            confidence=0.0,
        ),
        PlayerPrediction(
            player_id="b",
            player_name="Bob",
            current_rank=2,
            most_likely_finish=2,
            best_possible_finish=1,
            worst_possible_finish=4,
            expected_finish=2.2,
            playoff_probability=0.55,
            champion_probability=0.25,
            remaining_strength_of_schedule=0.52,
            fate_control=True,
            required_results=[],
            helpful_results=[],
            eliminating_results=[],
            feature_contributions=[],
            positive_drivers=[],
            negative_drivers=[],
            confidence=0.0,
        ),
    ]
    matches = [
        MatchProbability(
            match_id="m1",
            round_nr=1,
            player_a_id="a",
            player_a_name="Alice",
            player_b_id="b",
            player_b_name="Bob",
            player_a_win_probability=0.65,
            draw_probability=0.10,
            player_b_win_probability=0.25,
            baseline_probability=0.44,
            confidence=0.75,
            feature_contributions=[
                FeatureContribution("historical_match_win_rate", 0.10, 0.9, "Hist"),
                FeatureContribution("deck_matchup", 0.06, 0.8, "Deck"),
                FeatureContribution("head_to_head", -0.03, 0.7, "H2H"),
            ],
        )
    ]

    enriched = engine.compute_player_explainability(players, matches, playoff_cut=1)
    baseline = 1 / len(players)
    for player in enriched:
        reconstructed = baseline + sum(item.contribution for item in player.feature_contributions)
        assert abs(reconstructed - player.playoff_probability) < 1e-9
