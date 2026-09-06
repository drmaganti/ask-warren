from __future__ import annotations

import pytest

from warren.deep import DeterministicDeepAnalysisProvider
from warren.models import CategoryScores, EvidenceBundle, MetricComparison, MetricSnapshot, SourceStatus


@pytest.mark.asyncio
async def test_deterministic_provider_returns_public_verdict_vocabulary():
    provider = DeterministicDeepAnalysisProvider()
    metrics = MetricSnapshot(
        ticker="TEST",
        company_name="Test Co",
        market_cap=100_000_000_000,
        free_cash_flow=7_000_000_000,
        operating_cash_flow=9_000_000_000,
        trailing_pe=20,
        forward_pe=18,
        revenue_growth=0.12,
        earnings_growth=0.14,
        operating_margin=0.22,
        return_on_equity=0.24,
        debt_to_equity=40,
        current_ratio=1.5,
        quarterly_comparisons=[
            MetricComparison(
                metric="quarterly_operating_margin",
                label="Quarterly operating margin",
                unit="percent",
                current=0.22,
                previous_quarter=0.20,
                year_ago=0.18,
            )
        ],
    )
    scores = CategoryScores(
        fundamentals=80,
        valuation=75,
        business_quality=82,
        growth=76,
        risk_resilience=72,
        market_context=65,
        overall=78,
    )
    evidence = EvidenceBundle(source_status=[SourceStatus(source="Yahoo Finance", status="ok")])

    analysis, model = await provider.analyze(metrics, scores, evidence)

    assert analysis.verdict == "attractive"
    assert analysis.confidence in {"low", "medium", "high"}
    assert analysis.thesis
    assert analysis.bull_case
    assert any("Inputs:" in item for item in analysis.bull_case)
    assert any("operating margin 22.0%" in item for item in analysis.bull_case)
    assert any("2.0 percentage points above last quarter" in item for item in analysis.bull_case)
    assert any("4.0 percentage points above the same quarter last year" in item for item in analysis.bull_case)
    assert analysis.bear_case
    assert model == "deterministic-v1.1"
