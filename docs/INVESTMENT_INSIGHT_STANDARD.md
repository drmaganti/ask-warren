# Investment Insight Standard

Status: Approved product direction; implementation in progress.

## Purpose

Ask Warren must help a retail investor understand what is happening inside a business, what could happen next, what the market appears to expect, and which evidence could confirm or disprove the investment thesis. It must not behave like a financial-data summary with an AI paragraph attached.

The emotional job of the product is **confidence through understanding**. After reading an analysis, the user should be able to explain:

- the underlying business story;
- the strongest Bull and Bear interpretations;
- which future outcomes the valuation depends on;
- which facts are established, inferred or still unknown; and
- what to monitor next.

The target reader is a retail investor with general financial knowledge at approximately a Grade 12 reading level. Terms such as P/E, PEG, DCF, 50-day average, Bull and Bear may be used without basic definitions. More specialized accounting, legal or industry concepts must be explained in plain language.

## Problem statement

Raw values, percentages and internal scores tell users what was measured but often fail to explain why a result changed, whether it is sustainable, or how it affects future value. This encourages users to mistake lagging indicators for investment insight and gives unsupported precision to an incomplete narrative.

Bull and Bear must therefore be competing, evidence-backed investment theses—not lists of favorable and unfavorable metrics.

## Core product question

Every analysis should answer:

> What is changing in this business, what caused it, is it likely to improve or worsen, what expectations are already reflected in the price, and what evidence should make an investor believe or reject that conclusion?

## Required insight structure

Each material Bull or Bear item must contain:

1. **Finding** — the meaningful change, tension or opportunity.
2. **Cause** — the best-supported operating, financial, competitive, legal or macroeconomic explanation.
3. **Durability** — whether the cause appears recurring, temporary, one-time or unresolved.
4. **Investor implication** — how it could affect future demand, revenue, margins, cash flow, risk or valuation.
5. **What to watch** — observable evidence that would confirm or invalidate the interpretation.
6. **Confidence** — high, medium or low, based on evidence quality and agreement.
7. **Sources** — clickable citations supporting the finding and causal explanation.

Numbers should support the interpretation rather than serve as the headline. A bullet that only restates values, percentages, scores or labels does not meet this standard.

### Progressive disclosure

The default Bull/Bear view should show only the insight headline and a two-to-three-sentence summary combining the finding with its investor implication. Cause analysis, durability, time horizon, monitoring signals, catalyst, confidence and sources remain available through **View detailed analysis**. This preserves analytical depth without making the primary decision view feel like a report.

## Bull and Bear as competing theses

The Bull case should describe the strongest supported path to future value creation and the conditions required for it to occur. The Bear case should describe the strongest supported path to disappointment or permanent impairment and the conditions that would make it material.

The two sides may interpret the same evidence differently. For example, rising EPS alongside falling revenue could support:

- a Bull interpretation if durable operating improvements can compound when demand returns; and
- a Bear interpretation if earnings depend on finite cost reductions, tax effects or non-operating gains while demand remains weak.

Ask Warren must not manufacture symmetry. If evidence is substantially stronger on one side, the analysis should say so.

## Forward-looking evidence

Forward-looking analysis is not limited to forecasts. Ask Warren should use relevant leading indicators when available:

- analyst revenue and EPS forecasts, estimate revisions and revision breadth;
- management guidance, guidance changes and changes in management language;
- customer traffic, transactions, volume, pricing, orders, bookings, backlog, retention, churn and market share;
- product launches, store or capacity additions, geographic expansion and partnerships;
- hiring, inventory, capital expenditure and other operating commitments;
- competitor results and industry-level demand signals;
- earnings-call analyst questions and management responses;
- interest rates, wages, commodities, currencies and consumer or enterprise spending;
- debt maturities, refinancing requirements, covenants and capital-allocation flexibility;
- lawsuits, investigations, regulation, patent disputes, labor matters and contract losses;
- acquisitions, divestitures, restructuring, leadership changes, insider activity and incentives.

