from warren.models import MetricSnapshot
from warren.scoring import _higher, _lower, score_metrics


def test_band_scores_interpolate_between_thresholds():
    assert _lower(26, [(22, 82), (30, 68)]) == 75.0
    assert _higher(0.10, [(0.12, 95), (0.08, 85)]) == 90.0


def test_exact_threshold_scores_are_preserved():
    assert _lower(30, [(22, 82), (30, 68), (40, 50)]) == 68.0
    assert _higher(0.08, [(0.12, 95), (0.08, 85), (0.05, 70)]) == 85.0


def test_nearby_company_metrics_produce_distinct_category_scores():
    first = score_metrics(MetricSnapshot(ticker="FIRST", trailing_pe=26, forward_pe=24, peg_ratio=1.7))
    second = score_metrics(MetricSnapshot(ticker="SECOND", trailing_pe=29, forward_pe=28, peg_ratio=1.9))

    assert first.valuation != second.valuation
    assert first.valuation > second.valuation
