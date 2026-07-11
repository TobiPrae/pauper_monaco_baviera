from prediction.features import FeatureContext, HistoricalMatchWinRateFeature
from prediction.types import CompletedMatchSnapshot, MatchSnapshot


def _completed(result: str) -> CompletedMatchSnapshot:
    return CompletedMatchSnapshot(
        match_id="m",
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
        result=result,
        points_a=3 if result == "A" else (1 if result == "D" else 0),
        points_b=3 if result == "B" else (1 if result == "D" else 0),
        game_wins_a=2,
        game_wins_b=1,
        total_games=3,
    )


def test_historical_match_win_rate_uses_smoothing():
    feature = HistoricalMatchWinRateFeature()
    context = FeatureContext(
        historical_matches=[_completed("A")],
        target_completed_matches=[],
        remaining_matches=[],
        player_strength={"a": 0.5, "b": 0.5},
        deck_strength={"DeckA": 0.5, "DeckB": 0.5},
        laplace_alpha=10.0,
        league_average_match_rate=0.5,
        league_average_game_rate=0.5,
    )
    match = MatchSnapshot(
        match_id="m2",
        round_id="r2",
        round_nr=2,
        round_start_date="2026-01-02",
        player_a_id="a",
        player_a_name="A",
        player_a_deck="DeckA",
        player_b_id="b",
        player_b_name="B",
        player_b_deck="DeckB",
        match_type="Round",
    )
    value = feature.evaluate(context, match)
    assert value.score < 0.2
    assert value.score > -0.2
