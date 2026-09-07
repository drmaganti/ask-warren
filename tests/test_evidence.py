from __future__ import annotations

from datetime import UTC, date, datetime

from warren.evidence import (
    AlphaVantageEarningsCallProvider,
    CompositeEvidenceProvider,
    EvidenceRouter,
    ExaWebEvidenceProvider,
    FredMacroEvidenceProvider,
    SecFilingEvidenceProvider,
    SecRagEvidenceProvider,
)
from warren.models import (
    EvidenceBundle,
    FilingEvidence,
    InsiderTransactionEvidence,
    MetricSnapshot,
    NewsEvidence,
    SourceStatus,
    TechnicalEvidence,
    WebEvidence,
)
from warren.evidence.router import _themes


class GoodProvider:
    def fetch_evidence(self, ticker: str, metrics: MetricSnapshot) -> EvidenceBundle:
        return EvidenceBundle(
            news=[NewsEvidence(title="Grounded headline")],
            source_status=[SourceStatus(source="good", status="ok")],
        )


def test_evidence_themes_identify_forward_and_legal_signals():
    themes = _themes("Management lowered demand guidance after a regulatory lawsuit and increased capital expenditure.")

    assert {"demand", "forecast", "legal_regulatory", "investment_capacity"}.issubset(themes)


class BadProvider:
    def fetch_evidence(self, ticker: str, metrics: MetricSnapshot) -> EvidenceBundle:
        raise RuntimeError("boom")


class DuplicateNewsProvider:
    def fetch_evidence(self, ticker: str, metrics: MetricSnapshot) -> EvidenceBundle:
        return EvidenceBundle(
            filings=[
                FilingEvidence(
                    form="10-Q",
                    filed_at=date(2026, 7, 31),
                    accession_number="0000000000-26-000001",
                    url="https://www.sec.gov/example?tracking=1",
                )
            ],
            news=[
                NewsEvidence(
                    title="Company raises full-year guidance",
                    publisher="Publisher A",
                    url="https://example.com/story?utm_source=a",
                ),
                NewsEvidence(
                    title="Company raises full year guidance!",
                    publisher="Publisher B",
                    url="https://example.org/story?utm_source=b",
                ),
            ],
            web=[
                WebEvidence(
                    title="Company investor update",
                    url="https://investor.example.com/update?utm_source=search",
                    highlights=["Management discussed updated demand expectations."],
                    query="company material developments",
                ),
                WebEvidence(
                    title="Duplicate company investor update",
                    url="https://investor.example.com/update?ref=duplicate",
                    highlights=["Management discussed updated demand expectations."],
                    query="company material developments",
                ),
            ],
            technical=[
                TechnicalEvidence(
                    as_of=date(2026, 9, 1),
                    close=100,
                    sma_50=95,
                    sma_200=90,
                    rsi_14=62,
                    macd=1.5,
                    macd_signal=1.2,
                )
            ],
            insider_transactions=[
                InsiderTransactionEvidence(
                    insider="Example Executive",
                    transaction="Sale",
                    start_date=date(2026, 8, 20),
                    shares=1000,
                    value=100000,
                )
            ],
            source_status=[SourceStatus(source="test", status="ok")],
        )


class RagSecProvider:
    def fetch_evidence(self, ticker, metrics):
        return EvidenceBundle(
            filings=[
                FilingEvidence(form="10-Q", filed_at=date(2026, 7, 31), accession_number="new", url="https://www.sec.gov/new.htm"),
                FilingEvidence(form="10-Q", filed_at=date(2026, 4, 30), accession_number="prior", url="https://www.sec.gov/prior.htm"),
            ]
        )


class FakeVector:
    def __init__(self):
        self.replaced = None

    def replace_ticker(self, ticker, chunks):
        self.replaced = (ticker, chunks)

    def query(self, ticker, query):
        return [{
            "id": "sec:AAPL:new:0",
            "data": "Risk factors now identify increased supplier concentration.",
            "metadata": {"form": "10-Q", "filed_at": "2026-07-31", "url": "https://www.sec.gov/new.htm"},
        }]


