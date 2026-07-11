from dataclasses import dataclass, field
from typing import Dict


DEFAULT_FEATURE_WEIGHTS: Dict[str, float] = {
    "historical_match_win_rate": 1.35,
    "historical_game_win_rate": 1.1,
    "head_to_head": 1.25,
    "deck_matchup": 0.95,
    "current_form": 1.05,
    "strength_of_schedule": 0.75,
    "remaining_opponent_strength": 0.6,
}


@dataclass(frozen=True)
class PredictionConfig:
    simulations: int = 50_000
    random_seed: int = 42
    laplace_alpha: float = 6.0
    logistic_scale: float = 3.0
    min_draw_probability: float = 0.08
    max_draw_probability: float = 0.22
    playoff_cut: int = 4
    feature_weights: Dict[str, float] = field(default_factory=lambda: DEFAULT_FEATURE_WEIGHTS.copy())
