from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class MetricComparison(BaseModel):
    metric: str
    label: str
    unit: Literal["money", "percent"]
    current: float
    current_period: date | None = None
    previous_quarter: float | None = None
    previous_period: date | None = None
    year_ago: float | None = None
    year_ago_period: date | None = None
    peer_median: float | None = None
    peer_group: str | None = None


class MetricSnapshot(BaseModel):
    ticker: str
    company_name: str | None = None
    sector: str | None = None
    industry: str | None = None
    currency: str | None = None
    price: float | None = None
    market_cap: float | None = None
    total_revenue: float | None = None
    trailing_pe: float | None = None
    forward_pe: float | None = None
    peg_ratio: float | None = None
    price_to_book: float | None = None
    enterprise_to_ebitda: float | None = None
    free_cash_flow: float | None = None
    operating_cash_flow: float | None = None
    total_cash: float | None = None
    total_debt: float | None = None
    shares_outstanding: float | None = None
    fetched_at: datetime | None = None
    most_recent_quarter: date | None = None
    fiscal_year_end: date | None = None
    historical_free_cash_flow: list[float] = Field(default_factory=list)
    quarterly_comparisons: list[MetricComparison] = Field(default_factory=list)
    revenue_growth: float | None = None
    earnings_growth: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    profit_margin: float | None = None
    return_on_equity: float | None = None
    return_on_assets: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    beta: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    fifty_day_average: float | None = None
    two_hundred_day_average: float | None = None


class CategoryScores(BaseModel):
    fundamentals: float
    valuation: float
    business_quality: float
    growth: float
    risk_resilience: float
    market_context: float
    overall: float


class ScreenResult(BaseModel):
    ticker: str
    company_name: str | None = None
    sector: str | None = None
    price: float | None = None
    scores: CategoryScores
    missing_data_count: int = 0


class ScreenRequest(BaseModel):
    tickers: list[str] = Field(min_length=1, max_length=1000)
    top_n: int = Field(default=25, ge=1, le=100)
    min_score: float = Field(default=0, ge=0, le=100)


class ScreenResponse(BaseModel):
    screened_count: int
    failed_tickers: list[str] = Field(default_factory=list)
    results: list[ScreenResult] = Field(default_factory=list)


class SourceStatus(BaseModel):
    source: str
    status: Literal["ok", "partial", "unavailable", "error"]
    detail: str | None = None


class FilingEvidence(BaseModel):
    form: str
    filed_at: date | None = None
    accession_number: str | None = None
    primary_document: str | None = None
    url: str | None = None
    source: str = "SEC EDGAR"


class SecFactEvidence(BaseModel):
    concept: str
    label: str
    value: float
    unit: str
    period_end: date | None = None
    filed_at: date | None = None
    fiscal_period: str | None = None
    form: str | None = None
    accession_number: str | None = None
    url: str | None = None
    source: str = "SEC EDGAR XBRL"


class NewsEvidence(BaseModel):
    title: str
    publisher: str | None = None
    published_at: datetime | None = None
    url: str | None = None
    source: str = "Yahoo Finance"


class WebEvidence(BaseModel):
    title: str
    url: str
    published_at: datetime | None = None
    author: str | None = None
    highlights: list[str] = Field(default_factory=list)
    query: str | None = None
    source: str = "Exa"


class EstimateRevisionEvidence(BaseModel):
    horizon: str
    analyst_count: int | None = None
    eps_current: float | None = None
    eps_7d_ago: float | None = None
    eps_30d_ago: float | None = None
    eps_60d_ago: float | None = None
    eps_90d_ago: float | None = None
    eps_up_7d: int | None = None
    eps_down_7d: int | None = None
    eps_up_30d: int | None = None
    eps_down_30d: int | None = None
    earnings_growth: float | None = None
    revenue_growth: float | None = None
    source: str = "Yahoo Finance"


class EarningsHistoryEvidence(BaseModel):
    period: datetime | None = None
    eps_estimate: float | None = None
    eps_actual: float | None = None
    eps_difference: float | None = None
    surprise_percent: float | None = None
    source: str = "Yahoo Finance"


class EarningsCallQAEvidence(BaseModel):
    quarter: str
    analyst: str | None = None
    analyst_title: str | None = None
    question: str
    responder: str | None = None
    responder_title: str | None = None
    answer: str
    source_url: str = "https://www.alphavantage.co/documentation/#earnings-call-transcript"
    source: str = "Alpha Vantage earnings-call transcript"


class TechnicalEvidence(BaseModel):
    as_of: date | None = None
    close: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    rsi_14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    bollinger_upper_20: float | None = None
    bollinger_lower_20: float | None = None
    latest_volume: float | None = None
    avg_volume_20: float | None = None
    source: str = "Yahoo Finance"


class InsiderTransactionEvidence(BaseModel):
    insider: str | None = None
    position: str | None = None
    transaction: str | None = None
    start_date: date | datetime | None = None
    shares: float | None = None
    value: float | None = None
    ownership: str | None = None
    source: str = "Yahoo Finance"


class MacroEvidence(BaseModel):
    series_id: str
    label: str
    value: float
    prior_value: float | None = None
    prior_period: str | None = None
    as_of: date | None = None
    units: str | None = None
    source: str = "FRED"


class EvidenceReference(BaseModel):
    source: str
    publisher: str | None = None
    url: str | None = None
    authority_tier: Literal[1, 2, 3, 4, 5]
    retrieval_depth: Literal["metadata", "headline", "structured", "excerpt", "full_text"]