class StubRagProvider(SecRagEvidenceProvider):
    def _download_chunks(self, ticker, filing):
        return [{"id": f"sec:{ticker}:{filing.accession_number}:0", "data": "filing text", "metadata": {"ticker": ticker}}]


def test_composite_preserves_good_evidence_when_one_source_fails():
    provider = CompositeEvidenceProvider([GoodProvider(), BadProvider()])
    bundle = provider.fetch_evidence("AAPL", MetricSnapshot(ticker="AAPL"))

    assert bundle.news[0].title == "Grounded headline"
    assert any(status.status == "error" for status in bundle.source_status)


def test_evidence_router_normalizes_and_deduplicates_claims():
    provider = EvidenceRouter(DuplicateNewsProvider())
    bundle = provider.fetch_evidence("AAPL", MetricSnapshot(ticker="AAPL"))

    assert len(bundle.news) == 2
    assert len(bundle.web) == 2
    assert len(bundle.claims) == 5

    news_claim = next(claim for claim in bundle.claims if claim.category == "news")
    assert news_claim.retrieval_depth == "headline"
    assert news_claim.authority_tier == 4
    assert news_claim.duplicate_count == 1
    assert news_claim.independent_source_count == 1
    assert news_claim.metadata["publisher_count"] == 2
    assert news_claim.metadata["possible_syndication"] is True
    assert news_claim.confidence == "low"

    filing_claim = next(claim for claim in bundle.claims if claim.category == "filing")
    assert filing_claim.authority_tier == 1
    assert filing_claim.retrieval_depth == "metadata"
    assert filing_claim.metadata["content_retrieved"] is False

    web_claim = next(claim for claim in bundle.claims if claim.category == "web")
    assert web_claim.retrieval_depth == "excerpt"
    assert web_claim.duplicate_count == 1
    assert web_claim.independent_source_count == 1
    assert web_claim.metadata["excerpt_only"] is True

    technical_claim = next(claim for claim in bundle.claims if claim.category == "technical")
    assert technical_claim.confidence == "high"
    assert "14-day RSI 62.0" in technical_claim.claim

    insider_claim = next(claim for claim in bundle.claims if claim.category == "insider")
    assert insider_claim.confidence == "medium"
    assert "Example Executive" in insider_claim.claim

    router_meta = bundle.metadata["evidence_router"]
    assert router_meta["raw_items"] == 7
    assert router_meta["normalized_claims"] == 5
    assert router_meta["deduplicated_items"] == 2
    assert bundle.collected_at is not None
    assert len(bundle.evidence_version) == 16
    assert router_meta["evidence_version"] == bundle.evidence_version


