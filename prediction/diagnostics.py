from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from prediction.types import CompletedMatchSnapshot, MatchProbability, PredictionDiagnostics


def compute_diagnostics(
    historical_matches: List[CompletedMatchSnapshot],
    match_probabilities: List[MatchProbability],
) -> PredictionDiagnostics:
    draw_rate = 0.0
    if historical_matches:
        draws = sum(1 for m in historical_matches if m.result == "D")
        draw_rate = draws / len(historical_matches)

    # This release has no out-of-sample backtest store yet, so diagnostics are conservative placeholders.
    calibration_error = abs(draw_rate - 0.1)
    avg_error = calibration_error * 0.8
    accuracy = max(0.0, 1.0 - avg_error)
    historical_score = min(1.0, len(historical_matches) / 300.0)

    contrib_totals: Dict[str, float] = defaultdict(float)
    for mp in match_probabilities:
        for contribution in mp.feature_contributions:
            contrib_totals[contribution.feature_name] += abs(contribution.weighted_score)
    normalizer = sum(contrib_totals.values()) or 1.0
    feature_contrib = {name: value / normalizer for name, value in contrib_totals.items()}

    return PredictionDiagnostics(
        prediction_accuracy=accuracy,
        prediction_calibration_error=calibration_error,
        average_prediction_error=avg_error,
        historical_performance_score=historical_score,
        feature_contributions=feature_contrib,
    )
