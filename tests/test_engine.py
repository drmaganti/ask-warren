from __future__ import annotations

import pytest

from warren.engine import Warren
from warren.models import (
    AnalysisCitation,
    CategoryScores,
    DeepAnalysis,
    EvidenceBundle,
    EvidenceClaim,
    InvestmentInsight,
    MetricSnapshot,
    NewsEvidence,
    SourceStatus,
)


class FakeMarketData:
    def __init__(self):
        self.calls: list[str] = []

    def fetch_metrics(self, ticker: str) -> MetricSnapshot:
        self.calls.append(ticker)
        if ticker == "FAIL":
            raise RuntimeError("provider failure")
        quality = 0.25 if ticker == "GOOD" else 0.08
        return MetricSnapshot(
            ticker=ticker,
            company_name=ticker,
            price=100,
            market_cap=1_000_000_000,
            trailing_pe=18 if ticker == "GOOD" else 45,
            forward_pe=17 if ticker == "GOOD" else 40,
            peg_ratio=1.2 if ticker == "GOOD" else 3.5,
            enterprise_to_ebitda=12 if ticker == "GOOD" else 28,
            free_cash_flow=100_000_000 if ticker == "GOOD" else -10_000_000,
            operating_cash_flow=120_000_000 if ticker == "GOOD" else -5_000_000,
            revenue_growth=0.20 if ticker == "GOOD" else 0.02,
            earnings_growth=0.18 if ticker == "GOOD" else -0.05,
            gross_margin=0.55 if ticker == "GOOD" else 0.18,
            operating_margin=0.22 if ticker == "GOOD" else 0.02,
            profit_margin=0.16 if ticker == "GOOD" else -0.02,
            return_on_equity=quality,
            return_on_assets=0.10 if ticker == "GOOD" else 0.01,
            debt_to_equity=40 if ticker == "GOOD" else 180,
            current_ratio=1.8 if ticker == "GOOD" else 0.8,
            beta=1.0,
            fifty_two_week_high=110,
            fifty_two_week_low=70,
            fifty_day_average=98,
            two_hundred_day_average=90,
        )


class FakeEvidence:
    def __init__(self, fail: bool = False):
        self.calls = 0
        self.fail = fail

    def fetch_evidence(self, ticker: str, metrics: MetricSnapshot) -> EvidenceBundle:
        self.calls += 1
        if self.fail:
            raise RuntimeError("evidence unavailable")
        return EvidenceBundle(
            news=[NewsEvidence(title="Test headline", publisher="Test Publisher")],
            claims=[
                EvidenceClaim(
                    id="claim-real",
                    category="news",
                    claim="Test headline",
                    authority_tier=4,
                    retrieval_depth="headline",
                    confidence="low",
                )
            ],
            source_status=[SourceStatus(source="fake", status="ok")],
        )


class FakeDeepAnalysis:
    def __init__(self):
        self.calls = 0
        self.last_evidence: EvidenceBundle | None = None

    async def analyze(
        self,
        metrics: MetricSnapshot,
        scores: CategoryScores,
        evidence: EvidenceBundle,
    ):
        self.calls += 1
        self.last_evidence = evidence
        return (
            DeepAnalysis(
                thesis="Test thesis",
                positives=["positive"],
                concerns=["concern"],
                bull_case=["bull"],
                bear_case=["bear"],
                risks=["risk"],
                what_would_change_view=["change"],
                verdict="Test verdict",
                confidence="medium",
                citations=[
                    AnalysisCitation(section="thesis", item_index=0, claim_ids=["claim-real", "invented"]),
                    AnalysisCitation(section="bull_case", item_index=5, claim_ids=["claim-real"]),
                ],
                bull_insights=[InvestmentInsight(
                    headline="Test insight",
                    finding="Supported finding",
                    cause="Supported cause",
                    durability="recurring",
                    time_horizon="medium_term",
                    investor_implication="Future implication",
                    what_to_watch=["Observable signal"],
                    confidence="medium",
                    claim_ids=["claim-real", "invented"],
                )],
            ),
            "fake-model",
        )


@pytest.mark.asyncio
async def test_screen_ranks_without_calling_deep_or_evidence_provider():
    market = FakeMarketData()
    deep = FakeDeepAnalysis()
    evidence = FakeEvidence()
    warren = Warren(market_data=market, deep_analysis=deep, evidence=evidence)

    response = await warren.screen(["WEAK", "GOOD"])

    assert response.screened_count == 2
    assert [item.ticker for item in response.results] == ["GOOD", "WEAK"]
    assert deep.calls == 0
    assert evidence.calls == 0


@pytest.mark.asyncio
async def test_screen_deduplicates_and_isolates_failures():
    warren = Warren(market_data=FakeMarketData())

    response = await warren.screen(["GOOD", "GOOD", "FAIL", "WEAK"])

    assert response.screened_count == 3
    assert response.failed_tickers == ["FAIL"]
    assert {item.ticker for item in response.results} == {"GOOD", "WEAK"}


@pytest.mark.asyncio
async def test_deep_collects_and_passes_evidence_once():
    market = FakeMarketData()
    evidence = FakeEvidence()
    deep = FakeDeepAnalysis()
    warren = Warren(market_data=market, deep_analysis=deep, evidence=evidence)

    response = await warren.deep("GOOD")

    assert response.ticker == "GOOD"
    assert response.analysis.verdict == "Test verdict"
    assert response.model == "fake-model"
    assert evidence.calls == 1
    assert deep.calls == 1
    assert response.evidence.news[0].title == "Test headline"
    assert deep.last_evidence is not None
    assert deep.last_evidence.news[0].title == "Test headline"
    assert len(response.analysis.citations) == 1
    assert response.analysis.citations[0].claim_ids == ["claim-real"]
    assert response.analysis.bull_insights[0].claim_ids == ["claim-real"]


@pytest.mark.asyncio
async def test_deep_degrades_when_evidence_provider_fails():
    deep = FakeDeepAnalysis()
    warren = Warren(market_data=FakeMarketData(), deep_analysis=deep, evidence=FakeEvidence(fail=True))

    response = await warren.deep("GOOD")

    assert response.analysis.verdict == "Test verdict"
    assert response.evidence.source_status[0].status == "error"
    assert deep.calls == 1


@pytest.mark.asyncio
async def test_deep_requires_provider():
    warren = Warren(market_data=FakeMarketData())

    with pytest.raises(RuntimeError, match="DeepAnalysisProvider"):
        await warren.deep("GOOD")


@pytest.mark.asyncio
async def test_min_score_filters_results():
    warren = Warren(market_data=FakeMarketData())

    baseline = await warren.screen(["GOOD", "WEAK"])
    good_score = baseline.results[0].scores.overall
    weak_score = baseline.results[1].scores.overall
    threshold = (good_score + weak_score) / 2

    filtered = await warren.screen(["GOOD", "WEAK"], min_score=threshold)

    assert [item.ticker for item in filtered.results] == ["GOOD"]