A forecast must be presented as an expectation, not a fact. Ask Warren should show the assumption or condition that must hold and identify disagreement or uncertainty where supported.

## Expectations and valuation

Investment outcomes depend on the difference between business performance and expectations. Ask Warren should connect:

1. what the company delivered;
2. what management and analysts expect next; and
3. what performance the current valuation appears to require.

“The business is improving” is incomplete if the price already assumes a stronger recovery. “The business is weakening” is incomplete if the valuation already reflects a severe decline. Bull and Bear should explain this expectations gap whenever evidence allows.

## Time horizons

Every thesis must distinguish the period over which it is expected to matter:

- **Near term:** the next reported quarters and identifiable catalysts;
- **Medium term:** approximately 12–24 months of execution; and
- **Long term:** competitive position, reinvestment runway and durable earnings power.

The same evidence can be negative in the near term and positive over a longer period. Ask Warren should explain that tension rather than presenting the arguments as contradictory. When no horizon can be supported, the insight must label it as unresolved.

## Thesis changes and monitoring

Ask Warren should become an evolving investment record rather than a sequence of disconnected reports. When a prior analysis is available, the product should identify:

- new, strengthened, weakened or resolved Bull and Bear insights;
- changes in guidance, forecasts, estimates and management language;
- whether previously defined monitoring conditions were met;
- material changes in valuation without an equivalent business change;
- new risks, catalysts or contradictory evidence; and
- changes caused only by fresher data or improved source coverage.

The product must not imply that the thesis changed when only the wording or model changed. Stored analyses therefore require methodology, model, evidence-version and freshness metadata.

## Industry-specific drivers

The shared insight structure must be supplemented by industry-specific driver maps. Examples include:

- **Retail and restaurants:** traffic, transactions, comparable sales, ticket, unit economics and store growth;
- **Software:** recurring revenue, retention, bookings, remaining performance obligations, customer acquisition and margins;
- **Banks:** net interest margin, deposit mix, credit quality, provisions and regulatory capital;
- **Industrials:** orders, backlog, utilization, price-cost spread and input availability;
- **Pharmaceuticals:** clinical milestones, approvals, patents, exclusivity and pipeline concentration; and
- **Semiconductors:** units, utilization, inventory, pricing, capital intensity and customer concentration.

The system should use a generic framework when a validated industry map is unavailable and disclose that limitation. It must not force a sector-specific metric onto a company for which it is not economically meaningful.

## Risk priority and catalyst timing

Risks and opportunities should be prioritized using supported qualitative assessments of:

- likelihood;
- potential financial or strategic impact;
- time horizon;
- reversibility;
- evidence confidence; and
- the next identifiable catalyst or decision point.

Ask Warren should not invent numerical probabilities. “What to watch” should include a date or event when available, such as the next earnings report, product launch, trial result, regulatory decision, debt maturity, investor day or contract renewal. A high-impact but remote possibility should not be presented as equivalent to a moderate problem that is already occurring.

## Earnings-quality and causal analysis

Before describing an earnings change as operational improvement or deterioration, Ask Warren should reconcile available income-statement, balance-sheet and cash-flow evidence. It should distinguish:

- revenue, volume, price and mix;
- operating margins and recurring cost changes;
- taxes, interest and other income or expense;
- restructuring, impairments and transaction gains or losses;
- acquisitions, divestitures and changes in consolidation;
- share-count changes;
- working capital and capital expenditure; and
- differences between earnings and cash generation.

Arithmetic correlation is not proof of causation. Use language such as “The filing attributes…” for a documented explanation and “The statements show…” for a calculated bridge. When the cause cannot be established, identify the missing evidence rather than using vague speculation.

## Legal and event-risk materiality

The existence of a lawsuit or investigation does not automatically make it a Bear insight. Ask Warren should evaluate, when evidence allows:

