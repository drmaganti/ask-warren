# API Contract

## Base endpoint

`POST /v1/analyze`

The `mode` field selects one of two different jobs. Mode-specific validation prevents a caller from accidentally screening one ticker or running Deep against an entire universe.

## Screen mode

### Request

```json
{
  "mode": "screen",
  "tickers": ["AAPL", "MSFT", "NVDA", "GOOG"],
  "top_n": 20,
  "min_score": 60
}
```

Rules:

- `tickers` is required.
- `ticker` must not be supplied.
- Maximum current request size: 1,000 symbols.
- `top_n`: 1-100, default 25.
- `min_score`: 0-100, default 0.
- Duplicate tickers are removed while preserving first appearance.
- Screen does not invoke the DeepAnalysisProvider or EvidenceProvider.

### Response

```json
{
  "mode": "screen",
  "screened_count": 4,
  "failed_tickers": [],
  "results": [
    {
      "ticker": "MSFT",
      "company_name": "Microsoft Corporation",
      "sector": "Technology",
      "price": 0,
      "scores": {
        "fundamentals": 0,
        "valuation": 0,
        "business_quality": 0,
        "growth": 0,
        "risk_resilience": 0,
        "market_context": 0,
        "overall": 0
      },
      "missing_data_count": 0
    }
  ]
}
```

Values above are schema examples, not live market values.

Screen results are sorted by `scores.overall` descending after applying `min_score`.

## Deep mode

### Request

```json
{
  "mode": "deep",
  "ticker": "NVDA"
}
```

Rules:

- `ticker` is required.
- `tickers` must not be supplied.
- Deep mode uses the configured DeepAnalysisProvider.
- Deep mode may use a configured EvidenceProvider. Evidence-source failures are represented in `evidence.source_status` and do not automatically fail the whole analysis.

### Response

```json
{
  "mode": "deep",
  "ticker": "NVDA",
  "metrics": {},
  "scores": {},
  "evidence": {
    "filings": [
      {
        "form": "10-Q",
        "filed_at": "2026-01-01",
        "accession_number": "...",
        "primary_document": "...",
        "url": "...",
        "source": "SEC EDGAR"
      }
    ],
    "news": [
      {
        "title": "...",
        "publisher": "...",
        "published_at": "2026-01-01T12:00:00Z",
        "url": "...",
        "source": "Yahoo Finance"
      }
    ],
    "estimate_revisions": [
      {
        "horizon": "+1y",
        "analyst_count": 0,
        "eps_current": 0,
        "eps_30d_ago": 0,
        "eps_up_30d": 0,
        "eps_down_30d": 0,
        "earnings_growth": 0,
        "revenue_growth": 0,
        "source": "Yahoo Finance"
      }
    ],
    "earnings_history": [],
    "macro": [
      {
        "series_id": "DGS10",
        "label": "US 10-year Treasury yield",
        "value": 0,
        "prior_value": 0,
        "prior_period": "previous observation",
        "as_of": "2026-01-01",
        "units": "percent",
        "source": "FRED"
      }
    ],
    "source_status": [
      {"source": "SEC EDGAR", "status": "ok", "detail": "..."},
      {"source": "FRED", "status": "unavailable", "detail": "FRED_API_KEY is not configured; macro evidence skipped."}
    ],
    "metadata": {}
  },
  "missing_data": [],
  "analysis": {
    "thesis": "...",
    "positives": ["..."],
    "concerns": ["..."],
    "bull_case": ["..."],
    "bear_case": ["..."],
    "risks": ["..."],
    "what_would_change_view": ["..."],
    "verdict": "...",
    "confidence": "medium"
  },
  "model": "gemini-2.5-flash",
  "disclaimer": "For research purposes only. Not financial advice."
}
```

Values above are schema examples, not live financial data.

### Evidence semantics

- `filings` contains SEC filing metadata and does not mean Warren has read the filing body.
- `sec_facts` contains selected structured SEC XBRL values with periods, forms and accession references.
- `news` currently contains source-attributed headlines only. It does not mean Warren has retrieved full article text.
- `estimate_revisions` and `earnings_history` contain structured Yahoo/yfinance values when available.
- `earnings_call_qa` contains a bounded set of material analyst questions and management-answer excerpts when `ALPHA_VANTAGE_API_KEY` is available. The latest company fiscal quarter is queried first, fallback discovery is capped at four quarters, requests follow free-tier pacing, and raw transcripts are not retained.
- `analysis.bull_insights` and `analysis.bear_insights` are the primary investor-facing thesis objects. Each contains a headline, finding, supported cause, durability, time horizon, investor implication, monitoring signals, optional catalyst, qualitative likelihood and impact, confidence, and supporting claim IDs. The legacy `bull_case` and `bear_case` string arrays remain in the response for compatibility.
- `macro` contains configured FRED series when `FRED_API_KEY` is available.
- `source_status` is part of the research result. Clients should surface unavailable/error states rather than hiding them.

## Health

`GET /health`

```json
{
  "status": "ok",
  "service": "warren"
}
```

## HTTP status behavior

- `200`: successful Screen or Deep result.
- `422`: invalid request shape (Pydantic/FastAPI validation).
- `502`: upstream market-data or Deep-analysis execution failure.
- `503`: Deep mode requested without valid LLM/provider configuration.

Individual evidence-provider failures normally remain a `200` Deep response with explicit `source_status` error/unavailable entries.

## Compatibility policy

The `/v1` response contract should remain backward compatible. Additive fields may be introduced without a version bump. Removing/renaming fields or changing score meanings materially should result in a new API version or documented migration.

## Recommended future endpoints

Do not add these until needed by a client:

- `GET /v1/methodology` for machine-readable methodology/version metadata.
- `GET /v1/analysis/{ticker}` for cached analysis retrieval.
- `POST /v1/screen` and `POST /v1/deep` only if separate endpoints materially simplify client use; the current mode contract is intentionally compact.
