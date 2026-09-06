# Changelog

All notable product/module changes should be recorded here.

## Unreleased

- Fall back to deterministic synthesis when Gemini is unavailable or its free quota is exhausted.

### Added

- Official SEC company-facts retrieval for selected US-GAAP XBRL fundamentals with period, form, filing date and accession provenance.
- High-confidence normalized evidence claims for SEC XBRL facts and an Analyze-page fundamentals panel.
- Deterministic evidence fingerprints and collection timestamps surfaced in every Deep evidence packet and Analyze report.
- Validated claim-level citations connect generated conclusions to inspectable evidence.
- Deterministic five-year DCF engine with Bear/Base/Bull scenarios, per-share values, implied upside/downside and a 3×3 discount-rate/terminal-growth sensitivity grid.
- Explicit DCF unavailable states for missing inputs, non-positive free cash flow and invalid share counts.
- Yahoo Finance snapshot inputs for cash, debt, shares outstanding and retrieval time.
- Multi-year free-cash-flow normalization and bounded forward revenue/earnings growth anchors for DCF scenarios.
- Explicit revenue-growth and FCF-margin paths for every DCF scenario, plus a rendered sensitivity table.
- Company-specific CAPM-style discount rates using beta and capital structure, with explicit configured market assumptions and bounded fallbacks.
- Public Ask Warren methodology page served at `GET /methodology` in the approved dark visual direction.
- User-facing explanation of deterministic scoring, evidence discipline, Bull/Bear/Risk synthesis, verdict confidence and methodology versioning.
- Three-state Ask Warren verdict language: `Attractive`, `Watch`, `Avoid`.
- Transparent deterministic DCF specification with Bear/Base/Bull scenarios, required assumptions and sensitivity guardrails.
- API contract test confirming the methodology page is served and contains the core verdict/DCF concepts.

### Changed

- Deep API responses and the Analyze page now expose the deterministic DCF result, normalization method, assumption basis, source and methodology version.
- DCF methodology advanced to `dcf-v1.0`; application/package version advanced to `0.4.0`.
- Expanded `docs/METHODOLOGY.md` from the initial score description into the full research-methodology contract for Warren and Ask Warren.
- README now distinguishes the reusable Warren engine from the user-facing Ask Warren product and documents the public methodology route.

## v0.3.0

### Added

- Reusable `EvidenceProvider` protocol and typed `EvidenceBundle`.
- `CompositeEvidenceProvider` with per-source failure isolation.
- Official SEC EDGAR recent filing metadata provider for exact US ticker mappings.
- Yahoo/yfinance recent headline evidence.
- Yahoo/yfinance EPS trend and revision-count evidence.
- Yahoo/yfinance forward earnings/revenue growth estimate fields and recent earnings surprise history.
- Optional FRED macro evidence with explicit unavailable state when `FRED_API_KEY` is absent.
- Deep API response now returns the exact evidence packet used for synthesis.
- Deep prompts explicitly prevent inference of filing contents from metadata and article contents from headlines.
- Evidence-provider resilience tests.
- Data-source documentation and v0.3 methodology/evaluation updates.

### Changed

- `DeepAnalysisProvider.analyze` now receives `EvidenceBundle` in addition to metrics and deterministic scores.
- Warren Deep gathers evidence before Bull/Bear/Risk synthesis.
- Evidence source failures degrade gracefully and are returned through `source_status` rather than automatically failing Deep.
- API/package version advanced to `0.3.0`.

### Known limitations

- scoring thresholds/weights are not yet calibrated as predictive investment signals;
- SEC evidence is filing metadata, not filing-content extraction;
- Yahoo news evidence is headline-level, not full-article retrieval;
- Canadian SEDAR+ filing evidence is not yet implemented;
- FRED context is optional and generic/US-centric;
- Yahoo Finance is a development data source rather than a production SLA-backed feed;
- Warren is an internal working name pending legal trademark clearance.

## v0.2.0

### Added

- Warren reusable stock-intelligence package.
- `screen` mode for deterministic, LLM-free universe ranking.
- `deep` mode for one-company Bull/Bear/Risk/final synthesis.
- Replaceable `MarketDataProvider` and `DeepAnalysisProvider` interfaces.
- Yahoo Finance development adapter.
- Gemini deep-analysis adapter.
- FastAPI `/v1/analyze` adapter.
- Offline engine and API-contract tests.
- GitHub Actions test workflow.
- Product, architecture, API, methodology, integration, evaluation, risk, roadmap, security and naming documentation.
