# Warren / Ask Warren Roadmap

This roadmap covers both the reusable **Warren stock-intelligence engine** and the standalone **Ask Warren** product experience built on top of it.

The guiding principle is simple: improve research quality first, then add convenience and breadth. New UI should not create a stronger impression of certainty than the underlying methodology supports.

---

## Product north star

Ask Warren should help a user answer four questions:

1. **Is this a good business?**
2. **Is the current valuation reasonable?**
3. **What is the strongest case for and against owning it?**
4. **What evidence or event would change the conclusion?**

The experience should remain explainable, source-aware and useful even when the answer is uncertain.

---

## Ask Warren V1 — Standalone Analyze experience

Goal: a user can enter one ticker and receive a complete, understandable research report.

### Core Analyze page

- [x] Dark Ask Warren web interface.
- [x] Ticker/company search and `Run Analysis` action.
- [x] Company header with price, market cap, sector, P/E and 52-week context.
- [x] Investment thesis.
- [x] Bull vs Bear case.
- [x] Dedicated risk review.
- [x] Quality / fundamentals / growth / financial-health presentation.
- [x] Valuation snapshot.
- [x] Earnings summary and estimate-revision evidence.
- [x] Recent news/evidence section with source status.
- [x] Final verdict: **Attractive / Watch / Avoid**.
- [x] Confidence: **High / Medium / Low**.
- [x] `What would change Warren's view?` section.
- [x] Clear research-only / not-investment-advice disclosure.

### Navigation

For V1 only Analyze and Methodology need to be fully active.

- [x] Methodology page.
- [x] Analyze page.
- [ ] Watchlist — **Coming Soon**.
- [ ] Screener — **Coming Soon**.
- [ ] History — **Coming Soon**.
- [ ] Portfolio — **Coming Soon**.
- [x] Roadmap page.

Do not add paid-plan UI until the product has demonstrated repeat value and there is a real paid feature boundary.

---

## Ask Warren V1.1 — Transparent DCF valuation (complete)

Goal: add intrinsic-value analysis without creating false precision.

- [x] Deterministic DCF engine independent of the LLM.
- [x] Historical free-cash-flow normalization.
- [x] Explicit forecast period.
- [x] Revenue / margin / FCF-growth assumptions.
- [x] WACC / discount-rate calculation or transparent configured assumption.
- [x] Terminal-growth assumption.
- [x] Net cash/debt adjustment.
- [x] Diluted-share-count handling.
- [x] Per-share intrinsic-value output.
- [x] Bear / Base / Bull scenarios.
- [x] Sensitivity matrix for WACC vs terminal growth.
- [x] Visible source and timestamp for every DCF input.
- [x] Explain which assumptions are deterministic, consensus-derived or analyst-adjustable.
- [x] Never let an LLM perform hidden arithmetic or silently change valuation assumptions.

DCF should be presented as a **range of plausible values**, not a single authoritative target price.

---

## v0.2 — Reusable core (complete)

- [x] Warren package boundary independent of client applications.
- [x] Screen and Deep modes.
- [x] Provider protocols.
- [x] Yahoo Finance development data adapter.
- [x] Deterministic category scoring.
- [x] TradingAgents-inspired Bull/Bear/Risk -> Final Deep flow.
- [x] Gemini deep-analysis provider.
- [x] FastAPI adapter.
- [x] Product, architecture, API and methodology documentation.
- [x] Unit/contract test baseline.
- [x] CI workflow.

---

## v0.3 — Evidence quality (current)

Goal: make Deep mode materially more complete without letting LLMs invent context.

Completed in current v0.3 slice:

- [x] reusable `EvidenceProvider` protocol and typed `EvidenceBundle`;
- [x] composite evidence collector with per-source failure isolation;
- [x] official SEC EDGAR recent filing **metadata** provider for exact US ticker mappings;
- [x] Yahoo recent headline evidence;
- [x] Yahoo EPS/revenue estimate trends and revision counts;
- [x] Yahoo recent earnings surprise/history evidence;
- [x] optional FRED macro provider;
- [x] source status (`ok` / `partial` / `unavailable` / `error`);
- [x] evidence packet passed through Deep API response;
- [x] Deep prompts explicitly prevent filing-content and headline-content overreach;
- [x] provider resilience tests.

Remaining v0.3 quality work:

- [x] latest structured SEC XBRL facts with filing-period and accession provenance;
- [ ] actual SEC filing text rather than filing metadata only;
- [ ] SEDAR+ / Canadian issuer evidence strategy;
- [ ] earnings release and guidance text;
- [ ] full/licensed news content where terms permit;
- [ ] industry and peer context provider;
- [x] stable evidence IDs and claim-level citations in generated output;
- [x] explicit evidence freshness/version metadata;
- [x] claim-level evidence checker;
- [ ] frozen factuality/evidence-overreach eval fixtures.

Current Deep architecture:

```text
Fundamentals / structured metrics
SEC filing metadata + structured XBRL facts
Yahoo news headlines
Yahoo estimate revisions + earnings history
FRED macro (optional)
Market context
        |
Bull + Bear + Risk
        |
Final evaluator
```

---

## v0.4 — Better Screen methodology

- [ ] sector-relative valuation;
- [ ] company-history-relative valuation;
- [ ] ROIC;
- [ ] multi-year revenue/EPS/FCF growth;
- [ ] dilution/share-count trend;
- [ ] margin trend/stability;
- [ ] interest coverage;
- [ ] analyst estimate revision breadth/magnitude;
- [ ] earnings surprise/revision signals;
- [ ] data-coverage score;
- [ ] methodology version in every output.

