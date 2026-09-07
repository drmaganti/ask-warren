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


@pytest.mark.asyncio
async def test_deterministic_provider_can_surface_six_strong_reasons_per_side():
    provider = DeterministicDeepAnalysisProvider()
    metrics = MetricSnapshot(
        ticker="COST",
        price=915,
        market_cap=406_000_000_000,
        free_cash_flow=6_950_000_000,
        operating_cash_flow=15_000_000_000,
        total_cash=11_100_000_000,
        total_debt=10_200_000_000,
        trailing_pe=46,
        forward_pe=40,
        revenue_growth=.215,
        earnings_growth=.455,
        operating_margin=.04,
        profit_margin=.03,
        return_on_assets=.087,
        analyst_target_low=700,
        analyst_target_median=900,
        analyst_target_high=1200,
        analyst_opinion_count=30,
        quarterly_comparisons=[
            MetricComparison(metric="quarterly_operating_margin", label="Operating margin", unit="percent", current=.04, previous_quarter=.037, year_ago=.039),
            MetricComparison(metric="quarterly_capital_expenditure", label="Capital expenditure", unit="money", current=-1_400_000_000, year_ago=-1_100_000_000),
        ],
    )
    scores = CategoryScores(fundamentals=73, valuation=29, business_quality=68, growth=90, risk_resilience=75, market_context=62, overall=62)
    evidence = EvidenceBundle(
        estimate_revisions=[EstimateRevisionEvidence(horizon="0y", analyst_count=30, earnings_growth=.13, revenue_growth=.09)],
        technical=[TechnicalEvidence(close=915, sma_50=943, sma_200=960, rsi_14=37)],
        claims=[EvidenceClaim(id="estimate_revision:cost", category="estimate_revision", claim="Consensus growth", authority_tier=2, retrieval_depth="structured", confidence="high", references=[EvidenceReference(source="Yahoo Finance", authority_tier=2, retrieval_depth="structured")], metadata={"horizon":"0y"})],
    )

    analysis, _ = await provider.analyze(metrics, scores, evidence)

    assert len(analysis.bull_insights) >= 6
    assert len(analysis.bear_insights) >= 6


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


def test_fallback_produces_multiple_supported_insights_when_model_is_unavailable():
    metrics = MetricSnapshot(
        ticker="COST",
        free_cash_flow=6_900_000_000,
        trailing_pe=46,
        forward_pe=40,
        revenue_growth=0.21,
        earnings_growth=0.45,
        quarterly_comparisons=[MetricComparison(
            metric="quarterly_operating_margin",
            label="Quarterly operating margin",
            unit="percent",
            current=0.038,
            year_ago=0.035,
        )],
    )
    claim = EvidenceClaim(
        id="estimate_revision:cost",
        category="estimate_revision",
        claim="Consensus expects annual revenue and earnings growth.",
        authority_tier=2,
        retrieval_depth="structured",
        confidence="high",
        references=[EvidenceReference(source="Yahoo Finance", authority_tier=2, retrieval_depth="structured")],
        metadata={"horizon": "0y"},
    )
    evidence = EvidenceBundle(
        estimate_revisions=[EstimateRevisionEvidence(
            horizon="0y",
            eps_current=20.58,
            eps_30d_ago=20.59,
            earnings_growth=0.13,
            revenue_growth=0.096,
        )],
        technical=[TechnicalEvidence(
            close=916,
            sma_50=944,
            sma_200=960,
            rsi_14=37.5,
        )],
        claims=[claim],
    )
    forward_support, forward_caution = DeterministicDeepAnalysisProvider._forward_estimate_context(evidence)

    bull, bear = DeterministicDeepAnalysisProvider._structured_insights(
        metrics, evidence, forward_support, forward_caution
    )

    assert len(bull) >= 3
    assert {item.lens for item in bull} >= {"future_demand", "operating_leverage", "capital_allocation"}
    assert len(bear) >= 2
    assert {item.lens for item in bear} >= {"market_expectations", "market_positioning"}
