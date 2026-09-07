from __future__ import annotations

import asyncio

from .models import DeepAnalysis, DeepResponse, DcfResult, EvidenceBundle, MetricSnapshot, ScreenRequest, ScreenResponse, ScreenResult, SourceStatus
from .dcf import calculate_dcf
from .protocols import DeepAnalysisProvider, EvidenceProvider, MarketDataProvider
from .scoring import score_metrics


_IGNORED_MISSING = {"ticker", "company_name", "sector", "industry", "currency"}


def missing_fields(metrics: MetricSnapshot) -> list[str]:
    return [
        field
        for field, value in metrics.model_dump().items()
        if field not in _IGNORED_MISSING and value is None
    ]


def validate_analysis_citations(analysis: DeepAnalysis, evidence: EvidenceBundle) -> DeepAnalysis:
    """Keep only citations that point to a real claim and a real analysis item."""
    valid_claim_ids = {claim.id for claim in evidence.claims}
    section_lengths = {
        "thesis": 1,
        "positives": len(analysis.positives),
        "concerns": len(analysis.concerns),
        "bull_case": len(analysis.bull_case),
        "bear_case": len(analysis.bear_case),
        "risks": len(analysis.risks),
        "what_would_change_view": len(analysis.what_would_change_view),
    }
    cleaned = []
    for citation in analysis.citations:
        if citation.item_index >= section_lengths[citation.section]:
            continue
        claim_ids = list(dict.fromkeys(claim_id for claim_id in citation.claim_ids if claim_id in valid_claim_ids))
        if claim_ids:
            cleaned.append(citation.model_copy(update={"claim_ids": claim_ids}))
    def clean_insights(items):
        return [
            item.model_copy(update={
                "claim_ids": list(dict.fromkeys(
                    claim_id for claim_id in item.claim_ids if claim_id in valid_claim_ids
                ))
            })
            for item in items
        ]

    return analysis.model_copy(update={
        "citations": cleaned,
        "bull_insights": clean_insights(analysis.bull_insights),
        "bear_insights": clean_insights(analysis.bear_insights),
    })


def reconcile_analysis_with_dcf(analysis: DeepAnalysis, dcf: DcfResult) -> DeepAnalysis:
    """Explain material tension between the narrative verdict and deterministic valuation."""
    if dcf.status != "available":
        return analysis
    base = next((item for item in dcf.scenarios if item.name == "base"), None)
    bull = next((item for item in dcf.scenarios if item.name == "bull"), None)
    if not base or base.upside_downside is None or base.upside_downside > -0.30:
        return analysis
    gap = abs(base.upside_downside) * 100
    if analysis.verdict == "watch":
        explanation = (
            f" The base DCF is {gap:.0f}% below the current price, making valuation the main constraint. "
            "The view remains Watch rather than Avoid because DCF is highly assumption-sensitive and the operating evidence is mixed."
        )
    elif analysis.verdict == "attractive" and bull and bull.upside_downside is not None and bull.upside_downside < -0.20:
        explanation = (
            f" The base DCF is {gap:.0f}% below the current price and even the Bull scenario remains below it; "
            "that valuation conflict caps the current view at Watch."
        )
        return analysis.model_copy(update={"thesis": analysis.thesis + explanation, "verdict": "watch"})
    else:
        explanation = f" The base DCF is {gap:.0f}% below the current price, reinforcing valuation risk while remaining sensitive to its assumptions."
    return analysis.model_copy(update={"thesis": analysis.thesis + explanation})


class Warren:
    """Reusable stock-intelligence engine.

    Screen mode is deterministic and LLM-free. Deep mode gathers explicit,
    source-attributed evidence and then runs independent bull, bear and risk
    analysis before final synthesis through the configured DeepAnalysisProvider.
    """

    def __init__(
        self,
        market_data: MarketDataProvider,
        deep_analysis: DeepAnalysisProvider | None = None,
        evidence: EvidenceProvider | None = None,
        screen_concurrency: int = 8,
    ):
        self.market_data = market_data
        self.deep_analysis = deep_analysis
        self.evidence = evidence
        self.screen_concurrency = max(1, screen_concurrency)

    async def screen(
        self,
        tickers: list[str],
        *,
        top_n: int = 25,
        min_score: float = 0,
    ) -> ScreenResponse:
        request = ScreenRequest(tickers=tickers, top_n=top_n, min_score=min_score)
        symbols = list(dict.fromkeys(t.strip().upper() for t in request.tickers if t.strip()))
        semaphore = asyncio.Semaphore(self.screen_concurrency)

        async def one(symbol: str):
            async with semaphore:
                try:
                    metrics = await asyncio.to_thread(self.market_data.fetch_metrics, symbol)
                    scores = score_metrics(metrics)
                    return ScreenResult(
                        ticker=metrics.ticker,
                        company_name=metrics.company_name,
                        sector=metrics.sector,
                        price=metrics.price,
                        scores=scores,
                        missing_data_count=len(missing_fields(metrics)),
                    )
                except Exception:
                    return symbol

        raw = await asyncio.gather(*(one(symbol) for symbol in symbols))
        results = [item for item in raw if isinstance(item, ScreenResult)]
        failures = [item for item in raw if isinstance(item, str)]
        results = [item for item in results if item.scores.overall >= request.min_score]
        results.sort(key=lambda item: item.scores.overall, reverse=True)
        return ScreenResponse(
            screened_count=len(symbols),
            failed_tickers=failures,
            results=results[: request.top_n],
        )

    async def deep(self, ticker: str) -> DeepResponse:
        if self.deep_analysis is None:
            raise RuntimeError("A DeepAnalysisProvider must be configured for deep mode")

        symbol = ticker.strip().upper()
        metrics = await asyncio.to_thread(self.market_data.fetch_metrics, symbol)
        scores = score_metrics(metrics)
        dcf = calculate_dcf(metrics)
        evidence = EvidenceBundle()

        if self.evidence is not None:
            try:
                evidence = await asyncio.to_thread(self.evidence.fetch_evidence, symbol, metrics)
            except Exception as exc:
                evidence.source_status.append(
                    SourceStatus(
                        source=self.evidence.__class__.__name__,
                        status="error",
                        detail=f"{type(exc).__name__}: {exc}",
                    )
                )

        analysis, model = await self.deep_analysis.analyze(metrics, scores, evidence)
        analysis = validate_analysis_citations(analysis, evidence)
        analysis = reconcile_analysis_with_dcf(analysis, dcf)
        return DeepResponse(
            ticker=metrics.ticker,
            metrics=metrics,
            scores=scores,
            dcf=dcf,
            evidence=evidence,
            missing_data=missing_fields(metrics),
            analysis=analysis,
            model=model,
        )
