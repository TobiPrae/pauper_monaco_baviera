from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from prediction.types import CompletedMatchSnapshot, MatchSnapshot


@dataclass
class SimulationBase:
    player_ids: List[str]
    base_points: np.ndarray
    base_game_wins: np.ndarray
    base_total_games: np.ndarray
    completed_h2h_points: np.ndarray
    remaining_pair_to_match_index: Dict[Tuple[int, int], int]


def _gwr(game_wins: float, total_games: float) -> float:
    return game_wins / total_games if total_games > 0 else 0.0


def build_simulation_base(players: List[str], completed_matches: List[CompletedMatchSnapshot], remaining_matches: List[MatchSnapshot]) -> SimulationBase:
    player_index = {pid: idx for idx, pid in enumerate(players)}
    n = len(players)
    base_points = np.zeros(n, dtype=np.float64)
    base_game_wins = np.zeros(n, dtype=np.float64)
    base_total_games = np.zeros(n, dtype=np.float64)
    completed_h2h_points = np.zeros((n, n), dtype=np.float64)

    for match in completed_matches:
        i = player_index[match.player_a_id]
        j = player_index[match.player_b_id]
        base_points[i] += match.points_a
        base_points[j] += match.points_b
        base_game_wins[i] += match.game_wins_a
        base_game_wins[j] += match.game_wins_b
        base_total_games[i] += match.total_games
        base_total_games[j] += match.total_games
        completed_h2h_points[i, j] += match.points_a
        completed_h2h_points[j, i] += match.points_b

    remaining_pair_to_match_index: Dict[Tuple[int, int], int] = {}
    for idx, match in enumerate(remaining_matches):
        i = player_index[match.player_a_id]
        j = player_index[match.player_b_id]
        remaining_pair_to_match_index[(i, j)] = idx
        remaining_pair_to_match_index[(j, i)] = idx

    return SimulationBase(
        player_ids=players,
        base_points=base_points,
        base_game_wins=base_game_wins,
        base_total_games=base_total_games,
        completed_h2h_points=completed_h2h_points,
        remaining_pair_to_match_index=remaining_pair_to_match_index,
    )


def _resolve_tie_group(
    tied: List[int],
    points: np.ndarray,
    gwr: np.ndarray,
    outcomes: np.ndarray,
    base: SimulationBase,
    matches: List[MatchSnapshot],
) -> List[int]:
    if len(tied) <= 1:
        return tied

    # Head-to-head mini table among tie group.
    h2h_points = {idx: 0.0 for idx in tied}
    player_index = {pid: idx for idx, pid in enumerate(base.player_ids)}
    for i in tied:
        for j in tied:
            if i == j:
                continue
            h2h_points[i] += base.completed_h2h_points[i, j]

            match_idx = base.remaining_pair_to_match_index.get((i, j))
            if match_idx is None:
                continue
            result = outcomes[match_idx]
            match = matches[match_idx]
            a_idx = player_index[match.player_a_id]
            if i == a_idx:
                if result == 0:
                    h2h_points[i] += 3.0
                elif result == 1:
                    h2h_points[i] += 1.0
            else:
                if result == 2:
                    h2h_points[i] += 3.0
                elif result == 1:
                    h2h_points[i] += 1.0

    ordered = sorted(tied, key=lambda idx: (-h2h_points[idx], -points[idx], -gwr[idx], base.player_ids[idx]))
    return ordered


def _rank_single_simulation(points: np.ndarray, game_wins: np.ndarray, total_games: np.ndarray, outcomes: np.ndarray, base: SimulationBase, matches: List[MatchSnapshot]) -> np.ndarray:
    n = len(points)
    gwr = np.array([_gwr(game_wins[i], total_games[i]) for i in range(n)])
    ordered = list(range(n))
    ordered.sort(key=lambda idx: (points[idx], gwr[idx]), reverse=True)

    final_order: List[int] = []
    cursor = 0
    while cursor < len(ordered):
        current = ordered[cursor]
        group = [current]
        cursor += 1
        while cursor < len(ordered):
            nxt = ordered[cursor]
            if abs(points[nxt] - points[current]) < 1e-9 and abs(gwr[nxt] - gwr[current]) < 1e-12:
                group.append(nxt)
                cursor += 1
            else:
                break
        final_order.extend(_resolve_tie_group(group, points, gwr, outcomes, base, matches))
    return np.array(final_order, dtype=np.int16)


def run_monte_carlo(
    simulations: int,
    random_seed: int,
    match_probabilities: np.ndarray,
    base: SimulationBase,
    matches: List[MatchSnapshot],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(random_seed)
    n_players = len(base.player_ids)
    n_matches = len(matches)

    if n_matches == 0:
        rank_matrix = np.tile(np.arange(n_players, dtype=np.int16), (simulations, 1))
        points_matrix = np.tile(base.base_points, (simulations, 1))
        game_wins_matrix = np.tile(base.base_game_wins, (simulations, 1))
        total_games_matrix = np.tile(base.base_total_games, (simulations, 1))
        return np.zeros((simulations, 0), dtype=np.int8), rank_matrix, points_matrix, game_wins_matrix, total_games_matrix

    draws = rng.random((simulations, n_matches))
    cdf = np.cumsum(match_probabilities, axis=1)  # (n_matches, 3)
    outcome_matrix = np.zeros((simulations, n_matches), dtype=np.int8)
    for m_idx in range(n_matches):
        u = draws[:, m_idx]
        outcome_matrix[:, m_idx] = np.where(u < cdf[m_idx, 0], 0, np.where(u < cdf[m_idx, 1], 1, 2))

    points_matrix = np.tile(base.base_points, (simulations, 1))
    game_wins_matrix = np.tile(base.base_game_wins, (simulations, 1))
    total_games_matrix = np.tile(base.base_total_games, (simulations, 1))
    player_index = {pid: idx for idx, pid in enumerate(base.player_ids)}

    for m_idx, match in enumerate(matches):
        out = outcome_matrix[:, m_idx]
        a_idx = player_index[match.player_a_id]
        b_idx = player_index[match.player_b_id]

        points_matrix[:, a_idx] += np.where(out == 0, 3.0, np.where(out == 1, 1.0, 0.0))
        points_matrix[:, b_idx] += np.where(out == 2, 3.0, np.where(out == 1, 1.0, 0.0))

        game_wins_matrix[:, a_idx] += np.where(out == 0, 2.0, np.where(out == 1, 1.0, 1.0))
        game_wins_matrix[:, b_idx] += np.where(out == 2, 2.0, np.where(out == 1, 1.0, 1.0))
        total_games_matrix[:, a_idx] += np.where(out == 1, 2.0, 3.0)
        total_games_matrix[:, b_idx] += np.where(out == 1, 2.0, 3.0)

    rank_matrix = np.zeros((simulations, n_players), dtype=np.int16)
    for sim_idx in range(simulations):
        rank_matrix[sim_idx] = _rank_single_simulation(
            points_matrix[sim_idx],
            game_wins_matrix[sim_idx],
            total_games_matrix[sim_idx],
            outcome_matrix[sim_idx],
            base,
            matches,
        )
    return outcome_matrix, rank_matrix, points_matrix, game_wins_matrix, total_games_matrix
