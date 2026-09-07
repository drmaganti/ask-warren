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
  |-- SEC metadata + XBRL facts + full-text RAG passages
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

- SEC filing entries are metadata, SEC XBRL entries are structured primary-source facts, and SEC RAG entries are retrieved narrative passages. These evidence types remain distinct.
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
- [Investment Insight Standard](docs/INVESTMENT_INSIGHT_STANDARD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API contract](docs/API.md)
- [Methodology](docs/METHODOLOGY.md)
- [Integration guide](docs/INTEGRATION.md)
- [Evaluation strategy](docs/EVALUATION.md)
- [SEC filing RAG: design and benefits](docs/RAG.md)
- [Risks and limitations](docs/RISKS.md)
- [Security](SECURITY.md)
- [Roadmap](docs/ROADMAP.md)
- [Naming / trademark notes](docs/NAMING.md)

## Current status

The current build grounds Deep mode in filing metadata, structured XBRL facts, retrieved SEC filing passages, news headlines, analyst estimate revisions, recent earnings history and optional macro data. Its deterministic DCF adds transparent Bear/Base/Bull values and sensitivity output when the required cash-flow, balance-sheet and share-count inputs are available.

The transparent DCF V1 milestone is complete. It normalizes available annual free-cash-flow history, projects explicit revenue and FCF-margin paths, anchors growth to bounded forward estimates, calculates a company-specific discount rate, and exposes scenario and sensitivity results with clearly labeled fallbacks.

Still required before production investment-research reliance:

- score calibration/backtesting;
- deterministic section-by-section filing change extraction and evaluation;
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

# Optional: latest earnings-call analyst Q&A (free development key available).
export ALPHA_VANTAGE_API_KEY="..."

