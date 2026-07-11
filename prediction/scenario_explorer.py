from __future__ import annotations

from collections import Counter
from typing import Dict, List, Sequence, Tuple

from prediction.types import CriticalMatch, MatchProbability, PlayerPrediction, ScenarioReport, SimulationArtifacts


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _outcome_label(match, outcome: int) -> str:
    if outcome == 0:
        return f"{match.player_a_name} win"
    if outcome == 1:
        return "Draw"
    return f"{match.player_b_name} win"


def _standings_from_simulation(
    sim_idx: int,
    artifacts: SimulationArtifacts,
    player_predictions: List[PlayerPrediction],
    playoff_cut: int,
) -> Tuple[List[Dict], List[str], str]:
    names_by_id = {player.player_id: player.player_name for player in player_predictions}
    order = artifacts.rank_matrix[sim_idx]
    points = artifacts.points_matrix[sim_idx]
    total_games = artifacts.total_games_matrix[sim_idx]
    game_wins = artifacts.game_wins_matrix[sim_idx]

    standings: List[Dict] = []
    playoff_teams: List[str] = []
    champion = ""
    for rank, player_idx in enumerate(order, start=1):
        player_id = artifacts.player_order[player_idx]
        player_name = names_by_id.get(player_id, player_id)
        game_win_rate = float(game_wins[player_idx] / total_games[player_idx]) if total_games[player_idx] > 0 else 0.0
        row = {
            "Rank": rank,
            "Player": player_name,
            "Points": float(points[player_idx]),
            "Game Win Rate": game_win_rate,
            "Playoff": "✅" if rank <= playoff_cut else "",
        }
        standings.append(row)
        if rank <= playoff_cut:
            playoff_teams.append(player_name)
        if rank == 1:
            champion = player_name
    return standings, playoff_teams, champion


def _remaining_results_from_simulation(sim_idx: int, artifacts: SimulationArtifacts) -> List[Dict]:
    results: List[Dict] = []
    if artifacts.outcome_matrix.shape[1] == 0:
        return results
    for match_idx, match in enumerate(artifacts.remaining_matches):
        outcome = int(artifacts.outcome_matrix[sim_idx, match_idx])
        results.append(
            {
                "Round": match.round_nr,
                "Match": f"{match.player_a_name} vs {match.player_b_name}",
                "Result": _outcome_label(match, outcome),
            }
        )
    return results


def _probability_for_order(order_key: Tuple[int, ...], rank_keys: List[Tuple[int, ...]]) -> float:
    counts = Counter(rank_keys)
    total = max(len(rank_keys), 1)
    return counts[order_key] / total


def _playoff_set_key(order_key: Tuple[int, ...], playoff_cut: int) -> Tuple[int, ...]:
    return tuple(sorted(order_key[:playoff_cut]))


def _critical_match_label(critical_matches: List[CriticalMatch]) -> str:
    return critical_matches[0].match_label if critical_matches else "N/A"


def build_most_likely_scenario(
    artifacts: SimulationArtifacts,
    player_predictions: List[PlayerPrediction],
    critical_matches: List[CriticalMatch],
    playoff_cut: int,
) -> ScenarioReport:
    rank_keys = [tuple(int(v) for v in row) for row in artifacts.rank_matrix.tolist()]
    counts = Counter(rank_keys)
    most_likely_key, count = counts.most_common(1)[0]
    representative_sim_idx = rank_keys.index(most_likely_key)
    probability = count / max(len(rank_keys), 1)

    standings, playoff_teams, champion = _standings_from_simulation(
        representative_sim_idx, artifacts, player_predictions, playoff_cut
    )
    remaining_results = _remaining_results_from_simulation(representative_sim_idx, artifacts)
    key_remaining_matches = [item["Match"] for item in remaining_results[:3]]
    summary = (
        f"This scenario appeared in {count:,} of {len(rank_keys):,} simulations. "
        f"{champion} is champion with playoff teams: {', '.join(playoff_teams) if playoff_teams else 'none'}."
    )

    return ScenarioReport(
        scenario_type="most_likely",
        scenario_name="🎯 Most Likely",
        scenario_probability=probability,
        short_description="Current favorite outcome",
        final_standings=standings,
        remaining_results=remaining_results,
        playoff_teams=playoff_teams,
        champion=champion,
        critical_match=_critical_match_label(critical_matches),
        summary=summary,
        confidence=_clamp(0.4 + probability * 2.2, 0.0, 1.0),
        key_remaining_matches=key_remaining_matches,
    )


