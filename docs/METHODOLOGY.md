# Warren Methodology

## Purpose

Warren is a research system for evaluating public companies consistently and transparently. It combines deterministic financial analysis with source-grounded AI research. The goal is not to produce a mysterious one-number stock pick; it is to help a user understand:

- the quality of the underlying business;
- the strength of its financial position;
- its growth profile;
- whether the current valuation appears attractive;
- the strongest supported bull and bear arguments;
- the risks that could invalidate the thesis;
- what would change the conclusion.

> **Important:** Warren is research software, not personalized investment advice. The current scoring model is an initial heuristic model, not a validated return-prediction system. Weights and thresholds must be calibrated with historical and out-of-sample evaluation before being treated as predictive investment signals.

---

## 1. Structured category scores

Warren currently reports six deterministic category scores from 0 to 100:

1. Fundamentals
2. Valuation
3. Business quality
4. Growth
5. Risk resilience
6. Market context

The current overall score uses these weights:

```text
Fundamentals      30%
Valuation         25%
Business quality  20%
Growth            10%
Risk resilience   10%
Market context     5%
```

This weighting reflects a long-term fundamental-research orientation rather than a short-term trading model.

Each input is scored by interpolating between the published band thresholds. A company whose metric sits between two thresholds therefore receives a proportionate score rather than the same fixed bucket score as every company in that range. Exact threshold scores and the overall category weights remain unchanged.

### Fundamentals

Initial inputs include:

- positive free cash flow;
- positive operating cash flow;
- current ratio;
- debt-to-equity;
- profit margin.

### Valuation

Initial inputs include:

- trailing P/E;
- forward P/E;
- PEG;
- EV/EBITDA;
- free-cash-flow yield.

Current absolute valuation bands are placeholders. Planned improvements include:

- sector-relative valuation;
- company-history-relative valuation;
- earnings and FCF normalization;
- capital-intensity-aware metrics;
- analyst-estimate revisions as a separate Screen signal rather than an implicit valuation input.

### Business quality

Initial inputs include:

- ROE;
- ROA;
- gross margin;
- operating margin;
- positive free cash flow.

Planned improvements include ROIC, margin stability/trend, dilution, capital allocation, recurring/repeat revenue proxies and competitive-position evidence.

### Growth

Initial inputs include:

- revenue growth;
- earnings growth.

Planned improvements include multi-year CAGR, forward consensus, estimate-revision breadth/magnitude and growth quality.

### Risk resilience

Initial inputs include:

- beta;
- debt-to-equity;
- current ratio;
- positive free cash flow.

This is not a complete investment-risk model. Planned additions include interest coverage, refinancing maturity, customer concentration, cyclicality, dilution, accounting flags and event/regulatory risks.

### Market context

Market context is deliberately low weight. Initial inputs compare price with the 200-day average and 52-week high.

Technical context should not turn a weak business into a high-quality investment. User-specific technical or trading rules remain outside Ask Warren's research methodology.

---

## 2. Missing-data discipline

Warren does not invent missing financial metrics.

Category averages use available components. If no component is available, the current neutral fallback is 50. Deep mode separately measures the completeness of important financial inputs as part of verdict confidence, so a neutral fallback is not treated as equally trustworthy as a fully observed score.

---

## 3. Deep-analysis methodology

Deep mode is inspired by TradingAgents but adapted for fundamental stock research.

### Step 1: structured company metrics

Warren retrieves a `MetricSnapshot` and computes deterministic category scores. Numerical company metrics originate from the configured market-data provider, not model memory.

### Step 2: source-attributed evidence packet

Warren builds an explicit `EvidenceBundle` before any LLM reasoning.

Current evidence sources include:

- **Company filings:** recent material SEC filing documents (`10-K`, `10-Q`, `8-K`, `20-F`, `40-F`, `6-K` and amendments) delivered through Yahoo Finance's filing mirror;
- **Yahoo Finance/yfinance:** recent news headlines;
- **Yahoo Finance/yfinance:** EPS estimate trend/revision counts and forward earnings/revenue growth fields when available;
- **Yahoo Finance/yfinance:** recent actual-vs-estimate earnings history;
- **FRED:** selected macro observations when `FRED_API_KEY` is configured.

Every provider reports an explicit source status. One failed source does not cause the other evidence to disappear.

### Step 3: evidence-depth rules

Warren distinguishes source authority from the depth actually retrieved:

- SEC filing metadata proves that a filing/form/date exists; it does **not** prove the contents of that filing were read.
- A Yahoo headline is headline-level evidence; Warren may not infer the unseen article body.

### Material-development ranking

Ask Warren converts recent news and retrieved web excerpts into deduplicated investment events before presenting them. Exa searches through three focused lenses: future demand and growth catalysts; expectations, margins and capital deployment; and competition, regulation, litigation and structural risks. Results are deduplicated by URL and event-title similarity so syndicated coverage does not receive artificial weight.

Each event receives a deterministic, explainable materiality score out of 100:

