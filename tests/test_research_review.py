from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.models import AnalyzeRequest
from tests.test_engine import FakeMarketData, FakeEvidence, FakeDeepAnalysis
from warren.analysis_input import analysis_input_payload
from warren.cache import CachedDeepAnalysisProvider
from warren.engine import Warren
from warren.models import (
    DeepAnalysis, EvidenceBundle, EvidenceClaim, MetricSnapshot, ResearchReview,
    SavedThesis, ThesisCheck, LanguageChange, CategoryScores,
)
from warren.research import finalize_research_review


def baseline():
    return SavedThesis(statements=["Margins will improve."], invalidation_conditions=["Two quarters of falling margin."], saved_at=datetime.now(UTC))


def analysis(review=None):
    return DeepAnalysis(thesis="A research view", positives=[], concerns=[], bull_case=[], bear_case=[], risks=[],
                        what_would_change_view=[], verdict="watch", confidence="low", research_review=review or ResearchReview())


def claim(cid="real", category="sec_fact", depth="structured", quarter=None, answer=None):
    return EvidenceClaim(id=cid, category=category, claim="Operating margin increased to 20 percent.",
                         authority_tier=1, retrieval_depth=depth, confidence="high",
                         metadata={"quarter": quarter, "answer": answer or "Operating margin increased to 20 percent."})


@pytest.mark.parametrize("ids,quote,depth", [(["invented"], "Operating margin increased", "structured"),
                                               (["real"], "Fabricated management quotation", "structured"),
                                               (["real"], "Operating margin increased", "headline")])
def test_unverified_or_headline_thesis_assessment_is_unresolved(ids, quote, depth):
    review = ResearchReview(thesis_checks=[ThesisCheck(statement_index=0, status="supported", explanation="INFERENCE: supports", evidence_quote=quote, claim_ids=ids)])
    result = finalize_research_review(analysis(review), EvidenceBundle(claims=[claim(depth=depth)]), MetricSnapshot(ticker="TEST"), baseline())
    assert result.research_review.thesis_checks[0].status == "unresolved"
    assert result.research_review.thesis_checks[0].claim_ids == []


def test_sourced_thesis_assessment_keeps_original_statement_and_quote():
    review = ResearchReview(thesis_checks=[ThesisCheck(statement_index=0, status="supported", explanation="INFERENCE: reported improvement supports this view.", evidence_quote="Operating margin increased to 20 percent.", claim_ids=["real"])])
    saved = baseline()
    result = finalize_research_review(analysis(review), EvidenceBundle(claims=[claim()]), MetricSnapshot(ticker="TEST"), saved)
    assert result.research_review.saved_thesis == saved
    assert result.research_review.thesis_checks[0].status == "supported"
    assert result.verdict == "watch"


def test_no_baseline_discards_model_generated_thesis_checks():
    review = ResearchReview(thesis_checks=[ThesisCheck(statement_index=0, status="supported", explanation="invented baseline")])
    assert finalize_research_review(analysis(review), EvidenceBundle(), MetricSnapshot(ticker="TEST"), None).research_review.thesis_checks == []


@pytest.mark.parametrize("prior_quarter,prior_quote,expected", [("2026Q2", "Operating margin increased to 20 percent.", 1),
                                                                ("2026Q3", "Operating margin increased to 20 percent.", 0),
                                                                ("2026Q2", "An invented management statement.", 0)])
def test_management_comparison_requires_distinct_quarters_and_exact_answers(prior_quarter, prior_quote, expected):
    review = ResearchReview(language_changes=[LanguageChange(current_claim_id="current", previous_claim_id="prior", current_quote="Operating margin increased to 20 percent.", previous_quote=prior_quote, interpretation="INFERENCE: wording comparison.")])
    evidence = EvidenceBundle(claims=[claim("current", "earnings_call", "excerpt", "2026Q3"), claim("prior", "earnings_call", "excerpt", prior_quarter)])
    assert len(finalize_research_review(analysis(review), evidence, MetricSnapshot(ticker="TEST"), None).research_review.language_changes) == expected


