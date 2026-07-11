from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Dict, List

from prediction.features import FeatureValue
from prediction.types import FeatureContribution


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + exp(-x))


@dataclass(frozen=True)
class MatchProbabilityResult:
    p_a_win: float
    p_draw: float
    p_b_win: float
    baseline_p_a_win: float
    confidence: float
    feature_contributions: List[FeatureContribution]


class ProbabilityEngine:
    def __init__(
        self,
        feature_weights: Dict[str, float],
        logistic_scale: float,
        min_draw_probability: float,
        max_draw_probability: float,
        base_draw_rate: float,
    ):
        self.feature_weights = feature_weights
        self.logistic_scale = logistic_scale
        self.min_draw_probability = min_draw_probability
        self.max_draw_probability = max_draw_probability
        self.base_draw_rate = base_draw_rate

    def compute(self, values: List[FeatureValue]) -> MatchProbabilityResult:
        weighted_numerator = 0.0
        weighted_denominator = 0.0
        confidence_total = 0.0
        contributions: List[FeatureContribution] = []

        for value in values:
            weight = self.feature_weights.get(value.feature_name, 0.0)
            weighted_score = weight * value.score * value.confidence
            contributions.append(
                FeatureContribution(
                    feature_name=value.feature_name,
                    contribution=0.0,
                    confidence=value.confidence,
                    explanation=value.explanation,
                    score=value.score,
                    weighted_score=weighted_score,
                )
            )
            weighted_numerator += weighted_score
            weighted_denominator += abs(weight) * max(value.confidence, 1e-9)
            confidence_total += value.confidence

        aggregate = weighted_numerator / weighted_denominator if weighted_denominator else 0.0
        aggregate = _clamp(aggregate, -1.0, 1.0)
        avg_confidence = confidence_total / len(values) if values else 0.0

        draw_probability = self.base_draw_rate + (0.14 - abs(aggregate) * 0.08)
        draw_probability = _clamp(draw_probability, self.min_draw_probability, self.max_draw_probability)

        baseline_draw_probability = self.base_draw_rate + 0.14
        baseline_draw_probability = _clamp(baseline_draw_probability, self.min_draw_probability, self.max_draw_probability)
        baseline_p_a_win = (1.0 - baseline_draw_probability) * 0.5

        p_a_no_draw = _sigmoid(aggregate * self.logistic_scale)
        p_a_win = (1.0 - draw_probability) * p_a_no_draw
        p_b_win = 1.0 - draw_probability - p_a_win
        p_a_win = _clamp(p_a_win, 0.0, 1.0)
        p_b_win = _clamp(p_b_win, 0.0, 1.0)

        normalizer = p_a_win + draw_probability + p_b_win
        if normalizer <= 0:
            p_a_win, draw_probability, p_b_win = 0.45, 0.1, 0.45
        else:
            p_a_win /= normalizer
            draw_probability /= normalizer
            p_b_win /= normalizer

        return MatchProbabilityResult(
            p_a_win=p_a_win,
            p_draw=draw_probability,
            p_b_win=p_b_win,
            baseline_p_a_win=baseline_p_a_win,
            confidence=_clamp(avg_confidence, 0.0, 1.0),
            feature_contributions=contributions,
        )
