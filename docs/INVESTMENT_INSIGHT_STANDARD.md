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

## Example

### Margins improved, but demand has not yet confirmed the turnaround

Operating margin increased from 9.5% to 12.9% while quarterly revenue declined 1.4% from the prior year. The statements show that operating income contributed materially to the earnings increase, with additional help from items below operating income. Until the filing identifies those components, the analysis should not assume the entire increase represents recurring efficiency.

**Investor implication:** If customer traffic begins growing while the higher margin holds, earnings could rise faster than current revenue expectations. If traffic remains weak, cost improvements have a practical ceiling.

**What to watch:** Comparable-store transactions, customer traffic, regional sales, operating margin, and whether analysts raise revenue estimates as well as EPS estimates.

**Confidence:** Medium; the arithmetic is supported, but the recurring and non-recurring causes require primary-source attribution.

**Sources:** Quarterly filing · Earnings release · Analyst estimates · Earnings-call Q&A

## P0 requirements and acceptance criteria

The insight experience is not complete until all of the following are true:

- [ ] Bull and Bear contain two to four distinct investment insights rather than metric summaries.
- [ ] Every insight includes a finding, investor implication and what-to-watch condition.
- [ ] Every causal statement labels durability or explicitly says why durability is unresolved.
- [ ] Each side includes its strongest supported forward-looking argument when forward evidence exists.
- [ ] Relevant demand signals are distinguished from revenue changes; revenue decline alone is not labeled weaker demand.
- [ ] Earnings changes distinguish operating, below-operating, tax and cash-flow effects where data permits.
- [ ] Material legal, regulatory and event risks are assessed for investment impact, not merely mentioned.
- [ ] Valuation is connected to the future performance required to justify the current price.
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
- Producing equal numbers of Bull and Bear arguments when the evidence is asymmetric.
- Replacing the underlying sources; the interface should make verification easier, not ask users to trust Ask Warren blindly.

## Evaluation standard

Before release, representative analyses should be reviewed across growth, cyclical, financial, consumer, industrial and distressed companies. Reviewers should be able to answer the following without opening the raw evidence sections:

- What is the central business tension?
- Why did the most important financial change occur?
- Is the change recurring or one-time?
- What are the strongest future demand and earnings signals?
- What does the valuation require?
- What could make the Bull or Bear thesis wrong?
- Which source supports each material conclusion?

Target acceptance thresholds for the evaluation set:

- at least 90% of Bull/Bear items pass the required insight structure;
- 100% of causal and forward-looking claims have relevant citations;
- zero unsupported causal explanations;
- zero score-led Bull/Bear items;
- zero cases where a revenue change alone is presented as proof of demand change; and
- graceful, specific disclosure whenever required evidence is unavailable.

## Implementation sequence

1. Define a structured insight schema containing finding, cause, durability, implication, watch items, confidence and citations.
2. Add evidence classification for demand, forecasts, guidance, investment, competition, legal events and earnings-quality drivers.
3. Build a deterministic causal and expectations layer before narrative generation.
4. Make Gemini synthesize from the structured insight candidates rather than from an undifferentiated evidence packet.
5. Bring material insights to the front of the Analyze page and keep detailed evidence expandable.
6. Add automated and human evaluation fixtures, including contradictory and missing-evidence cases.

## Open questions

- How should implied market expectations be estimated when a reverse DCF cannot be supported?
- Which legal-event sources and licensing terms are appropriate for production use?
- Should confidence be displayed per insight, only for the overall verdict, or both?
- How should the UI distinguish management guidance from independent analyst forecasts?
- Which industry-specific demand indicators deserve dedicated adapters after the cross-industry standard is complete?

