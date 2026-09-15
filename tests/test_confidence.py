from datetime import datetime, timezone

from warren.confidence import assess_analysis_confidence
from warren.models import (
    AnalysisCitation,
    DeepAnalysis,
    EvidenceBundle,
    EvidenceClaim,
    InvestmentInsight,
    MetricSnapshot,
)


def _insight(headline: str, claim_id: str) -> InvestmentInsight:
    return InvestmentInsight(
        headline=headline,
        finding="Supported finding",
        cause="Supported cause",
        durability="recurring",
        time_horizon="medium_term",
        investor_implication="Investment implication",
        what_to_watch=["Observable signal"],
        confidence="high",
        claim_ids=[claim_id],
    )


def _analysis() -> DeepAnalysis:
    return DeepAnalysis(
        thesis="Evidence-backed thesis",
        positives=["positive"],
        concerns=["concern"],
        bull_case=["bull"],
        bear_case=["bear"],
        risks=["risk"],
        what_would_change_view=["change"],
        verdict="watch",
        confidence="medium",
        citations=[AnalysisCitation(section="thesis", item_index=0, claim_ids=["primary"])],
        bull_insights=[_insight("Bull point", "primary")],
        bear_insights=[_insight("Bear point", "secondary")],
    )


def _complete_metrics() -> MetricSnapshot:
    return MetricSnapshot(
        ticker="TEST", trailing_pe=20, forward_pe=18, free_cash_flow=100,
        revenue_growth=.1, earnings_growth=.12, operating_margin=.2,
        return_on_equity=.25, debt_to_equity=40, current_ratio=1.5,
    )


def test_claim_weighted_confidence_rewards_supported_current_primary_evidence():
    now = datetime(2026, 9, 15, tzinfo=timezone.utc)
    evidence = EvidenceBundle(
        collected_at=now,
        claims=[
            EvidenceClaim(
                id=claim_id, category="sec_fact", claim="Reported fact", as_of=now,
                authority_tier=1, retrieval_depth="structured", confidence="high",
                independent_source_count=2,
            )
            for claim_id in ("primary", "secondary")
        ],
    )

    result = assess_analysis_confidence(_analysis(), evidence, _complete_metrics())

    assert result.confidence == "high"
    assert result.confidence_score is not None and result.confidence_score >= 80
    assert "3 of 3 key investment points" in result.confidence_reasons[0]
    assert any("independently corroborated" in reason for reason in result.confidence_reasons)


def test_claim_weighted_confidence_exposes_missing_support_and_inputs():
    result = assess_analysis_confidence(
        _analysis(),
        EvidenceBundle(collected_at=datetime(2026, 9, 15, tzinfo=timezone.utc)),
        MetricSnapshot(ticker="TEST"),
    )

    assert result.confidence == "low"
    assert result.confidence_score is not None and result.confidence_score < 60
    assert any("lack cited support" in gap for gap in result.confidence_gaps)
    assert any("financial inputs" in gap for gap in result.confidence_gaps)