@pytest.mark.parametrize("low,median,high,available", [(80,100,120,True),(None,100,120,False),(0,0,0,False),(120,100,80,False)])
def test_target_context_does_not_turn_missing_or_invalid_targets_into_prices(low, median, high, available):
    metrics = MetricSnapshot(ticker="TEST", analyst_target_low=low, analyst_target_median=median, analyst_target_high=high)
    review = finalize_research_review(analysis(), EvidenceBundle(), metrics, None).research_review
    assert review.analyst_context["available"] is available
    if available:
        assert review.analyst_context["range_as_fraction_of_median"] == pytest.approx(.4)
    else:
        assert review.analyst_context["low"] is None


def test_baseline_validation_rejects_unbounded_text_future_and_naive_dates():
    for updates in ({"statements":["x"*501]}, {"saved_at":datetime.now()}, {"saved_at":datetime.now(UTC)+timedelta(days=1)}):
        with pytest.raises(ValidationError):
            SavedThesis.model_validate({**baseline().model_dump(), **updates})
    with pytest.raises(ValidationError):
        AnalyzeRequest(mode="screen", tickers=["TEST"], saved_thesis=baseline())


@pytest.mark.asyncio
async def test_personal_thesis_is_request_scoped_and_invalidates_semantic_cache():
    raw = FakeEvidence().fetch_evidence("GOOD", MetricSnapshot(ticker="GOOD"))
    class SharedEvidence:
        def fetch_evidence(self, ticker, metrics):
            return raw
    provider = FakeDeepAnalysis()
    cached = CachedDeepAnalysisProvider(provider)
    engine = Warren(FakeMarketData(), deep_analysis=cached, evidence=SharedEvidence())
    saved = baseline()
    first = await engine.deep("GOOD", saved_thesis=saved)
    await engine.deep("GOOD", saved_thesis=saved)
    assert provider.calls == 1
    assert first.analysis.research_review.saved_thesis == saved
    await engine.deep("GOOD")
    assert provider.calls == 2
    assert "saved_thesis" not in raw.metadata


def test_api_accepts_saved_thesis_and_returns_review(monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, "engine", Warren(FakeMarketData(), deep_analysis=FakeDeepAnalysis(), evidence=FakeEvidence()))
    response = TestClient(main.app).post("/v1/analyze", json={"mode":"deep", "ticker":"GOOD", "saved_thesis":baseline().model_dump(mode="json")})
    assert response.status_code == 200
    review = response.json()["analysis"]["research_review"]
    assert review["saved_thesis"]["statements"] == ["Margins will improve."]
    assert review["thesis_checks"][0]["status"] == "unresolved"
    assert review["missing_evidence"]


def test_prior_transcript_error_preserves_current_excerpts(monkeypatch):
    from tests.test_evidence import StubEarningsCallProvider
    monkeypatch.setattr("warren.evidence.earnings_calls.time.sleep", lambda seconds: None)
    class LimitedProvider(StubEarningsCallProvider):
        def _request(self, ticker, quarter):
            if quarter == "2026Q2":
                raise RuntimeError("Provider quota exceeded")
            return super()._request(ticker, quarter)
    result = LimitedProvider(api_key="test").fetch_evidence("TEST", MetricSnapshot(ticker="TEST"))
    assert len(result.earnings_call_qa) == 1
    assert result.earnings_call_qa[0].quarter == "2026Q3"
    assert any(s.source == "Prior earnings-call excerpts" and s.status == "unavailable" for s in result.source_status)


def test_compact_packet_keeps_both_quarters():
    claims = [claim(f"{quarter}-{i}", "earnings_call", "excerpt", quarter) for quarter in ["2026Q3","2026Q2"] for i in range(6)]
    scores = CategoryScores(**dict.fromkeys(["fundamentals","valuation","business_quality","growth","risk_resilience","market_context","overall"],50))
    packet = analysis_input_payload(MetricSnapshot(ticker="TEST"), scores, EvidenceBundle(claims=claims))
    assert len(packet["evidence"]["claims"]) == 8
    assert {c["quarter"] for c in packet["evidence"]["claims"]} == {"2026Q3","2026Q2"}
