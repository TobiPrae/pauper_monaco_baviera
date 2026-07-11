from __future__ import annotations

from typing import Dict

import numpy as np

from prediction.simulation import _rank_single_simulation, build_simulation_base
from prediction.types import PredictionReport


RESULT_TO_CODE = {
    "Player A Win": 0,
    "Draw": 1,
    "Player B Win": 2,
}


def recalculate_with_overrides(report: PredictionReport, overrides: Dict[str, int]) -> np.ndarray:
    artifacts = report.internal_artifacts
    if artifacts is None:
        return np.array([])

    outcome_matrix = artifacts.outcome_matrix.copy()
    match_idx_by_id = {m.match_id: idx for idx, m in enumerate(artifacts.remaining_matches)}
    for match_id, outcome_code in overrides.items():
        idx = match_idx_by_id.get(match_id)
        if idx is None:
            continue
        outcome_matrix[:, idx] = outcome_code

    player_ids = artifacts.player_order
    player_index = {pid: idx for idx, pid in enumerate(player_ids)}
    base_points = np.zeros(len(player_ids), dtype=np.float64)
    base_game_wins = np.zeros(len(player_ids), dtype=np.float64)
    base_total_games = np.zeros(len(player_ids), dtype=np.float64)
    for row in report.current_standings:
        idx = player_index[row["player_id"]]
        base_points[idx] = float(row["points"])
        base_game_wins[idx] = float(row["game_wins"])
        base_total_games[idx] = float(row["total_games"])

    base = build_simulation_base(player_ids, artifacts.completed_matches, artifacts.remaining_matches)
    base.base_points = base_points
    base.base_game_wins = base_game_wins
    base.base_total_games = base_total_games

    sim_count = outcome_matrix.shape[0]
    points_matrix = np.tile(base_points, (sim_count, 1))
    game_wins_matrix = np.tile(base_game_wins, (sim_count, 1))
    total_games_matrix = np.tile(base_total_games, (sim_count, 1))

    for m_idx, match in enumerate(artifacts.remaining_matches):
        out = outcome_matrix[:, m_idx]
        a_idx = player_index[match.player_a_id]
        b_idx = player_index[match.player_b_id]
        points_matrix[:, a_idx] += np.where(out == 0, 3.0, np.where(out == 1, 1.0, 0.0))
        points_matrix[:, b_idx] += np.where(out == 2, 3.0, np.where(out == 1, 1.0, 0.0))
        game_wins_matrix[:, a_idx] += np.where(out == 0, 2.0, np.where(out == 1, 1.0, 1.0))
        game_wins_matrix[:, b_idx] += np.where(out == 2, 2.0, np.where(out == 1, 1.0, 1.0))
        total_games_matrix[:, a_idx] += np.where(out == 1, 2.0, 3.0)
        total_games_matrix[:, b_idx] += np.where(out == 1, 2.0, 3.0)

    rank_matrix = np.zeros_like(artifacts.rank_matrix)
    for sim_idx in range(rank_matrix.shape[0]):
        rank_matrix[sim_idx] = _rank_single_simulation(
            points_matrix[sim_idx],
            game_wins_matrix[sim_idx],
            total_games_matrix[sim_idx],
            outcome_matrix[sim_idx],
            base,
            artifacts.remaining_matches,
        )
    return rank_matrix
