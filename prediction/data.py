from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from models import compute_match_summary
from prediction.types import CompletedMatchSnapshot, MatchSnapshot, PlayerSnapshot


@dataclass(frozen=True)
class LeaguePredictionDataset:
    league_id: str
    league_name: str
    league_nr: int
    players: List[PlayerSnapshot]
    completed_target_matches: List[CompletedMatchSnapshot]
    remaining_target_matches: List[MatchSnapshot]
    historical_completed_matches: List[CompletedMatchSnapshot]
    current_standings: List[Dict]


def _safe_round_nr(round_obj) -> int:
    nr = getattr(round_obj, "nr", 0)
    return nr if isinstance(nr, int) else 0


def _build_completed_match_snapshot(match, round_obj, users_by_id: Dict[str, str], player_decks: Dict[str, str], match_id: str) -> CompletedMatchSnapshot:
    summary = compute_match_summary(match)
    return CompletedMatchSnapshot(
        match_id=match_id,
        round_id=str(getattr(match, "round_id", "")),
        round_nr=_safe_round_nr(round_obj),
        round_start_date=getattr(round_obj, "start_date", "") or "",
        player_a_id=match.player_a,
        player_a_name=users_by_id.get(match.player_a, f"Player {match.player_a}"),
        player_a_deck=player_decks.get(match.player_a, "No Deck"),
        player_b_id=match.player_b,
        player_b_name=users_by_id.get(match.player_b, f"Player {match.player_b}"),
        player_b_deck=player_decks.get(match.player_b, "No Deck"),
        match_type=getattr(match, "match_type", "Round"),
        result=summary["match_result"],
        points_a=summary["points_a"],
        points_b=summary["points_b"],
        game_wins_a=summary["player_a_game_wins"],
        game_wins_b=summary["player_b_game_wins"],
        total_games=summary["total_games_played"],
    )


def _build_remaining_match_snapshot(match, round_obj, users_by_id: Dict[str, str], player_decks: Dict[str, str], match_id: str) -> MatchSnapshot:
    return MatchSnapshot(
        match_id=match_id,
        round_id=str(getattr(match, "round_id", "")),
        round_nr=_safe_round_nr(round_obj),
        round_start_date=getattr(round_obj, "start_date", "") or "",
        player_a_id=match.player_a,
        player_a_name=users_by_id.get(match.player_a, f"Player {match.player_a}"),
        player_a_deck=player_decks.get(match.player_a, "No Deck"),
        player_b_id=match.player_b,
        player_b_name=users_by_id.get(match.player_b, f"Player {match.player_b}"),
        player_b_deck=player_decks.get(match.player_b, "No Deck"),
        match_type=getattr(match, "match_type", "Round"),
    )


def _compute_current_standings(players: List[PlayerSnapshot], completed_matches: List[CompletedMatchSnapshot]) -> List[Dict]:
    stats = {
        p.player_id: {
            "player_name": p.player_name,
            "deck_name": p.deck_name,
            "points": 0,
            "match_wins": 0,
            "match_losses": 0,
            "match_draws": 0,
            "game_wins": 0,
            "total_games": 0,
        }
        for p in players
    }
    for match in completed_matches:
        a = stats[match.player_a_id]
        b = stats[match.player_b_id]
        a["points"] += match.points_a
        b["points"] += match.points_b
        a["game_wins"] += match.game_wins_a
        b["game_wins"] += match.game_wins_b
        a["total_games"] += match.total_games
        b["total_games"] += match.total_games
        if match.result == "A":
            a["match_wins"] += 1
            b["match_losses"] += 1
        elif match.result == "B":
            b["match_wins"] += 1
            a["match_losses"] += 1
        else:
            a["match_draws"] += 1
            b["match_draws"] += 1
    rows: List[Dict] = []
    for player_id, row in stats.items():
        gwr = (row["game_wins"] / row["total_games"]) if row["total_games"] else 0.0
        rows.append(
            {
                "player_id": player_id,
                "player_name": row["player_name"],
                "deck_name": row["deck_name"],
                "points": row["points"],
                "game_wins": row["game_wins"],
                "total_games": row["total_games"],
                "game_win_rate": gwr,
                "points_plus": row["points"] + gwr,
                "match_wins": row["match_wins"],
                "match_losses": row["match_losses"],
                "match_draws": row["match_draws"],
            }
        )
    rows.sort(key=lambda r: (r["points"], r["game_win_rate"], r["player_name"]), reverse=True)
    for idx, row in enumerate(rows, start=1):
        row["rank"] = idx
    return rows


def build_prediction_dataset(client, selected_league) -> LeaguePredictionDataset:
    all_users = client.list_users()
    users_by_id = {u.id: u.username for u in all_users}
    all_decks = client.list_decks()
    decks_by_id = {d.id: d.deck_name for d in all_decks}
    all_matches = client.list_matches()
    all_leagues = client.list_leagues()

    rounds = client.list_rounds(selected_league.id)
    rounds_by_id = {r.id: r for r in rounds}
    round_ids = set(rounds_by_id.keys())

    memberships = client.list_league_players(selected_league.id)
    player_decks = {m.user_id: decks_by_id.get(m.deck_id, "No Deck") for m in memberships}
    players = [
        PlayerSnapshot(player_id=member.user_id, player_name=users_by_id.get(member.user_id, f"Player {member.user_id}"), deck_name=player_decks.get(member.user_id, "No Deck"))
        for member in memberships
    ]

    completed_target_matches: List[CompletedMatchSnapshot] = []
    remaining_target_matches: List[MatchSnapshot] = []
    for match in all_matches:
        if getattr(match, "match_type", "Round") != "Round":
            continue
        rid = getattr(match, "round_id", None)
        if rid not in round_ids:
            continue
        round_obj = rounds_by_id.get(rid)
        match_id = str(match.id)
        summary = compute_match_summary(match)
        if summary["total_games_played"] > 0:
            completed_target_matches.append(_build_completed_match_snapshot(match, round_obj, users_by_id, player_decks, match_id))
        else:
            remaining_target_matches.append(_build_remaining_match_snapshot(match, round_obj, users_by_id, player_decks, match_id))

    historical_completed_matches: List[CompletedMatchSnapshot] = []
    for league in all_leagues:
        rounds_hist = client.list_rounds(league.id)
        rounds_hist_by_id = {r.id: r for r in rounds_hist}
        hist_round_ids = set(rounds_hist_by_id.keys())
        memberships_hist = client.list_league_players(league.id)
        hist_player_decks = {m.user_id: decks_by_id.get(m.deck_id, "No Deck") for m in memberships_hist}

        for match in all_matches:
            if getattr(match, "match_type", "Round") != "Round":
                continue
            rid = getattr(match, "round_id", None)
            if rid not in hist_round_ids:
                continue
            summary = compute_match_summary(match)
            if summary["total_games_played"] == 0:
                continue
            round_obj = rounds_hist_by_id.get(rid)
            historical_completed_matches.append(_build_completed_match_snapshot(match, round_obj, users_by_id, hist_player_decks, str(match.id)))

    current_standings = _compute_current_standings(players, completed_target_matches)
    remaining_target_matches.sort(key=lambda m: (m.round_nr, m.player_a_name, m.player_b_name))
    return LeaguePredictionDataset(
        league_id=selected_league.id,
        league_name=selected_league.league_name or f"League {selected_league.nr}",
        league_nr=selected_league.nr,
        players=players,
        completed_target_matches=completed_target_matches,
        remaining_target_matches=remaining_target_matches,
        historical_completed_matches=historical_completed_matches,
        current_standings=current_standings,
    )