# Recommended for production automated SEC access.
export SEC_USER_AGENT="AskWarren/0.8 your-real-contact-email@domain.com"
```

Screen mode does not require an LLM key or evidence-provider keys.

## Runtime caching and API efficiency

Ask Warren avoids unnecessary upstream requests with a two-level cache: fast in-memory entries plus optional persistent Upstash Redis entries:

| Layer | Cache duration | Cache key |
|---|---:|---|
| Yahoo market snapshot | 5 minutes | ticker |
| Yahoo evidence | 15 minutes | ticker |
| SEC filings, facts and RAG passages | 6 hours | ticker |
| Exa web discovery | 2 hours | ticker |
| FRED macro observations | 6 hours | global (shared by every ticker) |
| Gemini synthesis | 30 minutes | metrics + scores + evidence fingerprint |
| Earnings-call analyst Q&A | 7 days | ticker |

Concurrent requests for the same cache key share a single upstream fetch. Independent evidence providers are fetched in parallel. Cached models are copied on read and write so request-level normalization cannot mutate cached source data.

Deterministic results produced as a fallback after a transient Gemini failure are not cached, allowing the next request to retry Gemini instead of preserving a degraded response.

Gemini failures are classified without logging prompts, response bodies or API keys. Source status and structured runtime logs record the safe failure category, exception type and HTTP status when available—for example rate/quota limit (`429`), authentication (`401`), permission (`403`), invalid request (`400`) or temporary provider service failure (`5xx`).

Bull and Bear sections lead with investor-facing findings rather than category scores. Each argument states the observed evidence, explains why it matters and, where compatible quarterly history is available, compares revenue, net income, operating cash flow, free cash flow, gross margin and operating margin with both the previous quarter and the same quarter one year earlier. Margin changes are expressed in percentage points; dollar measures are expressed as percentage changes. Ask Warren does not display an industry or peer average unless the data provider supplies a defined, comparable peer group, so a missing comparison is preferable to a misleading one.

The decision-first view presents up to six evidence-ranked reasons to own and six reasons to sell or wait. Each opens into the finding, supported cause, durability, time horizon, investor implication, monitoring signals, confidence and clickable evidence. Unsupported filler is never added merely to reach six. The legacy Bull/Bear strings remain in the API for compatibility, and the deterministic fallback produces the same structured experience when model synthesis is unavailable.

The overview uses the reported analyst low, median and high price targets instead of presenting Ask Warren's DCF as a price prediction. Median is preferred to mean because one unusually high or low analyst target has less influence on it. The targets are explicitly labeled as estimates, linked to Yahoo Finance, and never treated as guarantees. DCF remains available as a deeper scenario-analysis tool.

Forward-looking Bull and Bear arguments use structured analyst growth expectations, estimate changes and revision breadth, plus retrieved guidance and demand evidence when available. “Signals that could change the view” surfaces observable changes such as customer demand, estimate revisions, margins, capital returns, litigation or market positioning—not financial-report calendar dates. Supported arguments carry a source link in the analysis. The detailed supporting evidence, SEC-reported fundamentals and filing/research passages remain available in collapsed sections at the end of the page so the primary conclusion stays readable without hiding its evidence trail.

When `ALPHA_VANTAGE_API_KEY` is configured, Deep mode also retrieves the newest available earnings-call transcript. Ask Warren derives the company's latest fiscal quarter from market-data metadata, tries that quarter first, and limits fallback discovery to four quarters. Requests are paced for the free tier and successful or unavailable results are cached for seven days. Only material analyst questions and short management-answer excerpts are retained; the raw transcript is not stored. The analysis model may use these excerpts to identify the concern behind a question, assess whether the response addressed it, and connect the exchange to future demand, earnings or execution risk. Confirm licensing before using third-party transcript content in a commercial offering.

When `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` are configured, fresh entries survive Vercel cold starts and deployments. Every Redis entry has the same source-specific TTL shown above and Redis automatically deletes it at expiry; no stale duplicate is retained. Redis errors never prevent analysis: the application falls back to its local cache and live providers. Without Redis configuration, the same code operates as a warm-instance memory cache.

The Vercel Upstash integration supplies these variables automatically. `KV_REST_API_URL` and `KV_REST_API_TOKEN` are also accepted for compatibility. Keep all Redis credentials server-side and out of Git.

### SEC filing RAG

When `UPSTASH_VECTOR_REST_URL` and `UPSTASH_VECTOR_REST_TOKEN` are configured, Deep mode retrieves citation-ready passages from the latest and prior annual and quarterly SEC filings. Ask Warren downloads the primary SEC documents, retains a small set of material-risk and business-change chunks, replaces the ticker's prior vector corpus, and retrieves passages relevant to changes in risks, demand, competition, margins, liquidity, capital allocation and management outlook.

The vector index uses Upstash-hosted embeddings, so no separate embedding API key is required. Each ticker corpus is replaced rather than appended, and inactive ticker corpora are pruned after 30 days, preventing stale filings from consuming the free storage allowance. If the free vector service is temporarily unavailable or still indexing, Ask Warren returns the same bounded, materiality-ranked filing passages locally and reports the fallback in evidence metadata. RAG is not used for prices, ratios, technicals, estimates or macro observations; those remain structured source data.

This improves the product in four practical ways: it connects financial changes to management's disclosed explanations, compares current and prior filing language, gives Bull/Bear/Risk reviewers stronger primary-document evidence, and makes conclusions easier to trace back to source passages. See [SEC filing RAG: design and benefits](docs/RAG.md) for the full rationale, safeguards and limitations.

## Development

### Earnings-driver analysis

Quarterly statement comparisons include operating income, pretax income, tax provision,
interest, other income, capital expenditure and working-capital changes when available.
An arithmetic bridge separates operating-income changes, below-operating changes and
tax-expense effects, retaining any unexplained residual. Comparisons require aligned
periods; missing quarters are not substituted for the previous quarter or year.

Filing retrieval targets transaction gains, restructuring, taxes and cash-flow notes.
Synthesis must distinguish recurring operations from one-time effects, prefer matching
company-reported GAAP figures over conflicting aggregator values, and cite evidence for
causal explanations. Revenue contraction alone does not establish weaker customer demand.
When the evidence does not identify a cause, analysis states what is missing. The
deterministic fallback provides arithmetic diagnostics, not an inferred management explanation.
This does not yet provide a complete balance-sheet bridge or guarantee retrieval of every note.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
uvicorn app.main:app --reload
```

OpenAPI documentation is available from FastAPI at `/docs` when running locally. The public methodology page is available at `/methodology`.
