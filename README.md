# Warren

Ask Warren is a stock-research product backed by a reusable intelligence engine for screening and deeper investment research.

Its provider interfaces are intentionally independent of any specific market-data vendor or LLM.

> Research software only. Warren does not provide personalized investment advice or execute trades.

## Why Warren exists

Most stock tools either rank companies with opaque scores or ask one LLM to produce an unchallenged narrative. Warren separates these jobs:

- **Screen mode** cheaply ranks a universe using structured data and deterministic scoring.
- **Deep mode** investigates one company using source-attributed evidence, independent bull/bear/risk perspectives, and final synthesis.

This preserves the strongest design idea from TradingAgents while avoiding multi-agent cost across an entire index.

## Ask Warren

**Ask Warren** is the standalone user-facing product built on top of the Warren engine. Its primary experience is a single-stock Deep analysis: enter a ticker, review the investment thesis, Bull and Bear cases, risks, quality/valuation evidence, and a three-state research verdict:

- **Attractive** — closest analogue to Buy;
- **Watch** — closest analogue to Hold / Wait;
- **Avoid** — closest analogue to Sell / Do not initiate.

Every verdict should also state its confidence and **what would change Warren's view**.

The public methodology page is served at:

```text
GET /methodology
```

It explains the scoring model, evidence discipline, Deep workflow, three verdicts, DCF framework, limitations and methodology versioning in user-facing language. The detailed technical specification remains in [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

## Modes

### Screen

Use when the question is: **Which stocks deserve further research?**

```json
{
  "mode": "screen",
  "tickers": ["AAPL", "MSFT", "NVDA", "GOOG"],
  "top_n": 20,
  "min_score": 60
}
```

Screen mode:

- makes no LLM calls;
- does not collect news, filings or macro evidence;
- scores fundamentals, valuation, business quality, growth, risk resilience and market context;
- ranks a caller-supplied universe;
- powers Ask Warren's transparent stock screener and can support future research workflows.

### Deep

Use when the question is: **I am interested in this company. What is the investment argument and what could be wrong with it?**

```json
{
  "mode": "deep",
  "ticker": "NVDA"
}
```

Deep mode currently runs:

```text
Structured company metrics
          +
Source-attributed evidence
  |-- SEC filing metadata + structured XBRL facts
  |-- Yahoo recent news headlines
  |-- Yahoo EPS/revenue estimates + revisions
  |-- Yahoo earnings surprise history
  `-- FRED macro observations (optional)
          |
Deterministic scoring
          |
   +------+------+------+
   |             |      |
 Bull analyst   Bear   Risk reviewer
   |             |      |
   +-------------+------+
                 |
          Final evaluator
                 |
Thesis / positives / concerns / risks /
what changes the view / verdict / confidence
```

### Evidence discipline

Warren treats source material according to what was actually retrieved:

- SEC filing entries are metadata; SEC XBRL entries are structured primary-source facts. Neither means the narrative filing text was read.
- Yahoo news entries are **headlines**, not full-article content. Deep must not infer facts beyond the headline.
- Estimate revisions, earnings history and FRED observations are structured values and can be compared directly.
- Every evidence source reports `ok`, `partial`, `unavailable` or `error`; missing sources reduce confidence rather than silently disappearing.

## DCF direction

Ask Warren's valuation experience is designed to include a transparent deterministic DCF rather than an unexplained model-generated fair value. The DCF specification requires:

- normalized base free cash flow;
- explicit forecast assumptions;
- WACC / discount rate;
- terminal-value assumptions;
- net cash/debt and diluted shares;
- Bear / Base / Bull scenarios;
- visible sensitivity and data freshness.

The LLM may explain or challenge assumptions, but it should not perform hidden free-form valuation arithmetic. See [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

## Reusable Python API

```python
from warren import Warren
from warren.deep import GeminiDeepAnalysisProvider
from warren.evidence import (
    CompositeEvidenceProvider,
    FredMacroEvidenceProvider,
    SecFilingEvidenceProvider,
    YahooEvidenceProvider,
)
from warren.providers import YFinanceMarketDataProvider

warren = Warren(
    market_data=YFinanceMarketDataProvider(),
    deep_analysis=GeminiDeepAnalysisProvider(),
    evidence=CompositeEvidenceProvider([
        SecFilingEvidenceProvider(),
        YahooEvidenceProvider(),
        FredMacroEvidenceProvider(),
    ]),
)

screen = await warren.screen(["AAPL", "MSFT", "NVDA"])
deep = await warren.deep("NVDA")
```

The provider interfaces are deliberately replaceable. A future application can use Polygon, FMP, licensed fundamentals, a paid news feed, another macro provider, another LLM, or a non-LLM deep-analysis implementation without changing Warren's caller contract.

## HTTP API

The FastAPI adapter exposes:

- `GET /health`
- `GET /methodology` — public Ask Warren methodology page
- `POST /v1/analyze`

Deep responses include the exact `evidence` packet used for analysis so clients can display provenance and evidence availability.

See [docs/API.md](docs/API.md).

## Documentation

- [Product definition](docs/PRODUCT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API contract](docs/API.md)
- [Methodology](docs/METHODOLOGY.md)
- [Integration guide](docs/INTEGRATION.md)
- [Evaluation strategy](docs/EVALUATION.md)
- [Risks and limitations](docs/RISKS.md)
- [Security](SECURITY.md)
- [Roadmap](docs/ROADMAP.md)
- [Naming / trademark notes](docs/NAMING.md)

## Current status

**v0.3** establishes the reusable evidence layer and grounds Deep mode in filings metadata, news headlines, analyst estimate revisions, recent earnings history and optional macro data. The first deterministic DCF slice now adds transparent Bear/Base/Bull values and sensitivity output when the required cash-flow, balance-sheet and share-count inputs are available.

The transparent DCF V1 milestone is complete. It normalizes available annual free-cash-flow history, projects explicit revenue and FCF-margin paths, anchors growth to bounded forward estimates, calculates a company-specific discount rate, and exposes scenario and sensitivity results with clearly labeled fallbacks.

Still required before production investment-research reliance:

- score calibration/backtesting;
- primary-source filing narrative-text extraction beyond metadata and XBRL facts;
- production/SLA-backed market and news providers;
- evidence freshness/caching policy;
- methodology/model versioning in stored outputs;
- DCF outcome validation against later realized cash flows;
- deeper evaluation of factuality and investment usefulness.

## Configuration

```bash
# Required for Deep synthesis
export GEMINI_API_KEY="..."

# Optional model override
export GEMINI_MODEL="gemini-3.6-flash"

# Optional macro evidence. Deep continues without it when absent.
export FRED_API_KEY="..."

# Recommended for production automated SEC access.
export SEC_USER_AGENT="AskWarren/0.4 contact@example.com"
```

Screen mode does not require an LLM key or evidence-provider keys.

## Runtime caching and API efficiency

Ask Warren avoids unnecessary upstream requests with bounded, in-memory TTL caches:

| Layer | Cache duration | Cache key |
|---|---:|---|
| Yahoo market snapshot | 5 minutes | ticker |
| Yahoo evidence | 15 minutes | ticker |
| SEC filings and facts | 1 hour | ticker |
| Exa web discovery | 2 hours | ticker |
| FRED macro observations | 6 hours | global (shared by every ticker) |
| Gemini synthesis | 30 minutes | metrics + scores + evidence fingerprint |

Concurrent requests for the same cache key share a single upstream fetch. Independent evidence providers are fetched in parallel. Cached models are copied on read and write so request-level normalization cannot mutate cached source data.

Deterministic results produced as a fallback after a transient Gemini failure are not cached, allowing the next request to retry Gemini instead of preserving a degraded response.

These caches live within a warm application instance. A Vercel cold start begins with an empty cache, so this reduces repeated calls without introducing a database or paid service. Persistent cross-instance caching can later be added behind the same provider interfaces if traffic justifies it.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
uvicorn app.main:app --reload
```

OpenAPI documentation is available from FastAPI at `/docs` when running locally. The public methodology page is available at `/methodology`.
