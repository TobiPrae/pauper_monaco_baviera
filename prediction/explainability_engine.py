from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Dict, List

from prediction.types import FeatureContribution, MatchProbability, PlayerPrediction


FEATURE_LABELS: Dict[str, str] = {
    "historical_match_win_rate": "Historical Match Win Rate",
    "historical_game_win_rate": "Historical Game Win Rate",
    "head_to_head": "Head-to-Head",
    "deck_matchup": "Deck Matchup",
    "current_form": "Current Form",
    "strength_of_schedule": "Strength of Schedule",
    "remaining_opponent_strength": "Remaining Opponent Strength",
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _driver_confidence(contributions: List[FeatureContribution]) -> float:
    if not contributions:
        return 0.0
    total = sum(abs(item.contribution) for item in contributions)
    if total <= 1e-12:
        return sum(item.confidence for item in contributions) / len(contributions)
    weighted = sum(abs(item.contribution) * item.confidence for item in contributions)
    return _clamp(weighted / total, 0.0, 1.0)


class PredictionExplainabilityEngine:
    def compute_match_feature_contributions(self, match_probability: MatchProbability) -> List[FeatureContribution]:
        delta = match_probability.player_a_win_probability - match_probability.baseline_probability
        total_weighted = sum(item.weighted_score for item in match_probability.feature_contributions)

        if abs(total_weighted) <= 1e-12:
            return [replace(item, contribution=0.0) for item in match_probability.feature_contributions]

        factor = delta / total_weighted
        return [replace(item, contribution=item.weighted_score * factor) for item in match_probability.feature_contributions]

    def compute_player_explainability(self, players: List[PlayerPrediction], matches: List[MatchProbability], playoff_cut: int) -> List[PlayerPrediction]:
        n_players = max(len(players), 1)
        baseline_playoff_probability = playoff_cut / n_players
        matches_by_player: Dict[str, List[MatchProbability]] = defaultdict(list)
        for match in matches:
            matches_by_player[match.player_a_id].append(match)
            matches_by_player[match.player_b_id].append(match)

        enriched: List[PlayerPrediction] = []
        for player in players:
            raw_feature_totals: Dict[str, float] = defaultdict(float)
            confidence_weight: Dict[str, float] = defaultdict(float)
            absolute_weight: Dict[str, float] = defaultdict(float)
            explanations: Dict[str, str] = {}

            for match in matches_by_player.get(player.player_id, []):
                sign = 1.0 if player.player_id == match.player_a_id else -1.0
                for item in match.feature_contributions:
                    raw_feature_totals[item.feature_name] += sign * item.contribution
                    contribution_size = abs(item.contribution)
                    confidence_weight[item.feature_name] += contribution_size * item.confidence
                    absolute_weight[item.feature_name] += contribution_size
                    explanations[item.feature_name] = item.explanation

            delta = player.playoff_probability - baseline_playoff_probability
            raw_sum = sum(raw_feature_totals.values())

            feature_contributions: List[FeatureContribution] = []
            if abs(raw_sum) <= 1e-12:
                if raw_feature_totals:
                    scale = delta / len(raw_feature_totals)
                    for feature_name in sorted(raw_feature_totals.keys()):
                        avg_confidence = confidence_weight[feature_name] / absolute_weight[feature_name] if absolute_weight[feature_name] > 1e-12 else 0.5
                        feature_contributions.append(
                            FeatureContribution(
                                feature_name=feature_name,
                                contribution=scale,
                                confidence=_clamp(avg_confidence, 0.0, 1.0),
                                explanation=explanations.get(feature_name, ""),
                            )
                        )
                else:
                    feature_contributions = []
            else:
                factor = delta / raw_sum
                for feature_name, raw_value in sorted(raw_feature_totals.items()):
                    avg_confidence = confidence_weight[feature_name] / absolute_weight[feature_name] if absolute_weight[feature_name] > 1e-12 else 0.5
                    feature_contributions.append(
                        FeatureContribution(
                            feature_name=feature_name,
                            contribution=raw_value * factor,
                            confidence=_clamp(avg_confidence, 0.0, 1.0),
                            explanation=explanations.get(feature_name, ""),
                        )
                    )

            feature_contributions.sort(key=lambda item: abs(item.contribution), reverse=True)
            positive_drivers = sorted((item for item in feature_contributions if item.contribution > 0), key=lambda item: item.contribution, reverse=True)[:3]
            negative_drivers = sorted((item for item in feature_contributions if item.contribution < 0), key=lambda item: item.contribution)[:3]

            enriched.append(
                replace(
                    player,
                    feature_contributions=feature_contributions,
                    positive_drivers=positive_drivers,
                    negative_drivers=negative_drivers,
                    confidence=_driver_confidence(feature_contributions),
                )
            )
        return enriched

    def build_league_insights(self, players: List[PlayerPrediction], matches: List[MatchProbability]) -> Dict[str, str]:
        all_player_contributions = [item for player in players for item in player.feature_contributions]
        if all_player_contributions:
            feature_influence: Dict[str, float] = defaultdict(float)
            for item in all_player_contributions:
                feature_influence[item.feature_name] += abs(item.contribution)
            most_influential_name, most_influential_value = max(feature_influence.items(), key=lambda pair: pair[1])
            strongest_positive = max(all_player_contributions, key=lambda item: item.contribution)
            strongest_negative = min(all_player_contributions, key=lambda item: item.contribution)
        else:
            most_influential_name, most_influential_value = "n/a", 0.0
            strongest_positive = FeatureContribution("n/a", 0.0, 0.0, "")
            strongest_negative = FeatureContribution("n/a", 0.0, 0.0, "")

        if matches:
            most_important_match = max(matches, key=lambda match: 1.0 - max(match.player_a_win_probability, match.draw_probability, match.player_b_win_probability))
            most_balanced_match = min(matches, key=lambda match: abs(match.player_a_win_probability - match.player_b_win_probability))
        else:
            most_important_match = None
            most_balanced_match = None

        schedule_advantage = max(
            players,
            key=lambda player: sum(item.contribution for item in player.feature_contributions if item.feature_name in ("strength_of_schedule", "remaining_opponent_strength")),
            default=None,
        )
        deck_advantage = max(
            players,
            key=lambda player: sum(item.contribution for item in player.feature_contributions if item.feature_name == "deck_matchup"),
            default=None,
        )

        return {
            "most_influential_feature": f"{FEATURE_LABELS.get(most_influential_name, most_influential_name)} ({most_influential_value:.1%} total impact)",
            "most_important_remaining_match": (f"{most_important_match.player_a_name} vs {most_important_match.player_b_name}" if most_important_match else "N/A"),
            "largest_schedule_advantage": (schedule_advantage.player_name if schedule_advantage else "N/A"),
            "largest_deck_advantage": (deck_advantage.player_name if deck_advantage else "N/A"),
            "most_balanced_matchup": (f"{most_balanced_match.player_a_name} vs {most_balanced_match.player_b_name}" if most_balanced_match else "N/A"),
            "strongest_positive_driver": f"{FEATURE_LABELS.get(strongest_positive.feature_name, strongest_positive.feature_name)} ({strongest_positive.contribution:+.1%})",
            "strongest_negative_driver": f"{FEATURE_LABELS.get(strongest_negative.feature_name, strongest_negative.feature_name)} ({strongest_negative.contribution:+.1%})",
        }
