from __future__ import annotations

import pytest

from warren.cache import (
    CachedDeepAnalysisProvider,
    CachedEvidenceProvider,
    CachedMarketDataProvider,
    PersistentTTLCache,
)
from warren.models import CategoryScores, DeepAnalysis, EvidenceBundle, MetricSnapshot


class CountingMarket:
    def __init__(self):
        self.calls = 0

    def fetch_metrics(self, ticker: str) -> MetricSnapshot:
        self.calls += 1
        return MetricSnapshot(ticker=ticker, price=100)


class CountingEvidence:
    def __init__(self):
        self.calls = 0

    def fetch_evidence(self, ticker: str, metrics: MetricSnapshot) -> EvidenceBundle:
        self.calls += 1
        return EvidenceBundle(evidence_version="same")


class CountingDeep:
    def __init__(self):
        self.calls = 0

    async def analyze(self, metrics, scores, evidence):
        self.calls += 1
        return (
            DeepAnalysis(
                thesis="cached",
                positives=["p"],
                concerns=["c"],
                bull_case=["b"],
                bear_case=["b"],
                risks=["r"],
                what_would_change_view=["w"],
                verdict="watch",
                confidence="medium",
            ),
            "test-model",
        )


class FallbackDeep(CountingDeep):
    async def analyze(self, metrics, scores, evidence):
        analysis, _ = await super().analyze(metrics, scores, evidence)
        return analysis, "deterministic-v1.1"


class FakeRedisStore:
    def __init__(self):
        self.items = {}

    def get(self, key):
        return self.items.get(key)

    def set(self, key, value, ttl_seconds):
        self.items[key] = value


def test_market_data_cache_normalizes_ticker_and_copies_values():
    upstream = CountingMarket()
    cached = CachedMarketDataProvider(upstream, ttl_seconds=60)

    first = cached.fetch_metrics(" aapl ")
    first.price = 1
    second = cached.fetch_metrics("AAPL")

    assert upstream.calls == 1
    assert second.price == 100


def test_global_evidence_cache_reuses_one_result_across_tickers():
    upstream = CountingEvidence()
    cached = CachedEvidenceProvider(upstream, ttl_seconds=60, key=lambda ticker, metrics: "global")

    cached.fetch_evidence("AAPL", MetricSnapshot(ticker="AAPL"))
    cached.fetch_evidence("MSFT", MetricSnapshot(ticker="MSFT"))

    assert upstream.calls == 1


@pytest.mark.asyncio
async def test_deep_cache_reuses_analysis_for_unchanged_inputs():
    upstream = CountingDeep()
    cached = CachedDeepAnalysisProvider(upstream, ttl_seconds=60)
    metrics = MetricSnapshot(ticker="AAPL", price=100)
    scores = CategoryScores(
        fundamentals=50,
        valuation=50,
        business_quality=50,
        growth=50,
        risk_resilience=50,
        market_context=50,
        overall=50,
    )
    evidence = EvidenceBundle(evidence_version="same")

    first = await cached.analyze(metrics, scores, evidence)
    second = await cached.analyze(metrics, scores, evidence)

    assert first == second
    assert upstream.calls == 1


@pytest.mark.asyncio
async def test_deep_cache_does_not_preserve_degraded_fallback():
    upstream = FallbackDeep()
    cached = CachedDeepAnalysisProvider(upstream, ttl_seconds=60)
    metrics = MetricSnapshot(ticker="AAPL", price=100)
    scores = CategoryScores(
        fundamentals=50,
        valuation=50,
        business_quality=50,
        growth=50,
        risk_resilience=50,
        market_context=50,
        overall=50,
    )
    evidence = EvidenceBundle(evidence_version="same")

    await cached.analyze(metrics, scores, evidence)
    await cached.analyze(metrics, scores, evidence)

    assert upstream.calls == 2


def test_persistent_cache_survives_a_new_application_instance():
    store = FakeRedisStore()
    first = PersistentTTLCache(
        "test", 60, lambda value: value, lambda value: value, store=store
    )
    first.set("AAPL", {"price": 100})

    second = PersistentTTLCache(
        "test", 60, lambda value: value, lambda value: value, store=store
    )

    assert second.get("AAPL") == {"price": 100}
    assert list(store.items) == ["ask-warren:v1:test:AAPL:fresh"]