def build_bubble_scenario(
    artifacts: SimulationArtifacts,
    player_predictions: List[PlayerPrediction],
    match_probabilities: List[MatchProbability],
    playoff_cut: int,
) -> ScenarioReport:
    ordered_by_playoff = sorted(player_predictions, key=lambda player: player.playoff_probability, reverse=True)
    lower = max(0, playoff_cut - 2)
    upper = min(len(ordered_by_playoff), playoff_cut + 2)
    bubble_group = ordered_by_playoff[lower:upper] or ordered_by_playoff[: min(4, len(ordered_by_playoff))]
    bubble_ids = {player.player_id for player in bubble_group}
    idx_by_player = {player_id: idx for idx, player_id in enumerate(artifacts.player_order)}
    rank_keys = [tuple(int(v) for v in row) for row in artifacts.rank_matrix.tolist()]
    playoff_set_keys = [_playoff_set_key(key, playoff_cut) for key in rank_keys]
    playoff_set_counts = Counter(playoff_set_keys)

    best_sim_idx = 0
    best_score = -10**9
    for sim_idx, ranking in enumerate(artifacts.rank_matrix):
        cutoff_a_idx = int(ranking[playoff_cut - 1]) if playoff_cut - 1 < len(ranking) else int(ranking[-1])
        cutoff_b_idx = int(ranking[playoff_cut]) if playoff_cut < len(ranking) else int(ranking[-1])
        points_gap = abs(
            float(artifacts.points_matrix[sim_idx, cutoff_a_idx]) - float(artifacts.points_matrix[sim_idx, cutoff_b_idx])
        )
        in_playoffs = set(int(v) for v in ranking[:playoff_cut])
        bubble_in = len([pid for pid in bubble_ids if idx_by_player.get(pid, -1) in in_playoffs])
        split_bonus = 1.0 if 0 < bubble_in < len(bubble_group) else 0.0
        score = split_bonus * 10.0 - points_gap
        if score > best_score:
            best_score = score
            best_sim_idx = sim_idx

    chosen_key = playoff_set_keys[best_sim_idx]
    probability = playoff_set_counts[chosen_key] / max(len(playoff_set_keys), 1)
    standings, playoff_teams, champion = _standings_from_simulation(best_sim_idx, artifacts, player_predictions, playoff_cut)
    remaining_results = _remaining_results_from_simulation(best_sim_idx, artifacts)

    bubble_players = [
        {
            "Player": player.player_name,
            "Current Playoff Probability": f"{player.playoff_probability:.0%}",
            "Expected Final Rank": f"{player.expected_finish:.1f}",
        }
        for player in bubble_group
    ]
    required_results = [item for player in bubble_group for item in player.required_results][:6]
    helpful_results = [item for player in bubble_group for item in player.helpful_results][:6]
    current_momentum = [
        (
            f"{player.player_name}: positive momentum"
            if (sum(item.contribution for item in player.positive_drivers[:2]) + sum(item.contribution for item in player.negative_drivers[:2])) >= 0
            else f"{player.player_name}: negative momentum"
        )
        for player in bubble_group
    ]
    key_remaining_matches = [
        f"{match.player_a_name} vs {match.player_b_name}"
        for match in sorted(
            [
                match
                for match in match_probabilities
                if match.player_a_id in bubble_ids or match.player_b_id in bubble_ids
            ],
            key=lambda match: 1.0 - max(match.player_a_win_probability, match.draw_probability, match.player_b_win_probability),
            reverse=True,
        )[:3]
    ]

    summary = (
        f"The bubble race centers on {', '.join(player.player_name for player in bubble_group)}. "
        f"Current scenario path puts {', '.join(playoff_teams)} into playoffs."
    )
    critical_match = key_remaining_matches[0] if key_remaining_matches else "N/A"
    return ScenarioReport(
        scenario_type="bubble_race",
        scenario_name="⚔ Bubble Race",
        scenario_probability=probability,
        short_description="Current playoff battle",
        final_standings=standings,
        remaining_results=remaining_results,
        playoff_teams=playoff_teams,
        champion=champion,
        critical_match=critical_match,
        summary=summary,
        confidence=_clamp(sum(player.confidence for player in bubble_group) / max(len(bubble_group), 1), 0.0, 1.0),
        key_remaining_matches=key_remaining_matches,
        bubble_players=bubble_players,
        required_results=required_results,
        helpful_results=helpful_results,
        current_momentum=current_momentum,
    )


