from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

from prediction.types import CompletedMatchSnapshot, MatchSnapshot


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class FeatureValue:
    feature_name: str
    score: float
    confidence: float
    explanation: str


@dataclass(frozen=True)
class FeatureContext:
    historical_matches: Sequence[CompletedMatchSnapshot]
    target_completed_matches: Sequence[CompletedMatchSnapshot]
    remaining_matches: Sequence[MatchSnapshot]
    player_strength: Dict[str, float]
    deck_strength: Dict[str, float]
    laplace_alpha: float
    league_average_match_rate: float
    league_average_game_rate: float


class FeatureProvider(ABC):
    name: str

    @abstractmethod
    def evaluate(self, context: FeatureContext, match: MatchSnapshot) -> FeatureValue:
        raise NotImplementedError


def _smoothed_rate(success: float, total: float, prior: float, alpha: float) -> float:
    return (success + alpha * prior) / (total + alpha)


def _player_matches(matches: Iterable[CompletedMatchSnapshot], player_id: str) -> List[CompletedMatchSnapshot]:
    return [m for m in matches if m.player_a_id == player_id or m.player_b_id == player_id]


class HistoricalMatchWinRateFeature(FeatureProvider):
    name = "historical_match_win_rate"

    def evaluate(self, context: FeatureContext, match: MatchSnapshot) -> FeatureValue:
        def rate_for(player_id: str) -> tuple[float, int]:
            items = _player_matches(context.historical_matches, player_id)
            score = 0.0
            for item in items:
                if item.player_a_id == player_id:
                    score += 1.0 if item.result == "A" else (0.5 if item.result == "D" else 0.0)
                else:
                    score += 1.0 if item.result == "B" else (0.5 if item.result == "D" else 0.0)
            rate = _smoothed_rate(score, float(len(items)), context.league_average_match_rate, context.laplace_alpha)
            return rate, len(items)

        a_rate, a_n = rate_for(match.player_a_id)
        b_rate, b_n = rate_for(match.player_b_id)
        total = a_n + b_n
        confidence = _clamp(total / 24.0, 0.1, 1.0)
        score = _clamp(a_rate - b_rate, -1.0, 1.0)
        return FeatureValue(self.name, score, confidence, f"Historical match win profile ({a_n} vs {b_n} samples).")


class HistoricalGameWinRateFeature(FeatureProvider):
    name = "historical_game_win_rate"

    def evaluate(self, context: FeatureContext, match: MatchSnapshot) -> FeatureValue:
        def rate_for(player_id: str) -> tuple[float, int]:
            items = _player_matches(context.historical_matches, player_id)
            wins = 0
            games = 0
            for item in items:
                if item.player_a_id == player_id:
                    wins += item.game_wins_a
                else:
                    wins += item.game_wins_b
                games += item.total_games
            rate = _smoothed_rate(float(wins), float(games), context.league_average_game_rate, context.laplace_alpha)
            return rate, games

        a_rate, a_games = rate_for(match.player_a_id)
        b_rate, b_games = rate_for(match.player_b_id)
        confidence = _clamp((a_games + b_games) / 80.0, 0.1, 1.0)
        return FeatureValue(self.name, _clamp(a_rate - b_rate, -1.0, 1.0), confidence, "Historical per-game edge with smoothing.")


class HeadToHeadFeature(FeatureProvider):
    name = "head_to_head"

    def evaluate(self, context: FeatureContext, match: MatchSnapshot) -> FeatureValue:
        relevant = [
            m
            for m in context.historical_matches
            if {m.player_a_id, m.player_b_id} == {match.player_a_id, match.player_b_id}
        ]
        a_score = 0.0
        for item in relevant:
            if item.result == "D":
                a_score += 0.5
            elif (item.result == "A" and item.player_a_id == match.player_a_id) or (item.result == "B" and item.player_b_id == match.player_a_id):
                a_score += 1.0
        rate = _smoothed_rate(a_score, float(len(relevant)), 0.5, context.laplace_alpha)
        score = _clamp((rate - 0.5) * 2.0, -1.0, 1.0)
        confidence = _clamp(len(relevant) / 8.0, 0.15, 1.0)
        return FeatureValue(self.name, score, confidence, "Direct matchup history between both players.")


