from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class PlayerSnapshot:
    player_id: str
    player_name: str
    deck_name: str


@dataclass(frozen=True)
class MatchSnapshot:
    match_id: str
    round_id: str
    round_nr: int
    round_start_date: str
    player_a_id: str
    player_a_name: str
    player_a_deck: str
    player_b_id: str
    player_b_name: str
    player_b_deck: str
    match_type: str


@dataclass(frozen=True)
class CompletedMatchSnapshot(MatchSnapshot):
    result: str
    points_a: int
    points_b: int
    game_wins_a: int
    game_wins_b: int
    total_games: int


@dataclass(frozen=True)
class FeatureContribution:
    feature_name: str
    contribution: float
    confidence: float
    explanation: str
    score: float = 0.0
    weighted_score: float = 0.0


@dataclass(frozen=True)
class MatchProbability:
    match_id: str
    round_nr: int
    player_a_id: str
    player_a_name: str
    player_b_id: str
    player_b_name: str
    player_a_win_probability: float
    draw_probability: float
    player_b_win_probability: float
    baseline_probability: float
    confidence: float
    feature_contributions: List[FeatureContribution]


@dataclass(frozen=True)
class PlayerPrediction:
    player_id: str
    player_name: str
    current_rank: int
    most_likely_finish: int
    best_possible_finish: int
    worst_possible_finish: int
    expected_finish: float
    playoff_probability: float
    champion_probability: float
    remaining_strength_of_schedule: float
    fate_control: bool
    required_results: List[str]
    helpful_results: List[str]
    eliminating_results: List[str]
    feature_contributions: List[FeatureContribution]
    positive_drivers: List[FeatureContribution]
    negative_drivers: List[FeatureContribution]
    confidence: float


@dataclass(frozen=True)
class CriticalMatch:
    match_id: str
    round_nr: int
    match_label: str
    leverage_score: float
    reason: str


@dataclass(frozen=True)
class PredictionDiagnostics:
    prediction_accuracy: float
    prediction_calibration_error: float
    average_prediction_error: float
    historical_performance_score: float
    feature_contributions: Dict[str, float]


@dataclass(frozen=True)
class LeagueSummary:
    playoff_cut: int
    title_favorite_player_id: str
    title_favorite_player_name: str
    closest_playoff_bubble: str
    confidence_label: str


@dataclass(frozen=True)
class ScenarioReport:
    scenario_type: str
    scenario_name: str
    scenario_probability: float
    short_description: str
    final_standings: List[Dict]
    remaining_results: List[Dict]
    playoff_teams: List[str]
    champion: str
    critical_match: str
    summary: str
    confidence: float
    key_remaining_matches: List[str] = field(default_factory=list)
    bubble_players: List[Dict] = field(default_factory=list)
    required_results: List[str] = field(default_factory=list)
    helpful_results: List[str] = field(default_factory=list)
    current_momentum: List[str] = field(default_factory=list)
    largest_upsets: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class SimulationMetadata:
    simulations: int
    random_seed: int
    generated_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SimulationArtifacts:
    player_order: List[str]
    completed_matches: List[CompletedMatchSnapshot]
    remaining_matches: List[MatchSnapshot]
    outcome_matrix: np.ndarray  # 0 = A win, 1 = draw, 2 = B win
    rank_matrix: np.ndarray  # player index per finishing position (sim, rank)
    points_matrix: np.ndarray  # (sim, player)
    game_wins_matrix: np.ndarray  # (sim, player)
    total_games_matrix: np.ndarray  # (sim, player)


@dataclass
class PredictionReport:
    league_id: str
    league_name: str
    league_nr: int
    simulation_metadata: SimulationMetadata
    current_standings: List[Dict]
    remaining_schedule: List[MatchSnapshot]
    match_probabilities: List[MatchProbability]
    player_predictions: List[PlayerPrediction]
    critical_matches: List[CriticalMatch]
    league_summary: LeagueSummary
    diagnostics: PredictionDiagnostics
    ai_explanation: str
    confidence_metrics: Dict[str, float]
    league_insights: Dict[str, str]
    scenario_reports: List[ScenarioReport]
    internal_artifacts: Optional[SimulationArtifacts] = field(default=None, repr=False, compare=False)

    def to_dict(self) -> Dict:
        return {
            "league_id": self.league_id,
            "league_name": self.league_name,
            "league_nr": self.league_nr,
            "simulation_metadata": asdict(self.simulation_metadata),
            "current_standings": self.current_standings,
            "remaining_schedule": [asdict(m) for m in self.remaining_schedule],
            "match_probabilities": [asdict(m) for m in self.match_probabilities],
            "player_predictions": [asdict(p) for p in self.player_predictions],
            "critical_matches": [asdict(m) for m in self.critical_matches],
            "league_summary": asdict(self.league_summary),
            "diagnostics": asdict(self.diagnostics),
            "ai_explanation": self.ai_explanation,
            "confidence_metrics": self.confidence_metrics,
            "league_insights": self.league_insights,
            "scenario_reports": [asdict(s) for s in self.scenario_reports],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


MatchKey = Tuple[str, str]