Estimate revisions are intentionally not added to Screen until point-in-time/calibration work supports the weighting.

---

## v0.5 — Evaluation and calibration

- [ ] frozen point-in-time datasets;
- [ ] score-decile backtests;
- [ ] 1m/3m/6m/12m benchmark-relative outcomes;
- [ ] factor ablations;
- [ ] sector/regime analysis;
- [ ] Deep factuality eval suite;
- [ ] filing/headline evidence-overreach evals;
- [ ] Bull/Bear/Risk ablation versus single-agent baseline;
- [ ] evidence-category ablations;
- [ ] confidence calibration;
- [ ] verdict calibration for Attractive / Watch / Avoid;
- [ ] DCF backtesting against later realized cash-flow outcomes, not only market price.

---

## v0.6 — Cost, caching and reliability

- [x] cached market snapshots;
- [x] cached fundamentals until TTL expiry;
- [x] per-source evidence caches with separate TTLs;
- [x] Deep cache keyed to metrics, scores and evidence version;
- [x] duplicate-request coalescing and parallel evidence collection;
- [ ] optional persistent cross-instance cache when usage justifies another service;
- [ ] event-driven invalidation after earnings/filings/material news;
- [ ] retries/circuit breakers;
- [ ] provider fallback;
- [ ] observability for latency, provider errors, token/call cost;
- [ ] user-visible analysis freshness timestamps;
- [ ] graceful partial-analysis states when providers fail.

---

## v0.7 — Production data adapters

Evaluate paid/licensed providers based on coverage, point-in-time history, terms and cost. Candidates may include FMP, Polygon or other licensed fundamentals/estimate/news feeds.

The provider interface should prevent client changes when data vendors change.

Production-readiness criteria should include:

- corporate actions and split handling;
- point-in-time estimates;
- survivorship-bias controls;
- US and Canadian coverage;
- clear redistribution/display rights;
- uptime/SLA expectations;
- predictable cost at target usage.

---

## Ask Warren V2 — Research workflow

### Watchlist

- [ ] Save companies.
- [ ] Track latest verdict and confidence.
- [ ] Surface material changes since last analysis.
- [ ] Notify on earnings, filings or thesis-changing evidence.
- [ ] Show `why the verdict changed` rather than just a new score.

### History

- [ ] Store past analyses with methodology/model/evidence versions.
- [ ] Compare a current thesis with the prior thesis.
- [ ] Display score and verdict movement over time.
- [ ] Preserve the exact evidence packet used for each historical conclusion.

### Screener

- [ ] User-selectable universe.
- [ ] Quality / valuation / growth / risk filters.
- [ ] Warren Screen ranking.
- [ ] Transparent factor contributions.
- [ ] One-click Deep analysis from results.
- [ ] Keep generic Warren screening separate from user-defined portfolio and trading rules.

---

## Ask Warren V3 — Portfolio intelligence

Only after single-company research quality is strong.

- [ ] User-entered portfolio holdings.
- [ ] Aggregate sector/geography/business-model concentration.
- [ ] Portfolio-level risk summaries.
- [ ] Thesis overlap and correlated-risk identification.
- [ ] Earnings/event calendar across holdings.
- [ ] Portfolio research digest.
- [ ] `What changed this week?` summaries.

Explicit boundary: portfolio intelligence should not automatically become personalized asset-allocation advice or autonomous trading.

---

## Longer-term research improvements

- [ ] full SEC filing and earnings-transcript retrieval with claim-level citations;
- [ ] SEDAR+ support;
- [ ] peer-comparison engine;
- [ ] industry structure / moat evidence;
- [ ] management capital-allocation history;
- [ ] share dilution / buyback effectiveness;
- [ ] normalized-cycle earnings for cyclicals;
- [ ] bank/insurer/REIT-specific methodologies rather than forcing one generic model;
- [ ] segment-level financial analysis;
- [ ] geographic/customer concentration;
- [ ] accounting-quality and anomaly signals;
- [ ] insider ownership/trading context where licensed and useful;
- [ ] consensus-estimate dispersion and change history;
- [ ] scenario-specific thesis probabilities only after calibration supports them.

---

## Product milestones

- define the stock-detail experience;
- run Deep on explicit user action or a selected screening candidate;
- render company quality separately from valuation;
- show supporting evidence and missing-data confidence;
- make source status and evidence provenance visible;
- avoid double-counting factors between screening and Deep analysis.

---

## Explicitly deferred

- trade execution;
- autonomous portfolio management;
- personalized allocation advice;
- running Deep on every stock in an index;
- opaque AI-generated target prices;
- hidden DCF assumptions;
- public commercialization under the Warren name before trademark clearance.

---

## How roadmap priorities are chosen

Features should move up the roadmap when they improve one or more of:

1. **Research correctness** — better evidence or fewer unsupported conclusions.
2. **Explainability** — users can understand why Warren reached its view.
3. **Decision usefulness** — information helps users distinguish quality, valuation and risk.
4. **Reliability** — fewer provider, latency or freshness failures.
5. **Evaluation quality** — we can prove whether the feature improves results.
6. **Reuse** — the capability benefits multiple Ask Warren workflows without duplicating logic.

Visual polish and feature breadth should not outrank factual quality, evidence coverage or methodological integrity.