def test_exa_without_key_degrades_to_unavailable(monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    provider = ExaWebEvidenceProvider(api_key=None)

    bundle = provider.fetch_evidence("AAPL", MetricSnapshot(ticker="AAPL", company_name="Apple Inc."))

    assert bundle.web == []
    assert bundle.source_status[0].source == "Exa web discovery"
    assert bundle.source_status[0].status == "unavailable"


def test_fred_without_key_degrades_to_unavailable(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    provider = FredMacroEvidenceProvider(api_key=None)

    bundle = provider.fetch_evidence("AAPL", MetricSnapshot(ticker="AAPL"))

    assert bundle.macro == []
    assert bundle.source_status[0].source == "FRED"
    assert bundle.source_status[0].status == "unavailable"


class StubEarningsCallProvider(AlphaVantageEarningsCallProvider):
    @staticmethod
    def _quarters(now=None):
        return ["2026Q3"]

    def _request(self, ticker, quarter):
        return {"transcript": [
            {"speaker": "Operator", "title": "Operator", "content": "We will begin the question-and-answer session."},
            {"speaker": "A. Analyst", "title": "Research Analyst", "content": "What demand and margin assumptions support guidance?"},
            {"speaker": "C. Executive", "title": "Chief Financial Officer", "content": "We expect transaction growth and sales leverage, while labor investment continues."},
            {"speaker": "B. Analyst", "title": "Research Analyst", "content": "Thank you."},
        ]}


def test_earnings_call_quarter_probe_is_bounded_to_four_recent_quarters():
    quarters = AlphaVantageEarningsCallProvider._quarters(datetime(2026, 9, 1, tzinfo=UTC))

    assert quarters == [
        "2026Q3", "2026Q2", "2026Q1", "2025Q4",
    ]


def test_earnings_call_prefers_company_fiscal_quarter():
    metrics = MetricSnapshot(
        ticker="SBUX",
        most_recent_quarter=date(2025, 6, 29),
        fiscal_year_end=date(2024, 9, 29),
    )

    assert AlphaVantageEarningsCallProvider._fiscal_quarter(metrics) == "2025Q3"


def test_earnings_call_provider_extracts_material_qa_and_router_cites_it():
    provider = StubEarningsCallProvider(api_key="test")
    raw = provider.fetch_evidence("TEST", MetricSnapshot(ticker="TEST"))

    assert len(raw.earnings_call_qa) == 1
    assert raw.earnings_call_qa[0].analyst == "A. Analyst"
    assert "transaction growth" in raw.earnings_call_qa[0].answer
    assert raw.metadata["earnings_call"]["raw_transcript_retained"] is False

    routed = EvidenceRouter(provider).fetch_evidence("TEST", MetricSnapshot(ticker="TEST"))
    claim = next(item for item in routed.claims if item.category == "earnings_call")
    assert "What demand and margin assumptions" in claim.claim
    assert claim.references[0].url


def test_earnings_call_provider_without_key_degrades_to_unavailable(monkeypatch):
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    provider = AlphaVantageEarningsCallProvider(api_key=None)

    bundle = provider.fetch_evidence("AAPL", MetricSnapshot(ticker="AAPL"))

    assert bundle.earnings_call_qa == []
    assert bundle.source_status[0].status == "unavailable"


def test_sec_does_not_guess_cross_listing_for_tsx():
    provider = SecFilingEvidenceProvider()

    bundle = provider.fetch_evidence("RY.TO", MetricSnapshot(ticker="RY.TO"))

    assert bundle.filings == []
    assert bundle.source_status[0].source == "SEC EDGAR"
    assert bundle.source_status[0].status == "unavailable"


def test_sec_can_resolve_cik_from_yahoo_when_sec_ticker_map_is_blocked(monkeypatch):
    class Stock:
        sec_filings = [{"edgarUrl": "https://www.sec.gov/Archives/edgar/data/909832/0000909832-26-000060_909832"}]

    monkeypatch.setattr("warren.evidence.sec.yf.Ticker", lambda symbol: Stock())

    assert SecFilingEvidenceProvider._resolve_cik_from_yahoo("COST") == 909832


def test_sec_extracts_latest_structured_xbrl_facts():
    payload = {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {
                        "USD": [
                            {"val": 90, "end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "accn": "0001-26-000001"},
                            {"val": 100, "end": "2026-06-30", "filed": "2026-08-01", "form": "10-Q", "fp": "Q2", "accn": "0001-26-000002"},
                        ]
                    }
                },
                "NetIncomeLoss": {
                    "units": {"USD": [{"val": 12, "end": "2026-06-30", "filed": "2026-08-01", "form": "10-Q", "fp": "Q2", "accn": "0001-26-000002"}]}
                },
            }
        }
    }

    facts = SecFilingEvidenceProvider._extract_company_facts(payload, 1)

    assert [fact.label for fact in facts] == ["Revenue", "Net income"]
    assert facts[0].value == 100
    assert facts[0].period_end == date(2026, 6, 30)
    assert facts[0].source == "SEC EDGAR XBRL"


def test_sec_rag_replaces_ticker_corpus_and_returns_primary_passages():
    vector = FakeVector()
    provider = StubRagProvider(RagSecProvider(), vector=vector)

    bundle = EvidenceRouter(provider).fetch_evidence("AAPL", MetricSnapshot(ticker="AAPL"))

    assert vector.replaced[0] == "AAPL"
    assert len(vector.replaced[1]) == 2
    assert bundle.metadata["sec_rag"]["retrieved_passages"] == 1
    claim = next(item for item in bundle.claims if item.category == "web")
    assert claim.authority_tier == 1
    assert claim.retrieval_depth == "full_text"
    assert claim.confidence == "high"
    assert claim.metadata["excerpt_only"] is False
