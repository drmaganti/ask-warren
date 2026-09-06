from __future__ import annotations

import pytest

from warren.deep import ResilientDeepAnalysisProvider
from warren.models import CategoryScores, DeepAnalysis, EvidenceBundle, MetricSnapshot


class FailingProvider:
    async def analyze(self, metrics, scores, evidence):
        raise RuntimeError("quota exhausted")


class FallbackProvider:
    async def analyze(self, metrics, scores, evidence):
        return (
            DeepAnalysis(
                thesis="Fallback thesis",
                positives=["positive"],
                concerns=["concern"],
                bull_case=["bull"],
                bear_case=["bear"],
                risks=["risk"],
                what_would_change_view=["change"],
                verdict="watch",
                confidence="medium",
            ),
            "fallback-model",
        )


@pytest.mark.asyncio
async def test_resilient_provider_uses_fallback_and_reports_degradation():
    provider = ResilientDeepAnalysisProvider(FailingProvider(), FallbackProvider())
    evidence = EvidenceBundle()
    scores = CategoryScores(
        fundamentals=50,
        valuation=50,
        business_quality=50,
        growth=50,
        risk_resilience=50,
        market_context=50,
        overall=50,
    )

    analysis, model = await provider.analyze(MetricSnapshot(ticker="TEST"), scores, evidence)

    assert analysis.thesis == "Fallback thesis"
    assert model == "fallback-model"
    assert evidence.source_status[-1].status == "partial"
    assert "deterministic fallback" in (evidence.source_status[-1].detail or "")
