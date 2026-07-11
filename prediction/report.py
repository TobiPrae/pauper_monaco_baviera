from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

import numpy as np

from prediction.config import PredictionConfig
from prediction.data import LeaguePredictionDataset, build_prediction_dataset
from prediction.diagnostics import compute_diagnostics
from prediction.explainability_engine import PredictionExplainabilityEngine
from prediction.explanation import build_ai_explanation
from prediction.features import FeatureContext, FeatureRegistry
from prediction.probability import ProbabilityEngine
from prediction.scenario_explorer import build_scenario_report
from prediction.scenarios import build_player_predictions, compute_critical_matches, estimate_remaining_strength
from prediction.simulation import build_simulation_base, run_monte_carlo
from prediction.types import (
    LeagueSummary,
    MatchProbability,
    PredictionReport,
    SimulationArtifacts,
    SimulationMetadata,
)


def _build_strength_indexes(dataset: LeaguePredictionDataset, alpha: float) -> tuple[Dict[str, float], Dict[str, float], float, float, float]:
    player_wins = defaultdict(float)
    player_matches = defaultdict(float)
    player_game_wins = defaultdict(float)
    player_games = defaultdict(float)
    deck_wins = defaultdict(float)
    deck_matches = defaultdict(float)
    draw_count = 0.0

    for match in dataset.historical_completed_matches:
        if match.result == "D":
            draw_count += 1
            player_wins[match.player_a_id] += 0.5
            player_wins[match.player_b_id] += 0.5
            deck_wins[match.player_a_deck] += 0.5
            deck_wins[match.player_b_deck] += 0.5
        elif match.result == "A":
            player_wins[match.player_a_id] += 1.0
            deck_wins[match.player_a_deck] += 1.0
        else:
            player_wins[match.player_b_id] += 1.0
            deck_wins[match.player_b_deck] += 1.0

        player_matches[match.player_a_id] += 1.0
        player_matches[match.player_b_id] += 1.0
        deck_matches[match.player_a_deck] += 1.0
        deck_matches[match.player_b_deck] += 1.0

        player_game_wins[match.player_a_id] += match.game_wins_a
        player_game_wins[match.player_b_id] += match.game_wins_b
        player_games[match.player_a_id] += match.total_games
        player_games[match.player_b_id] += match.total_games

    total_matches = max(len(dataset.historical_completed_matches), 1)
    league_average_match_rate = 0.5
    league_average_game_rate = 0.5
    base_draw_rate = draw_count / total_matches

    player_strength = {
        player.player_id: (player_wins[player.player_id] + alpha * 0.5) / (player_matches[player.player_id] + alpha)
        for player in dataset.players
    }
    deck_strength = {
        player.deck_name: (deck_wins[player.deck_name] + alpha * 0.5) / (deck_matches[player.deck_name] + alpha)
        for player in dataset.players
    }
    return player_strength, deck_strength, league_average_match_rate, league_average_game_rate, base_draw_rate