| Factor | Weight |
|---|---:|
| Potential financial impact | 25 |
| Forward relevance | 20 |
| Ability to change the investment thesis | 15 |
| Evidence quality | 15 |
| Magnitude and business scope | 10 |
| Surprise relative to expectations | 10 |
| Immediacy | 5 |

Independent corroboration from separately retrieved excerpts can add up to five points, subject to the 100-point cap. Repeated headlines do not count as independent confirmation. Scores of 80–100 are **critical**, 60–79 **material**, 40–59 **relevant**, and below 40 **background**. Only relevant-or-higher developments are shown in the default Recent Developments view. The score ranks attention; it does not determine whether an event is bullish or bearish.

Each displayed development includes the event, its investor implication, directional interpretation, time horizon, themes, scoring breakdown and clickable source. Headline-only evidence remains visibly limited and ranks below retrieved excerpts or authoritative original sources. Material developments also remain available to the Bull/Bear synthesis as normalized evidence claims.
- Structured estimate revisions, earnings-history fields and FRED observations may be compared directly as supplied values.
- Missing or unavailable sources reduce confidence instead of being filled from model memory.

These restrictions are part of the Deep-analysis contract.

### Step 4: independent perspectives

Three research perspectives run independently:

- **Bull analyst:** strongest supported positive case and its weaknesses.
- **Bear analyst:** strongest supported negative case and its weaknesses.
- **Risk reviewer:** key risks, missing evidence, stale/incomplete-source concerns and risk summary.

The independent perspectives do not see one another's arguments before producing their initial view.

### Step 5: final synthesis

The final evaluator receives:

- original structured metrics;
- deterministic category scores;
- the exact source-attributed evidence packet;
- Bull output;
- Bear output;
- Risk output.

The evaluator synthesizes rather than votes. It must weight source facts above agent rhetoric, distinguish business quality from stock valuation, and reduce confidence when important evidence is missing.

---

## 4. Warren verdicts

The public Ask Warren product uses three research verdicts:

### Attractive

Closest familiar analogue: **Buy**.

Use when the combined evidence suggests the business quality, valuation and risk/reward are sufficiently favorable to merit serious consideration at the current price.

An Attractive verdict should not be produced merely because a company is high quality. Warren should be able to say that an excellent business is not currently attractive if valuation leaves insufficient margin of safety.

### Watch

Closest familiar analogue: **Hold / Wait**.

Use when the thesis is credible but the current setup is not compelling enough for an Attractive verdict. Typical reasons include:

- strong company but expensive valuation;
- attractive valuation but unresolved business risk;
- insufficient evidence;
- mixed Bull/Bear balance;
- a catalyst, filing or earnings event that materially affects uncertainty.

### Avoid

Closest familiar analogue: **Sell / Do not initiate**.

Use when current valuation, business deterioration, balance-sheet weakness, structural risks, evidence quality or risk/reward makes the stock unattractive for further investment consideration at the current time.

`Avoid` is preferred to `Sell` because a user may not own the security.

### Verdict confidence

Every verdict should include a separate confidence level:

- **High** — strong and sufficiently complete evidence with limited unresolved contradiction.
- **Medium** — reasonable conclusion with meaningful uncertainty or partial evidence.
- **Low** — important inputs are missing, stale or contradictory.

Confidence is not a measure of expected return. It measures confidence in the quality of the current research conclusion.

Warren calculates a company-specific evidence-confidence score after validating every citation. The score weights:

```text
Coverage of key investment points  30%
Source authority and retrieval depth 25%
Independent corroboration           20%
Evidence freshness                  15%
Critical financial-data completeness 10%
```

The key investment points are the thesis plus the leading Bull and Bear insights shown to the user. A point counts as supported only when it cites a claim that exists in the retrieved evidence packet. Primary or structured evidence earns more weight than metadata or headlines, and claims confirmed by multiple independent sources earn more weight than single-source claims. Unresolved duration or time horizon reduces confidence.

Scores of 80–100 are High confidence, 60–79 are Medium and below 60 are Low. The interface exposes concise reasons and the most important evidence gaps. Confidence is recalculated on every report, including when cached narrative analysis is reused.

### What would change the view?

Every Deep analysis should identify concrete conditions that could move Warren between Attractive, Watch and Avoid. Examples include:

- valuation moving into or out of a reasonable range;
- sustained margin deterioration or recovery;
- significant estimate revisions;
- debt or liquidity deterioration;
- a material regulatory outcome;
- evidence that strengthens or weakens the competitive moat;
- a new filing or earnings release that changes the thesis.

This makes the verdict falsifiable rather than static.

---

## 5. DCF valuation methodology

Ask Warren may include a deterministic discounted-cash-flow model as one valuation lens. The DCF must be transparent and must not be calculated by free-form LLM arithmetic.

### Required inputs

At minimum the model should use:

- normalized base free cash flow;
- explicit forecast period;
- forecast FCF growth assumptions;
- discount rate / WACC;
- terminal growth assumption or exit-value approach;
- net cash or net debt;
- diluted shares outstanding.