class EvidenceClaim(BaseModel):
    id: str
    category: Literal["filing", "sec_fact", "news", "estimate_revision", "earnings", "earnings_call", "technical", "insider", "macro", "web"]
    claim: str
    as_of: date | datetime | None = None
    authority_tier: Literal[1, 2, 3, 4, 5]
    retrieval_depth: Literal["metadata", "headline", "structured", "excerpt", "full_text"]
    confidence: Literal["low", "medium", "high"]
    references: list[EvidenceReference] = Field(default_factory=list)
    independent_source_count: int = 1
    duplicate_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceBundle(BaseModel):
    collected_at: datetime | None = None
    evidence_version: str | None = None
    filings: list[FilingEvidence] = Field(default_factory=list)
    sec_facts: list[SecFactEvidence] = Field(default_factory=list)
    news: list[NewsEvidence] = Field(default_factory=list)
    web: list[WebEvidence] = Field(default_factory=list)
    estimate_revisions: list[EstimateRevisionEvidence] = Field(default_factory=list)
    earnings_history: list[EarningsHistoryEvidence] = Field(default_factory=list)
    earnings_call_qa: list[EarningsCallQAEvidence] = Field(default_factory=list)
    technical: list[TechnicalEvidence] = Field(default_factory=list)
    insider_transactions: list[InsiderTransactionEvidence] = Field(default_factory=list)
    macro: list[MacroEvidence] = Field(default_factory=list)
    claims: list[EvidenceClaim] = Field(default_factory=list)
    source_status: list[SourceStatus] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def merge(self, other: "EvidenceBundle") -> "EvidenceBundle":
        return EvidenceBundle(
            collected_at=max(filter(None, (self.collected_at, other.collected_at)), default=None),
            filings=[*self.filings, *other.filings],
            sec_facts=[*self.sec_facts, *other.sec_facts],
            news=[*self.news, *other.news],
            web=[*self.web, *other.web],
            estimate_revisions=[*self.estimate_revisions, *other.estimate_revisions],
            earnings_history=[*self.earnings_history, *other.earnings_history],
            earnings_call_qa=[*self.earnings_call_qa, *other.earnings_call_qa],
            technical=[*self.technical, *other.technical],
            insider_transactions=[*self.insider_transactions, *other.insider_transactions],
            macro=[*self.macro, *other.macro],
            claims=[*self.claims, *other.claims],
            source_status=[*self.source_status, *other.source_status],
            metadata={**self.metadata, **other.metadata},
        )


class AnalysisCitation(BaseModel):
    section: Literal["thesis", "positives", "concerns", "bull_case", "bear_case", "risks", "what_would_change_view"]
    item_index: int = Field(ge=0)
    claim_ids: list[str] = Field(default_factory=list)


class InvestmentInsight(BaseModel):
    """An evidence-backed interpretation presented in Bull or Bear."""

    headline: str
    lens: Literal[
        "future_demand", "earnings_quality", "operating_leverage",
        "capital_allocation", "market_expectations", "market_positioning",
        "company_risk", "other",
    ] = "other"
    finding: str
    cause: str
    durability: Literal["recurring", "temporary", "one_time", "unresolved"]
    time_horizon: Literal["near_term", "medium_term", "long_term", "unresolved"]
    investor_implication: str
    expectation_gap: str | None = None
    scenario_path: str | None = None
    what_to_watch: list[str] = Field(min_length=1)
    catalyst: str | None = None
    likelihood: Literal["low", "medium", "high", "unresolved"] = "unresolved"
    impact: Literal["low", "medium", "high", "unresolved"] = "unresolved"
    confidence: Literal["low", "medium", "high"]
    claim_ids: list[str] = Field(default_factory=list)


class DeepAnalysis(BaseModel):
    thesis: str
    positives: list[str]
    concerns: list[str]
    bull_case: list[str]
    bear_case: list[str]
    risks: list[str]
    what_would_change_view: list[str]
    verdict: str
    confidence: Literal["low", "medium", "high"]
    citations: list[AnalysisCitation] = Field(default_factory=list)
    bull_insights: list[InvestmentInsight] = Field(default_factory=list)
    bear_insights: list[InvestmentInsight] = Field(default_factory=list)


class DcfScenario(BaseModel):
    name: Literal["bear", "base", "bull"]
    forecast_years: int
    fcf_growth: float
    revenue_growth: float
    starting_fcf_margin: float
    ending_fcf_margin: float
    discount_rate: float
    terminal_growth: float
    fair_value_per_share: float
    upside_downside: float | None = None
    assumption_basis: str


class DcfSensitivityPoint(BaseModel):
    discount_rate: float
    terminal_growth: float
    fair_value_per_share: float


class DiscountRateDetails(BaseModel):
    method: str
    risk_free_rate: float
    equity_risk_premium: float
    beta: float
    cost_of_equity: float
    pre_tax_cost_of_debt: float
    tax_rate: float
    equity_weight: float
    debt_weight: float
    calculated_wacc: float
    applied_discount_rate: float
    assumption_basis: list[str] = Field(default_factory=list)


class DcfResult(BaseModel):
    status: Literal["available", "unavailable"]
    methodology_version: str
    reason: str | None = None
    base_free_cash_flow: float | None = None
    normalization_method: str | None = None
    discount_rate_details: DiscountRateDetails | None = None
    net_cash: float | None = None
    shares_outstanding: float | None = None
    current_price: float | None = None
    input_source: str
    input_as_of: datetime | None = None
    scenarios: list[DcfScenario] = Field(default_factory=list)
    sensitivity: list[DcfSensitivityPoint] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class DeepResponse(BaseModel):
    ticker: str
    metrics: MetricSnapshot
    scores: CategoryScores
    dcf: DcfResult
    evidence: EvidenceBundle = Field(default_factory=EvidenceBundle)
    missing_data: list[str] = Field(default_factory=list)
    analysis: DeepAnalysis
    model: str | None = None
    disclaimer: str = "For research purposes only. Not financial advice."
