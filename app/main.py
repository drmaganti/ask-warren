from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from warren.cache import CachedDeepAnalysisProvider, CachedEvidenceProvider, CachedMarketDataProvider
from warren.deep import DeterministicDeepAnalysisProvider, GeminiDeepAnalysisProvider, ResilientDeepAnalysisProvider
from warren.engine import Warren
from warren.evidence import (
    AlphaVantageEarningsCallProvider,
    CompositeEvidenceProvider,
    EvidenceRouter,
    ExaWebEvidenceProvider,
    FredMacroEvidenceProvider,
    SecFilingEvidenceProvider,
    SecRagEvidenceProvider,
    YahooEvidenceProvider,
)
from warren.providers import YFinanceMarketDataProvider

from .models import AnalyzeRequest, AnalyzeResponse


def _deep_provider():
    if os.getenv("GEMINI_API_KEY"):
        return CachedDeepAnalysisProvider(
            ResilientDeepAnalysisProvider(
                primary=GeminiDeepAnalysisProvider(),
                fallback=DeterministicDeepAnalysisProvider(),
            ),
            ttl_seconds=1800,
        )
    return DeterministicDeepAnalysisProvider()


def _evidence_providers():
    sec_provider = SecFilingEvidenceProvider()
    if os.getenv("UPSTASH_VECTOR_REST_URL") and os.getenv("UPSTASH_VECTOR_REST_TOKEN"):
        sec_provider = SecRagEvidenceProvider(sec_provider)
    providers = [
        CachedEvidenceProvider(sec_provider, ttl_seconds=21600),
        CachedEvidenceProvider(YahooEvidenceProvider(), ttl_seconds=900),
        CachedEvidenceProvider(FredMacroEvidenceProvider(), ttl_seconds=21600, key=lambda ticker, metrics: "global"),
    ]
    if os.getenv("EXA_API_KEY"):
        providers.append(CachedEvidenceProvider(ExaWebEvidenceProvider(), ttl_seconds=7200))
    if os.getenv("ALPHA_VANTAGE_API_KEY"):
        providers.append(CachedEvidenceProvider(AlphaVantageEarningsCallProvider(), ttl_seconds=604800))
    return providers


raw_evidence = CompositeEvidenceProvider(_evidence_providers())

engine = Warren(
    market_data=CachedMarketDataProvider(YFinanceMarketDataProvider(), ttl_seconds=300),
    deep_analysis=_deep_provider(),
    evidence=EvidenceRouter(raw_evidence),
)

app = FastAPI(
    title="Ask Warren Stock Intelligence",
    version="0.5.0",
    description="Standalone stock research experience powered by the reusable Warren engine.",
)

WEB_DIR = Path(__file__).resolve().parents[1] / "web"


@app.get("/", include_in_schema=False)
def analyze_page() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html", media_type="text/html")


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "warren",
        "deep_provider": "gemini" if os.getenv("GEMINI_API_KEY") else "deterministic-v1.1",
        "evidence_router": EvidenceRouter.VERSION,
        "web_discovery": "exa" if os.getenv("EXA_API_KEY") else "disabled",
        "earnings_calls": "alpha-vantage" if os.getenv("ALPHA_VANTAGE_API_KEY") else "disabled",
        "cache": "persistent-redis" if (
            (os.getenv("UPSTASH_REDIS_REST_URL") and os.getenv("UPSTASH_REDIS_REST_TOKEN"))
            or (os.getenv("KV_REST_API_URL") and os.getenv("KV_REST_API_TOKEN"))
        ) else "memory",
        "rag": "sec-filings-upstash-vector" if (
            os.getenv("UPSTASH_VECTOR_REST_URL") and os.getenv("UPSTASH_VECTOR_REST_TOKEN")
        ) else "disabled",
    }


@app.get("/methodology", include_in_schema=False)
def methodology_page() -> FileResponse:
    return FileResponse(WEB_DIR / "methodology.html", media_type="text/html")


@app.get("/roadmap", include_in_schema=False)
def roadmap_page() -> FileResponse:
    return FileResponse(WEB_DIR / "roadmap.html", media_type="text/html")


@app.post("/v1/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    if request.mode == "screen":
        try:
            result = await engine.screen(
                request.tickers or [],
                top_n=request.top_n,
                min_score=request.min_score,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Screening failed") from exc
        return AnalyzeResponse.model_validate({"mode": "screen", **result.model_dump()})

    try:
        result = await engine.deep(request.ticker or "")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Deep analysis failed") from exc

    return AnalyzeResponse.model_validate({"mode": "deep", **result.model_dump()})
