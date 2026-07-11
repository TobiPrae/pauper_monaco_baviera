from prediction.probability import ProbabilityEngine
from prediction.features import FeatureValue


def test_probability_engine_normalizes_output():
    engine = ProbabilityEngine(
        feature_weights={"f1": 1.0, "f2": 1.0},
        logistic_scale=3.0,
        min_draw_probability=0.05,
        max_draw_probability=0.25,
        base_draw_rate=0.1,
    )
    result = engine.compute(
        [
            FeatureValue("f1", score=0.4, confidence=0.8, explanation=""),
            FeatureValue("f2", score=-0.1, confidence=0.6, explanation=""),
        ]
    )
    total = result.p_a_win + result.p_draw + result.p_b_win
    assert abs(total - 1.0) < 1e-9
    assert 0.0 <= result.p_a_win <= 1.0
    assert 0.0 <= result.p_draw <= 1.0
    assert 0.0 <= result.p_b_win <= 1.0
