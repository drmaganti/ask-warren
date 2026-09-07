from __future__ import annotations

import pytest
import httpx

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
    assert "unexpected provider error" in (evidence.source_status[-1].detail or "")


class HttpFailingProvider:
    def __init__(self, status_code):
        self.status_code = status_code

    async def analyze(self, metrics, scores, evidence):
        request = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/test:generateContent")
        response = httpx.Response(self.status_code, request=request)
        raise httpx.HTTPStatusError("provider request failed", request=request, response=response)


@pytest.mark.asyncio
@pytest.mark.parametrize(("status_code", "category"), [
    (400, "invalid provider request"),
    (401, "provider authentication failed"),
    (403, "provider permission or quota access denied"),
    (404, "configured model or endpoint unavailable"),
    (429, "provider rate or quota limit reached"),
    (503, "temporary provider service failure"),
])
async def test_resilient_provider_reports_safe_http_failure_category(status_code, category, caplog):
    provider = ResilientDeepAnalysisProvider(HttpFailingProvider(status_code), FallbackProvider())
    evidence = EvidenceBundle()
    scores = CategoryScores(
        fundamentals=50, valuation=50, business_quality=50, growth=50,
        risk_resilience=50, market_context=50, overall=50,
    )

    with caplog.at_level("WARNING"):
        await provider.analyze(MetricSnapshot(ticker="SAFE"), scores, evidence)

    detail = evidence.source_status[-1].detail or ""
    assert category in detail
    assert f"HTTP {status_code}" in detail
    assert "generativelanguage.googleapis.com" not in detail
    assert '"event":"deep_analysis_fallback"' in caplog.text
    assert f'"http_status":{status_code}' in caplog.text
