from __future__ import annotations

import json

from warren.deep.gemini import GeminiDeepAnalysisProvider
from warren.models import CategoryScores, EvidenceBundle, EvidenceClaim, EvidenceReference, MetricSnapshot, WebEvidence


def test_gemini_packet_uses_bounded_normalized_claims_not_raw_evidence():
    long_text = "material filing evidence " * 1000
    claims = [
        EvidenceClaim(
            id=f"web:{index}", category="web", claim=long_text,
            authority_tier=1, retrieval_depth="full_text", confidence="high",
            references=[EvidenceReference(source="SEC EDGAR", authority_tier=1, retrieval_depth="full_text")],
        )
        for index in range(10)
    ]
    evidence = EvidenceBundle(
        web=[WebEvidence(title="raw duplicate", url="https://www.sec.gov/test", highlights=[long_text])],
        claims=claims,
    )
    scores = CategoryScores(fundamentals=50, valuation=50, business_quality=50, growth=50, risk_resilience=50, market_context=50, overall=50)

    packet = json.loads(GeminiDeepAnalysisProvider._evidence(MetricSnapshot(ticker="TEST"), scores, evidence))

    assert "web" not in packet["evidence"]
    assert len(packet["evidence"]["claims"]) == 4
    assert all(len(item["claim"]) <= 1800 for item in packet["evidence"]["claims"])
    assert len(json.dumps(packet)) < 12_000