Where available, forecast assumptions may be anchored by:

- recent historical growth;
- analyst revenue/EPS/FCF consensus;
- company guidance;
- margin history;
- industry/peer context.

The LLM may explain or challenge assumptions but may not silently replace the deterministic DCF calculation.

### Operating comparisons

Score explanations show the reported inputs that moved the score and, where compatible data is available, compare quarterly revenue, net income, operating cash flow, free cash flow, gross margin and operating margin with the previous quarter and the same quarter a year earlier. Year-over-year comparisons help control for seasonality, while sequential comparisons show the latest direction of travel. Margin movements are stated in percentage points so they are not confused with percentage growth.

Industry or peer medians are shown only when a provider supplies a named, economically comparable peer group and aligned reporting periods. Ask Warren does not substitute a broad sector average or mix annual and quarterly periods merely to fill the field.

The current `dcf-v1.0` implementation normalizes base FCF as the median of up to three positive annual observations when at least two are available. Otherwise it uses current FCF and labels that fallback explicitly. Base revenue growth is anchored to the median of available Yahoo forward revenue and earnings growth estimates, bounded between 2% and 12%; when both estimates are unavailable, the documented fallback is 6%. Bear and Bull revenue growth are deterministic adjustments around that base.

Each scenario explicitly projects revenue and an FCF-margin path. Base holds the normalized starting FCF margin constant; Bear contracts it by one percentage point over five years; Bull expands it by one percentage point. The resulting FCF CAGR is returned alongside the revenue and margin assumptions rather than used as a hidden input.

The base discount rate uses a CAPM-style cost of equity derived from company beta, plus an after-tax debt cost weighted by market capitalization and reported debt. The risk-free rate, equity-risk premium, debt cost and tax rate are versioned configured assumptions. Missing or unsupported beta falls back to 1.0; incomplete capital structure falls back to an all-equity weighting; the final rate is bounded between 7% and 15%. Bear and Bull scenarios add or subtract one percentage point within those bounds. These choices and fallbacks are returned with every DCF result.

### Scenario model

Warren should show at least three scenarios:

```text
Bear case  — lower growth / weaker margins / higher discount rate
Base case  — central assumptions
Bull case  — stronger growth / stronger margins / lower risk premium
```

The user should see the assumptions that generate each result rather than one unexplained intrinsic-value number.

### DCF output

The UI should expose:

- estimated fair value per share for Bear / Base / Bull;
- current market price;
- implied upside/downside for each scenario;
- key assumptions;
- sensitivity to discount rate and terminal growth;
- data date/freshness;
- methodology version.

DCF is one lens, not the entire verdict. A precise model output should never be presented as a precise prediction of future market price.

### DCF guardrails

- Do not run a standard DCF where the business model makes FCF forecasting inappropriate without adapting the model.
- Do not hide unusually large stock-based compensation, dilution, debt or acquisition effects.
- Do not use negative or unstable FCF without explaining normalization or switching to an appropriate valuation framework.
- Do not let an LLM fabricate forecast assumptions when data is unavailable.
- Show sensitivity because small changes in WACC and terminal growth can materially change estimated value.

---

## 6. Estimate revisions and Screen

Estimate revisions are currently **Deep evidence only**. They are not yet part of the deterministic Screen score.

Adding revisions to Screen belongs in a methodology change that is backtested/calibrated rather than silently altering the current score.

---

## 7. Macro scope

The initial FRED bundle is intentionally small and generic, covering items such as rates, unemployment and CPI context.

Macro relevance varies materially by company and sector. Warren should not give generic macro signals large deterministic weight until company/sector sensitivity is validated.

---

## 8. Evidence still not included

Current Deep analysis is materially better grounded than a generic LLM response, but important evidence gaps remain:

- actual SEC filing text/XBRL facts and management commentary rather than filing metadata alone;
- SEDAR+ / Canadian issuer filing evidence;
- earnings-release and guidance text;
- full licensed news/article content;
- deeper industry and peer context;
- point-in-time historical estimates;
- explicit evidence IDs/citations at individual generated-claim level.

These gaps should be visible to the user through confidence and source-status indicators.

---

## 9. Methodology versioning

Material changes to weights, thresholds, DCF assumptions, factor definitions, evidence rules or verdict logic must produce a new `methodology_version`.

Every saved analysis should eventually persist at least:

```text
methodology_version
analysis_timestamp
market_data_timestamp
evidence_timestamp(s)
model/provider version
DCF assumption set/version, when used
```

Historical analyses must remain interpretable after Warren evolves.

---

## 10. Evaluation standard

A methodology is not considered improved merely because the output sounds more convincing.

Changes should be evaluated for:

- factual correctness;
- evidence attribution;
- deterministic reproducibility;
- missing-data behavior;
- stability across repeated runs;
- calibration of scores and verdicts;
- historical and out-of-sample performance where appropriate;
- usefulness to users making research decisions.

See [`EVALUATION.md`](./EVALUATION.md) for the broader evaluation framework.
