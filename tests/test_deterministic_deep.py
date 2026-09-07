from __future__ import annotations

import pytest

from warren.deep import DeterministicDeepAnalysisProvider
from warren.models import (
    CategoryScores,
    EstimateRevisionEvidence,
    EvidenceBundle,
    EvidenceClaim,
    EvidenceReference,
    MetricComparison,
    MetricSnapshot,
    SourceStatus,
    TechnicalEvidence,
)


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
    estimate_claim = EvidenceClaim(
        id="estimate_revision:test",
        category="estimate_revision",
        claim="Current-year consensus estimates increased.",
        authority_tier=2,
        retrieval_depth="structured",
        confidence="high",
        references=[EvidenceReference(source="Yahoo Finance", authority_tier=2, retrieval_depth="structured")],
        metadata={"horizon": "0y"},
    )
    evidence = EvidenceBundle(
        estimate_revisions=[EstimateRevisionEvidence(
            horizon="0y",
            analyst_count=20,
            eps_current=5.50,
            eps_30d_ago=5.00,
            eps_up_30d=12,
            eps_down_30d=1,
            earnings_growth=0.14,
            revenue_growth=-0.02,
        )],
        claims=[estimate_claim],
        source_status=[SourceStatus(source="Yahoo Finance", status="ok")],
    )

    analysis, model = await provider.analyze(metrics, scores, evidence)

    assert analysis.verdict == "attractive"
    assert analysis.confidence in {"low", "medium", "high"}
    assert analysis.thesis
    assert analysis.bull_case
    assert any("operating margin 22.0%" in item for item in analysis.bull_case)
    assert any("2.0 percentage points above last quarter" in item for item in analysis.bull_case)
    assert any("4.0 percentage points above the same quarter last year" in item for item in analysis.bull_case)
    assert all("scores " not in item.lower() for item in analysis.bull_case + analysis.bear_case)
    assert all("above average" not in item.lower() for item in analysis.bull_case + analysis.bear_case)
    assert any("Why it matters:" in item for item in analysis.bull_case)
    assert any("Earnings expectations are improving" in item for item in analysis.bull_case)
    assert any("Revenue expectations are contracting" in item for item in analysis.bear_case)
    assert {citation.section for citation in analysis.citations} == {"bull_case", "bear_case"}
    assert "/100" not in analysis.thesis
    assert analysis.bear_case
    assert analysis.bull_insights
    assert analysis.bear_insights
    assert all(item.investor_implication for item in analysis.bull_insights + analysis.bear_insights)
    assert all(item.what_to_watch for item in analysis.bull_insights + analysis.bear_insights)
    assert all(item.time_horizon != "unresolved" for item in analysis.bull_insights + analysis.bear_insights)
    assert any("future" in item.investor_implication.lower() for item in analysis.bull_insights)
    assert any(item.impact == "high" for item in analysis.bear_insights)
    assert model == "deterministic-v1.3-ranked-lenses"


def test_structured_insights_surface_valuation_and_stretched_trading_when_material():
    metrics = MetricSnapshot(
        ticker="NVDA",
        trailing_pe=55,
        forward_pe=45,
        revenue_growth=0.50,
        earnings_growth=0.60,
    )
    evidence = EvidenceBundle(technical=[TechnicalEvidence(
        close=150,
        sma_50=120,
        sma_200=90,
        rsi_14=76,
        latest_volume=200_000_000,
        avg_volume_20=100_000_000,
    )])

    _, bear = DeterministicDeepAnalysisProvider._structured_insights(
        metrics, evidence, [], []
    )

    assert len(bear) <= 4
    assert {item.lens for item in bear} >= {"market_expectations", "market_positioning"}
    positioning = next(item for item in bear if item.lens == "market_positioning")
    assert positioning.headline == "Trading enthusiasm looks stretched"
    assert "76.0" in positioning.finding
    assert "25.0% above its 50-day average" in positioning.finding
    assert "2.0x its 20-day average" in positioning.finding
    assert positioning.expectation_gap
    assert positioning.scenario_path
