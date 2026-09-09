# Ask Warren production UI v2

Approved: 2026-09-08

## Product identity

Warren is the name of the investment research analyst persona. The brand is not a reference to Warren Buffett and should not use Buffett quotations, imitation language, or “research like Buffett” positioning.

Primary positioning:

> Research any company with Warren.
>
> Your investment research analyst.
>
> Evidence-backed analysis. Clear reasoning. No hype.

## Approved information architecture

Primary research tabs:

1. Investment View
2. Bull & Bear
3. Expectations
4. Financials
5. Evidence

The first screen must answer the decision question quickly: Warren's current view, confidence, investment thesis, analyst price-target context, strongest reasons to own, strongest reasons to sell or wait, and observable signals that could change the view.

## Valuation direction

The production user experience no longer presents Ask Warren's DCF as a fair-value or price-prediction feature.

Instead, valuation expectations are communicated with:

- current share price;
- analyst low, median, and high price targets;
- implied upside/downside to the median and range;
- analyst opinion count when available;
- EPS estimates and recent estimate revisions;
- recent earnings surprises;
- common valuation ratios as context.

The median analyst target is preferred to the mean because it is less sensitive to a single extreme target.

Analyst targets must always be labeled as estimates, not guarantees.

The deterministic DCF code may remain temporarily in the backend for compatibility or research purposes, but it is deprecated from the primary production experience and should not be reintroduced without a new product decision.

## Visual direction

- near-black / deep green canvas;
- restrained Warren green accent;
- amber for Watch and red for material negative signals;
- strong typographic hierarchy;
- fewer cards and less decorative chrome;
- compact evidence-rich layouts;
- calm, premium research-product feel;
- responsive mobile layout;
- no generic AI-SaaS gradients, oversized pills, or excessive glassmorphism.

## Interaction principles

- decision first, supporting detail second;
- Bull and Bear arguments open to show cause, investor implication, confidence, horizon, what to watch, and source links;
- Expectations is a first-class screen;
- evidence remains inspectable without overwhelming the overview;
- source gaps reduce confidence rather than disappearing;
- no non-functional product promises in navigation.

## Production implementation

The v2 interface is served from `web/index-v2.html`.
The refreshed public methodology is served from `web/methodology-v2.html`.
The prior HTML files are retained temporarily as rollback references.
