from __future__ import annotations

from typing import Dict, List

from prediction.explainability_engine import FEATURE_LABELS
from prediction.types import CriticalMatch, PlayerPrediction


def build_ai_explanation(players: List[PlayerPrediction], critical_matches: List[CriticalMatch]) -> str:
    if not players:
        return "No actionable prediction narrative is available yet."

    leader = players[0]
    lines = [f"{leader.player_name} currently has a {leader.playoff_probability:.0%} playoff probability."]
    if leader.positive_drivers:
        top_positive = leader.positive_drivers[0]
        lines.append(
            f"Largest positive factor: {FEATURE_LABELS.get(top_positive.feature_name, top_positive.feature_name)} ({top_positive.contribution:+.0%})."
        )
    if leader.negative_drivers:
        top_negative = leader.negative_drivers[0]
        lines.append(
            f"Largest negative factor: {FEATURE_LABELS.get(top_negative.feature_name, top_negative.feature_name)} ({top_negative.contribution:+.0%})."
        )
    if len(players) > 1:
        contender = players[1]
        lines.append(
            f"{contender.player_name} follows with a {contender.playoff_probability:.0%} playoff probability and {contender.champion_probability:.0%} title chance."
        )
    if critical_matches:
        top_match = critical_matches[0]
        lines.append(f"Most important remaining match: {top_match.match_label}.")
    return "\n".join(lines)


def build_playoff_overview(players: List[PlayerPrediction], playoff_cut: int) -> List[Dict[str, str]]:
    ranked = sorted(players, key=lambda p: p.playoff_probability, reverse=True)
    overview: List[Dict[str, str]] = []
    for player in ranked:
        chance = player.playoff_probability
        if chance >= 0.75:
            status = "Very Likely"
        elif chance >= 0.45:
            status = "In Contention"
        else:
            status = "Long Shot"

        reason_parts = [
            f"{chance:.0%} playoff chance",
            f"currently rank {player.current_rank}",
            f"expected finish {player.expected_finish:.1f}",
        ]
        if player.remaining_strength_of_schedule >= 0.58:
            reason_parts.append("difficult remaining schedule")
        elif player.remaining_strength_of_schedule <= 0.42:
            reason_parts.append("favorable remaining schedule")
        key_result = f"; key match: {player.required_results[0]}" if player.required_results else ""

        overview.append(
            {
                "player_name": player.player_name,
                "status": status,
                "reason": f"{', '.join(reason_parts)}{key_result}.",
            }
        )
    return overview
