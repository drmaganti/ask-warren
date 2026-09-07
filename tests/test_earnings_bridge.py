from datetime import date

from warren.deep import DeterministicDeepAnalysisProvider
from warren.deep.drivers import earnings_bridge
from warren.models import EvidenceBundle, MetricComparison, MetricSnapshot


def snapshot():
    return MetricSnapshot(ticker="TEST", quarterly_comparisons=[
        MetricComparison(metric="quarterly_" + name, label=name, unit="money",
                         current=current, year_ago=prior,
                         current_period=date(2026, 6, 30), year_ago_period=date(2025, 6, 30))
        for name, current, prior in [
            ("operating_income", 110, 100), ("pretax_income", 170, 90),
            ("tax_provision", 40, 30), ("net_income", 125, 60)
        ]
    ])


def test_bridge_separates_nonoperating_gain_and_tax_expense_from_operations():
    result = earnings_bridge(snapshot())
    assert result["operating_income_change"] == 10
    assert result["below_operating_income_change"] == 70
    assert result["tax_expense_effect"] == -10
    assert result["net_income_change"] == 65
    assert result["unreconciled_change"] == -5


def test_bridge_refuses_missing_or_mismatched_comparisons():
    data = snapshot()
    data.quarterly_comparisons[0].year_ago_period = date(2025, 3, 31)
    assert earnings_bridge(data)["status"] == "unavailable"
    data.quarterly_comparisons.pop()
    assert earnings_bridge(data)["status"] == "unavailable"


def test_investor_copy_interprets_bridge_without_exposing_raw_diagnostics():
    data = snapshot()
    data.revenue_growth = -0.01
    data.earnings_growth = 0.20

    _, bear = DeterministicDeepAnalysisProvider._structured_insights(
        data, EvidenceBundle(), [], []
    )

    insight = next(item for item in bear if item.headline == "Profit growth is running ahead of sales growth")
    assert "below operating income rather than in the core business" in insight.cause
    assert "unreconciled difference" not in insight.cause.lower()
    assert "$" not in insight.cause
