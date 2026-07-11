from __future__ import annotations

from typing import Dict, List

import numpy as np

from prediction.types import CriticalMatch, MatchProbability, MatchSnapshot, PlayerPrediction


def build_player_predictions(
    player_ids: List[str],
    player_names: Dict[str, str],
    current_ranks: Dict[str, int],
    rank_matrix: np.ndarray,
    playoff_cut: int,
    remaining_strength: Dict[str, float],
    remaining_matches: List[MatchSnapshot],
) -> List[PlayerPrediction]:
    simulations = rank_matrix.shape[0]
    rank_positions = np.zeros((len(player_ids), simulations), dtype=np.int16)
    for sim_idx in range(simulations):
        for rank_idx, player_idx in enumerate(rank_matrix[sim_idx], start=1):
            rank_positions[player_idx, sim_idx] = rank_idx

    predictions: List[PlayerPrediction] = []
    for player_idx, player_id in enumerate(player_ids):
        ranks = rank_positions[player_idx]
        rank_counts = np.bincount(ranks, minlength=len(player_ids) + 1)
        most_likely = int(np.argmax(rank_counts[1:]) + 1)
        expected = float(np.mean(ranks))
        best = int(np.min(ranks))
        worst = int(np.max(ranks))
        playoff_prob = float(np.mean(ranks <= playoff_cut))
        champion_prob = float(np.mean(ranks == 1))

        own_matches = [m for m in remaining_matches if player_id in (m.player_a_id, m.player_b_id)]
        required = [f"Win vs {m.player_b_name if m.player_a_id == player_id else m.player_a_name}" for m in own_matches[:3]]
        helpful = [f"{m.player_a_name} vs {m.player_b_name} ends in draw" for m in remaining_matches if player_id not in (m.player_a_id, m.player_b_id)][:3]
        eliminating = [f"Lose vs {m.player_b_name if m.player_a_id == player_id else m.player_a_name}" for m in own_matches[:2]]

        predictions.append(
            PlayerPrediction(
                player_id=player_id,
                player_name=player_names[player_id],
                current_rank=current_ranks.get(player_id, len(player_ids)),
                most_likely_finish=most_likely,
                best_possible_finish=best,
                worst_possible_finish=worst,
                expected_finish=expected,
                playoff_probability=playoff_prob,
                champion_probability=champion_prob,
                remaining_strength_of_schedule=remaining_strength.get(player_id, 0.5),
                fate_control=bool(required),
                required_results=required,
                helpful_results=helpful,
                eliminating_results=eliminating,
                feature_contributions=[],
                positive_drivers=[],
                negative_drivers=[],
                confidence=0.0,
            )
        )
    predictions.sort(key=lambda p: p.expected_finish)
    return predictions


def estimate_remaining_strength(player_ids: List[str], player_strength: Dict[str, float], remaining_matches: List[MatchSnapshot]) -> Dict[str, float]:
    values: Dict[str, List[float]] = {pid: [] for pid in player_ids}
    for match in remaining_matches:
        values[match.player_a_id].append(player_strength.get(match.player_b_id, 0.5))
        values[match.player_b_id].append(player_strength.get(match.player_a_id, 0.5))
    return {pid: (sum(v) / len(v) if v else 0.5) for pid, v in values.items()}


def compute_critical_matches(match_probabilities: List[MatchProbability], champion_probability: Dict[str, float]) -> List[CriticalMatch]:
    critical: List[CriticalMatch] = []
    for mp in match_probabilities:
        uncertainty = 1.0 - max(mp.player_a_win_probability, mp.draw_probability, mp.player_b_win_probability)
        title_pressure = champion_probability.get(mp.player_a_id, 0.0) + champion_probability.get(mp.player_b_id, 0.0)
        leverage = uncertainty * (0.5 + title_pressure)
        critical.append(
            CriticalMatch(
                match_id=mp.match_id,
                round_nr=mp.round_nr,
                match_label=f"{mp.player_a_name} vs {mp.player_b_name}",
                leverage_score=leverage,
                reason="High uncertainty with direct impact on top-of-table outcomes.",
            )
        )
    critical.sort(key=lambda item: item.leverage_score, reverse=True)
    return critical[:10]