- potential exposure relative to earnings, cash and liquidity;
- the likelihood of restricting a material product, market or business practice;
- whether the matter is routine, recurring or exceptional;
- management's disclosed response and reserves;
- timing and identifiable decision points; and
- second-order effects on reputation, customers, regulation or strategy.

Material unresolved events belong in Bear or Risks with explicit uncertainty and a monitoring trigger. Immaterial routine litigation may remain in supporting evidence.

## Evidence and uncertainty rules

- Every material causal or forward-looking claim requires one or more relevant citations.
- Primary sources are preferred for company-specific facts and management explanations.
- Analyst consensus, market data and reputable research may support expectations and external context.
- Headlines and search excerpts must not be treated as full-article evidence.
- Conflicting evidence must be surfaced, not silently resolved.
- Confidence must fall when evidence is stale, indirect, incomplete or contradictory.
- The analysis must separate established facts, supported interpretations and unresolved questions.
- Internal scores may assist ranking, but must not be presented as evidence or lead the Bull/Bear narrative.
- The deterministic fallback must meet the same presentation and evidence standard as model-generated analysis.

## Required investment lenses and ranking

Every analysis evaluates future demand, earnings quality, operating leverage, capital allocation, market expectations and valuation, market positioning, and company-specific risk. A lens becomes a visible Bull or Bear insight only when the available evidence supports a decision-relevant conclusion.

Supported candidates are ranked by potential financial impact, likelihood, evidence confidence and relevance to the current price. Only the strongest three or four insights per side are shown. Each expanded insight explains the expectation gap and a plausible success or failure path. Technical extension requires evidence such as RSI, distance from moving averages, Bollinger position or volume relative to its recent average; price appreciation alone is not evidence that a stock is crowded or overtraded.

## Example

### Margins improved, but demand has not yet confirmed the turnaround

Operating margin increased from 9.5% to 12.9% while quarterly revenue declined 1.4% from the prior year. The statements show that operating income contributed materially to the earnings increase, with additional help from items below operating income. Until the filing identifies those components, the analysis should not assume the entire increase represents recurring efficiency.

Do not expose raw reconciliation diagnostics such as an “unreconciled difference” or an unnamed “below operating income” contribution as an investor-facing bullet. Translate the bridge into a clear conclusion—core operations were the larger driver, non-operating items were the larger driver, or the cause is unresolved—and name a transaction, tax item, or adjustment only when primary evidence supports that attribution.

**Investor implication:** If customer traffic begins growing while the higher margin holds, earnings could rise faster than current revenue expectations. If traffic remains weak, cost improvements have a practical ceiling.

**What to watch:** Comparable-store transactions, customer traffic, regional sales, operating margin, and whether analysts raise revenue estimates as well as EPS estimates.

**Confidence:** Medium; the arithmetic is supported, but the recurring and non-recurring causes require primary-source attribution.

**Sources:** Quarterly filing · Earnings release · Analyst estimates · Earnings-call Q&A

## P0 requirements and acceptance criteria

The insight experience is not complete until all of the following are true:

