from prediction.explanation import build_playoff_overview
from prediction.types import PlayerPrediction


def _prediction(name: str, playoff_probability: float, strength: float) -> PlayerPrediction:
    return PlayerPrediction(
        player_id=name.lower(),
        player_name=name,
        current_rank=2,
        most_likely_finish=2,
        best_possible_finish=1,
        worst_possible_finish=5,
        expected_finish=2.4,
        playoff_probability=playoff_probability,
        champion_probability=0.2,
        remaining_strength_of_schedule=strength,
        fate_control=True,
        required_results=["Win vs Rival"],
        helpful_results=[],
        eliminating_results=[],
        feature_contributions=[],
        positive_drivers=[],
        negative_drivers=[],
        confidence=0.7,
    )


def test_build_playoff_overview_sorts_and_labels():
    overview = build_playoff_overview(
        [
            _prediction("Charlie", 0.33, 0.61),
            _prediction("Alice", 0.81, 0.39),
            _prediction("Bob", 0.58, 0.50),
        ],
        playoff_cut=4,
    )

    assert [row["player_name"] for row in overview] == ["Alice", "Bob", "Charlie"]
    assert [row["status"] for row in overview] == ["Very Likely", "In Contention", "Long Shot"]
    assert "favorable remaining schedule" in overview[0]["reason"]
    assert "difficult remaining schedule" in overview[2]["reason"]
    assert "|" not in overview[0]["reason"]
    assert overview[0]["reason"].endswith(".")