def build_chaos_scenario(
    artifacts: SimulationArtifacts,
    player_predictions: List[PlayerPrediction],
    match_probabilities: List[MatchProbability],
    playoff_cut: int,
) -> ScenarioReport:
    expected_order = sorted(player_predictions, key=lambda player: player.expected_finish)
    expected_rank = {player.player_id: rank for rank, player in enumerate(expected_order, start=1)}
    title_favorite_id = expected_order[0].player_id if expected_order else ""
    idx_to_player_id = {idx: player_id for idx, player_id in enumerate(artifacts.player_order)}
    rank_keys = [tuple(int(v) for v in row) for row in artifacts.rank_matrix.tolist()]
    playoff_set_keys = [_playoff_set_key(key, playoff_cut) for key in rank_keys]
    playoff_set_counts = Counter(playoff_set_keys)
    sim_count = max(len(rank_keys), 1)

    best_sim_idx = 0
    best_surprise = -10**9
    for sim_idx, ranking in enumerate(artifacts.rank_matrix):
        scenario_probability = playoff_set_counts[playoff_set_keys[sim_idx]] / sim_count
        if scenario_probability > 0.2:
            continue

        surprise = 0.0
        champion_idx = int(ranking[0])
        champion_id = idx_to_player_id[champion_idx]
        playoff_ids = {idx_to_player_id[int(v)] for v in ranking[:playoff_cut]}
        for rank, player_idx in enumerate(ranking, start=1):
            player_id = idx_to_player_id[int(player_idx)]
            surprise += abs(rank - expected_rank.get(player_id, rank))
        if title_favorite_id and title_favorite_id not in playoff_ids:
            surprise += 6.0
        if title_favorite_id and champion_id != title_favorite_id:
            surprise += 3.0
        if surprise > best_surprise:
            best_surprise = surprise
            best_sim_idx = sim_idx

    selected_playoff_key = playoff_set_keys[best_sim_idx]
    probability = playoff_set_counts[selected_playoff_key] / sim_count
    standings, playoff_teams, champion = _standings_from_simulation(best_sim_idx, artifacts, player_predictions, playoff_cut)
    remaining_results = _remaining_results_from_simulation(best_sim_idx, artifacts)

    ranking = artifacts.rank_matrix[best_sim_idx]
    largest_upsets: List[str] = []
    for rank, player_idx in enumerate(ranking, start=1):
        player_id = idx_to_player_id[int(player_idx)]
        player = next((item for item in player_predictions if item.player_id == player_id), None)
        if player is None:
            continue
        delta = rank - player.expected_finish
        if abs(delta) >= 1.5:
            largest_upsets.append(f"{player.player_name}: finished {rank}, expected {player.expected_finish:.1f}")
    largest_upsets = largest_upsets[:5]

    match_by_id = {match.match_id: match for match in match_probabilities}
    upsets: List[Tuple[float, str]] = []
    for match_idx, match in enumerate(artifacts.remaining_matches):
        outcome = int(artifacts.outcome_matrix[best_sim_idx, match_idx]) if artifacts.outcome_matrix.shape[1] > 0 else 1
        probability_a = match_by_id[match.match_id].player_a_win_probability if match.match_id in match_by_id else 0.33
        probability_b = match_by_id[match.match_id].player_b_win_probability if match.match_id in match_by_id else 0.33
        if outcome == 0:
            upset_value = max(0.0, probability_b - probability_a)
        elif outcome == 2:
            upset_value = max(0.0, probability_a - probability_b)
        else:
            upset_value = 0.0
        if upset_value > 0.0:
            upsets.append((upset_value, f"{match.player_a_name} vs {match.player_b_name}: {_outcome_label(match, outcome)}"))
    upsets.sort(reverse=True)
    key_remaining_matches = [item[1].split(":")[0] for item in upsets[:3]]
    upset_results = [item[1] for item in upsets[:3]]

    summary = (
        f"This outcome appeared in {probability:.1%} of simulations and creates the largest realistic shake-up. "
        f"{champion} wins the league while expected order is heavily disrupted."
    )
    critical_match = key_remaining_matches[0] if key_remaining_matches else "N/A"
    return ScenarioReport(
        scenario_type="chaos",
        scenario_name="😱 Chaos",
        scenario_probability=probability,
        short_description="Maximum upset scenario",
        final_standings=standings,
        remaining_results=remaining_results,
        playoff_teams=playoff_teams,
        champion=champion,
        critical_match=critical_match,
        summary=summary,
        confidence=_clamp(0.25 + probability * 2.5, 0.0, 1.0),
        key_remaining_matches=key_remaining_matches,
        largest_upsets=(upset_results + largest_upsets)[:5],
    )


def build_scenario_cards(scenarios: Sequence[ScenarioReport]) -> List[Dict]:
    return [
        {
            "scenario_type": scenario.scenario_type,
            "scenario_name": scenario.scenario_name,
            "scenario_probability": scenario.scenario_probability,
            "short_description": scenario.short_description,
            "confidence": scenario.confidence,
        }
        for scenario in scenarios
    ]


def build_scenario_report(
    artifacts: SimulationArtifacts | None,
    player_predictions: List[PlayerPrediction],
    match_probabilities: List[MatchProbability],
    critical_matches: List[CriticalMatch],
    playoff_cut: int,
) -> List[ScenarioReport]:
    if artifacts is None or len(player_predictions) == 0 or artifacts.rank_matrix.size == 0:
        return []

    scenarios = [
        build_most_likely_scenario(artifacts, player_predictions, critical_matches, playoff_cut),
        build_bubble_scenario(artifacts, player_predictions, match_probabilities, playoff_cut),
        build_chaos_scenario(artifacts, player_predictions, match_probabilities, playoff_cut),
    ]
    return scenarios