class PredictionService:
    def __init__(self, config: PredictionConfig):
        self.config = config
        self.registry = FeatureRegistry.default()
        self.explainability_engine = PredictionExplainabilityEngine()

    def build_report(self, client, selected_league) -> PredictionReport:
        dataset = build_prediction_dataset(client, selected_league)
        return self.build_report_from_dataset(dataset)

    def build_report_from_dataset(self, dataset: LeaguePredictionDataset) -> PredictionReport:
        player_strength, deck_strength, avg_match_rate, avg_game_rate, base_draw_rate = _build_strength_indexes(dataset, self.config.laplace_alpha)
        context = FeatureContext(
            historical_matches=dataset.historical_completed_matches,
            target_completed_matches=dataset.completed_target_matches,
            remaining_matches=dataset.remaining_target_matches,
            player_strength=player_strength,
            deck_strength=deck_strength,
            laplace_alpha=self.config.laplace_alpha,
            league_average_match_rate=avg_match_rate,
            league_average_game_rate=avg_game_rate,
        )

        probability_engine = ProbabilityEngine(
            feature_weights=self.config.feature_weights,
            logistic_scale=self.config.logistic_scale,
            min_draw_probability=self.config.min_draw_probability,
            max_draw_probability=self.config.max_draw_probability,
            base_draw_rate=base_draw_rate,
        )

        match_probabilities: List[MatchProbability] = []
        probability_matrix: List[List[float]] = []
        for match in dataset.remaining_target_matches:
            features = self.registry.evaluate(context, match)
            result = probability_engine.compute(features)
            match_probabilities.append(
                MatchProbability(
                    match_id=match.match_id,
                    round_nr=match.round_nr,
                    player_a_id=match.player_a_id,
                    player_a_name=match.player_a_name,
                    player_b_id=match.player_b_id,
                    player_b_name=match.player_b_name,
                    player_a_win_probability=result.p_a_win,
                    draw_probability=result.p_draw,
                    player_b_win_probability=result.p_b_win,
                    baseline_probability=result.baseline_p_a_win,
                    confidence=result.confidence,
                    feature_contributions=result.feature_contributions,
                )
            )
            probability_matrix.append([result.p_a_win, result.p_draw, result.p_b_win])

        match_probabilities = [
            MatchProbability(
                match_id=match.match_id,
                round_nr=match.round_nr,
                player_a_id=match.player_a_id,
                player_a_name=match.player_a_name,
                player_b_id=match.player_b_id,
                player_b_name=match.player_b_name,
                player_a_win_probability=match.player_a_win_probability,
                draw_probability=match.draw_probability,
                player_b_win_probability=match.player_b_win_probability,
                baseline_probability=match.baseline_probability,
                confidence=match.confidence,
                feature_contributions=self.explainability_engine.compute_match_feature_contributions(match),
            )
            for match in match_probabilities
        ]

        player_ids = [p.player_id for p in dataset.players]
        player_names = {p.player_id: p.player_name for p in dataset.players}
        base = build_simulation_base(player_ids, dataset.completed_target_matches, dataset.remaining_target_matches)
        outcome_matrix, rank_matrix, points_matrix, game_wins_matrix, total_games_matrix = run_monte_carlo(
            simulations=self.config.simulations,
            random_seed=self.config.random_seed,
            match_probabilities=np.array(probability_matrix, dtype=np.float64) if probability_matrix else np.zeros((0, 3), dtype=np.float64),
            base=base,
            matches=dataset.remaining_target_matches,
        )

        current_ranks = {row["player_id"]: row["rank"] for row in dataset.current_standings}
        remaining_strength = estimate_remaining_strength(player_ids, player_strength, dataset.remaining_target_matches)
        player_predictions = build_player_predictions(
            player_ids=player_ids,
            player_names=player_names,
            current_ranks=current_ranks,
            rank_matrix=rank_matrix,
            playoff_cut=min(self.config.playoff_cut, len(player_ids)),
            remaining_strength=remaining_strength,
            remaining_matches=dataset.remaining_target_matches,
        )
        player_predictions = self.explainability_engine.compute_player_explainability(
            players=player_predictions,
            matches=match_probabilities,
            playoff_cut=min(self.config.playoff_cut, len(player_ids)),
        )
        champion_prob = {prediction.player_id: prediction.champion_probability for prediction in player_predictions}
        critical_matches = compute_critical_matches(match_probabilities, champion_prob)
        artifacts = SimulationArtifacts(
            player_order=player_ids,
            completed_matches=dataset.completed_target_matches,
            remaining_matches=dataset.remaining_target_matches,
            outcome_matrix=outcome_matrix,
            rank_matrix=rank_matrix,
            points_matrix=points_matrix,
            game_wins_matrix=game_wins_matrix,
            total_games_matrix=total_games_matrix,
        )
        scenario_reports = build_scenario_report(
            artifacts=artifacts,
            player_predictions=player_predictions,
            match_probabilities=match_probabilities,
            critical_matches=critical_matches,
            playoff_cut=min(self.config.playoff_cut, len(player_ids)),
        )
        league_insights = self.explainability_engine.build_league_insights(player_predictions, match_probabilities)
        diagnostics = compute_diagnostics(dataset.historical_completed_matches, match_probabilities)
        ai_explanation = build_ai_explanation(player_predictions, critical_matches)

        title_favorite = player_predictions[0] if player_predictions else None
        league_summary = LeagueSummary(
            playoff_cut=min(self.config.playoff_cut, len(player_ids)),
            title_favorite_player_id=title_favorite.player_id if title_favorite else "",
            title_favorite_player_name=title_favorite.player_name if title_favorite else "N/A",
            closest_playoff_bubble=", ".join(p.player_name for p in player_predictions[2:6]) if len(player_predictions) > 3 else "N/A",
            confidence_label="High" if diagnostics.historical_performance_score >= 0.7 else ("Medium" if diagnostics.historical_performance_score >= 0.4 else "Low"),
        )

        confidence_metrics = {
            "historical_sample_coverage": diagnostics.historical_performance_score,
            "average_match_confidence": float(np.mean([m.confidence for m in match_probabilities])) if match_probabilities else 0.0,
            "model_calibration": 1.0 - diagnostics.prediction_calibration_error,
        }

        report = PredictionReport(
            league_id=dataset.league_id,
            league_name=dataset.league_name,
            league_nr=dataset.league_nr,
            simulation_metadata=SimulationMetadata(simulations=self.config.simulations, random_seed=self.config.random_seed),
            current_standings=dataset.current_standings,
            remaining_schedule=dataset.remaining_target_matches,
            match_probabilities=match_probabilities,
            player_predictions=player_predictions,
            critical_matches=critical_matches,
            league_summary=league_summary,
            diagnostics=diagnostics,
            ai_explanation=ai_explanation,
            confidence_metrics=confidence_metrics,
            league_insights=league_insights,
            scenario_reports=scenario_reports,
            internal_artifacts=artifacts,
        )
        return report