class DeckMatchupFeature(FeatureProvider):
    name = "deck_matchup"

    def evaluate(self, context: FeatureContext, match: MatchSnapshot) -> FeatureValue:
        relevant = [
            m
            for m in context.historical_matches
            if {m.player_a_deck, m.player_b_deck} == {match.player_a_deck, match.player_b_deck}
        ]
        a_score = 0.0
        for item in relevant:
            if item.result == "D":
                a_score += 0.5
            elif (item.result == "A" and item.player_a_deck == match.player_a_deck) or (item.result == "B" and item.player_b_deck == match.player_a_deck):
                a_score += 1.0
        deck_base = _smoothed_rate(a_score, float(len(relevant)), 0.5, context.laplace_alpha)
        score = _clamp((deck_base - 0.5) * 2.0, -1.0, 1.0)
        confidence = _clamp(len(relevant) / 10.0, 0.1, 1.0)
        return FeatureValue(self.name, score, confidence, "Historical deck-vs-deck pairing results.")


class CurrentFormFeature(FeatureProvider):
    name = "current_form"

    def evaluate(self, context: FeatureContext, match: MatchSnapshot) -> FeatureValue:
        ordered = sorted(context.target_completed_matches, key=lambda m: (m.round_nr, m.round_start_date, m.match_id))

        def recent_form(player_id: str) -> tuple[float, int]:
            recent = [m for m in ordered if m.player_a_id == player_id or m.player_b_id == player_id][-5:]
            if not recent:
                return 0.5, 0
            points = 0.0
            for item in recent:
                if item.player_a_id == player_id:
                    points += item.points_a / 3.0
                else:
                    points += item.points_b / 3.0
            return points / len(recent), len(recent)

        a_form, a_n = recent_form(match.player_a_id)
        b_form, b_n = recent_form(match.player_b_id)
        confidence = _clamp((a_n + b_n) / 10.0, 0.1, 1.0)
        return FeatureValue(self.name, _clamp(a_form - b_form, -1.0, 1.0), confidence, "Recent form over latest league matches.")


class StrengthOfScheduleFeature(FeatureProvider):
    name = "strength_of_schedule"

    def evaluate(self, context: FeatureContext, match: MatchSnapshot) -> FeatureValue:
        def sos_for(player_id: str) -> tuple[float, int]:
            items = _player_matches(context.target_completed_matches, player_id)
            opp_strengths: List[float] = []
            for item in items:
                opponent = item.player_b_id if item.player_a_id == player_id else item.player_a_id
                opp_strengths.append(context.player_strength.get(opponent, 0.5))
            if not opp_strengths:
                return 0.5, 0
            return sum(opp_strengths) / len(opp_strengths), len(opp_strengths)

        a_sos, a_n = sos_for(match.player_a_id)
        b_sos, b_n = sos_for(match.player_b_id)
        confidence = _clamp((a_n + b_n) / 20.0, 0.1, 1.0)
        # Harder schedule so far can indicate stronger underlying level -> positive when A has harder SoS.
        return FeatureValue(self.name, _clamp(a_sos - b_sos, -1.0, 1.0), confidence, "Relative difficulty of schedule already faced.")


class RemainingOpponentStrengthFeature(FeatureProvider):
    name = "remaining_opponent_strength"

    def evaluate(self, context: FeatureContext, match: MatchSnapshot) -> FeatureValue:
        def remaining_strength(player_id: str) -> tuple[float, int]:
            remaining = [m for m in context.remaining_matches if m.player_a_id == player_id or m.player_b_id == player_id]
            if not remaining:
                return 0.5, 0
            values = []
            for item in remaining:
                opponent = item.player_b_id if item.player_a_id == player_id else item.player_a_id
                values.append(context.player_strength.get(opponent, 0.5))
            return sum(values) / len(values), len(values)

        a_rem, a_n = remaining_strength(match.player_a_id)
        b_rem, b_n = remaining_strength(match.player_b_id)
        confidence = _clamp((a_n + b_n) / 20.0, 0.1, 1.0)
        # Easier future path for A -> positive
        return FeatureValue(self.name, _clamp(b_rem - a_rem, -1.0, 1.0), confidence, "Remaining opponent quality differential.")


class FeatureRegistry:
    def __init__(self, providers: Sequence[FeatureProvider]):
        self._providers = list(providers)

    @classmethod
    def default(cls) -> "FeatureRegistry":
        return cls(
            [
                HistoricalMatchWinRateFeature(),
                HistoricalGameWinRateFeature(),
                HeadToHeadFeature(),
                DeckMatchupFeature(),
                CurrentFormFeature(),
                StrengthOfScheduleFeature(),
                RemainingOpponentStrengthFeature(),
            ]
        )

    def evaluate(self, context: FeatureContext, match: MatchSnapshot) -> List[FeatureValue]:
        return [provider.evaluate(context, match) for provider in self._providers]
