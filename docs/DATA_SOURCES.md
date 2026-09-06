# Data Sources

This document describes the initial v0.3 evidence sources and the boundaries Warren places around them.

## Source-selection principles

1. Prefer structured or primary sources for factual fields.
2. Preserve source provenance in the returned evidence packet.
3. Do not silently replace an unavailable source with LLM memory.
4. Distinguish source authority from retrieval depth.
5. Keep providers replaceable so a production/licensed feed can be introduced later.

## SEC EDGAR

Provider: `SecFilingEvidenceProvider`

Official references:

- https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data

Current use:

- exact ticker-to-CIK mapping from SEC's published ticker association file;
- recent submissions metadata from `data.sec.gov`;
- selected forms: `10-K`, `10-Q`, `8-K`, `20-F`, `40-F`, `6-K` and amendments;
- form, filing date, accession number, primary document name and EDGAR URL.
- latest structured US-GAAP XBRL facts for revenue, earnings, operating cash flow, capital expenditures, assets, liabilities, equity, stock compensation and shares when reported;
- fiscal period, period end, filing date and accession provenance for every returned XBRL fact.

Authentication:

- no API key;
- automated clients should use an identifying `User-Agent`;
- configure `SEC_USER_AGENT` for production deployments.

Important limitation:

Warren retrieves filing metadata and selected structured XBRL facts, but **not filing narrative text**. Deep may use returned XBRL values as primary-source structured evidence. It may not claim what management, risk factors, MD&A or guidance say unless filing text is retrieved separately.

Canadian `.TO` symbols are not automatically mapped to a possible US cross-listing because Warren should not guess ticker identity.

## Yahoo Finance via yfinance

Provider: `YahooEvidenceProvider`

Reference:

- https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.html

Current use:

- recent news headlines;
- EPS trend (`current`, 7/30/60/90 days ago);
- EPS revision counts (up/down over 7/30 days);
- analyst count and earnings-growth estimate fields;
- revenue-growth estimate fields;
- recent earnings actual vs estimate / surprise history.

Authentication:

- none in the current development adapter.

Important limitations:

- Yahoo/yfinance is a development source, not an SLA-backed production market-data contract.
- Field availability varies by security and geography.
- News evidence is headline-level only; full article text is not retrieved by this provider.
- Estimate history must not be treated as point-in-time historical data for backtests unless it was actually captured at that historical time.

## FRED

This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis. Use of FRED data is subject to the [FRED API Terms of Use](https://fred.stlouisfed.org/docs/api/terms_of_use.html).

Provider: `FredMacroEvidenceProvider`

Official reference:

- https://fred.stlouisfed.org/docs/api/fred/series_observations.html

Current series:

- `DGS10` — US 10-year Treasury yield;
- `DFF` — effective federal funds rate;
- `UNRATE` — US unemployment rate;
- `CPIAUCSL` — US Consumer Price Index.

Authentication:

- `FRED_API_KEY` is required by FRED;
- when absent, Warren records FRED as `unavailable` and continues Deep without macro evidence.

Important limitations:

- the initial macro packet is generic and US-centric;
- macro sensitivity differs by sector/company;
- Warren does not currently turn these observations into deterministic Screen factors.

## Market metrics

Provider: `YFinanceMarketDataProvider`

Current metrics include price, valuation multiples, cash flow, growth, margins, returns, leverage/liquidity, beta and moving-average/52-week context.

These feed the deterministic scoring model used by both Screen and Deep.

## Source status

Every evidence provider should report one or more source status records:

- `ok` — expected evidence returned;
- `partial` — provider responded but important/expected fields were sparse;
- `unavailable` — source intentionally could not be used, such as missing optional credentials or unsupported market mapping;
- `error` — provider execution failed.

Clients should expose these states to users when they materially affect confidence.

## Production migration

Before production commercialization, data-provider selection should be revisited for:

- commercial licensing/terms;
- point-in-time history;
- Canadian/international coverage;
- corporate actions and identifier mapping;
- estimate-revision history;
- full-text filings and earnings releases;
- licensed news content;
- latency/SLA/support;
- cost at expected volume.