- [ ] Bull and Bear target six distinct, evidence-ranked investment insights rather than metric summaries; return fewer when six strong points are not supported.
- [ ] The default view limits each insight to a headline and no more than three summary sentences; supporting analysis is collapsed by default.
- [ ] Every insight includes a finding, investor implication and what-to-watch condition.
- [ ] Every causal statement labels durability or explicitly says why durability is unresolved.
- [ ] Each side includes its strongest supported forward-looking argument when forward evidence exists.
- [ ] Relevant demand signals are distinguished from revenue changes; revenue decline alone is not labeled weaker demand.
- [ ] Earnings changes distinguish operating, below-operating, tax and cash-flow effects where data permits.
- [ ] Material legal, regulatory and event risks are assessed for investment impact, not merely mentioned.
- [ ] Valuation is connected to the future performance required to justify the current price.
- [ ] Future demand, earnings quality, operating leverage, capital allocation, market expectations, market positioning and company-specific risk are evaluated on every run.
- [ ] Visible insights are limited to the strongest three or four per side after ranking by impact, likelihood, evidence confidence and decision relevance.
- [ ] Each expanded insight identifies the expectation gap and a plausible success or failure path when the evidence supports one.
- [ ] Every insight identifies a near-, medium- or long-term horizon, or explicitly marks the horizon unresolved.
- [ ] Risks and opportunities are prioritized by supported likelihood, impact, reversibility and timing rather than presentation order.
- [ ] “What to watch” includes an identifiable catalyst or decision point when available.
- [ ] Industry-specific operating drivers are used where a validated driver map exists; otherwise the generic framework and its limitation are disclosed.
- [ ] When a prior analysis exists, Ask Warren distinguishes genuine thesis changes from data, source, methodology or wording changes.
- [ ] Every material insight has clickable, claim-level supporting evidence.
- [ ] Confidence reflects evidence quality, freshness, agreement and unresolved attribution.
- [ ] Missing evidence produces a specific research gap, not invented causation or generic hedging.
- [ ] Gemini and deterministic fallback outputs both satisfy this standard.
- [ ] Internal scores are hidden or secondary and never used to justify a thesis.

## Non-goals

- Personalized buy, sell, position-size or timing advice.
- False precision through point-price predictions or unsupported probabilities.
- Guaranteed detection of every legal, regulatory or corporate event.
- Treating social sentiment, price momentum or analyst consensus as independently decisive.
- Padding either side with weak or repetitive arguments merely to reach the six-insight target.
- Replacing the underlying sources; the interface should make verification easier, not ask users to trust Ask Warren blindly.

## Evaluation standard

Before release, representative analyses should be reviewed across growth, cyclical, financial, consumer, industrial and distressed companies. Reviewers should be able to answer the following without opening the raw evidence sections:

- What is the central business tension?
- Why did the most important financial change occur?
- Is the change recurring or one-time?
- What are the strongest future demand and earnings signals?
- What does the valuation require?
- What could make the Bull or Bear thesis wrong?
- Over what time horizon should each argument matter?
- Which catalyst or decision point could resolve the uncertainty?
- What has changed since the prior analysis, and why?
- Which source supports each material conclusion?

Target acceptance thresholds for the evaluation set:

- at least 90% of Bull/Bear items pass the required insight structure;
- 100% of causal and forward-looking claims have relevant citations;
- zero unsupported causal explanations;
- zero score-led Bull/Bear items;
- zero cases where a revenue change alone is presented as proof of demand change; and
- graceful, specific disclosure whenever required evidence is unavailable.

## Implementation sequence

1. Define a structured insight schema containing finding, cause, durability, time horizon, implication, watch items, catalyst, risk priority, confidence and citations.
2. Add evidence classification for demand, forecasts, guidance, investment, competition, legal events and earnings-quality drivers.
3. Build a deterministic causal and expectations layer before narrative generation.
4. Add an initial set of validated industry driver maps, beginning with consumer/retail and software.
5. Make Gemini synthesize from the structured insight candidates rather than from an undifferentiated evidence packet.
6. Bring material insights to the front of the Analyze page and keep detailed evidence expandable.
7. Persist versioned analysis snapshots and explain genuine thesis changes separately from pipeline changes.
8. Add automated and human evaluation fixtures, including contradictory, stale and missing-evidence cases.

## Open questions

- How should implied market expectations be estimated when a reverse DCF cannot be supported?
- Which legal-event sources and licensing terms are appropriate for production use?
- Should confidence be displayed per insight, only for the overall verdict, or both?
- How should the UI distinguish management guidance from independent analyst forecasts?
- Which industry-specific demand indicators deserve dedicated adapters after the cross-industry standard is complete?
- What analysis history should be retained, and for how long, to support thesis-change explanations?
- Which catalyst dates can be sourced reliably without introducing a paid event-data dependency?
