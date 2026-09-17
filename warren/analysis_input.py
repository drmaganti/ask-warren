from __future__ import annotations

from typing import Any

from .models import CategoryScores, EvidenceBundle, MetricSnapshot


ANALYSIS_INPUT_VERSION = "semantic-v1"


def analysis_input_payload(
    metrics: MetricSnapshot,
    scores: CategoryScores,
    evidence: EvidenceBundle,
) -> dict[str, Any]:
    """Return the exact, stable facts supplied to the synthesis provider.

    Retrieval timestamps are intentionally excluded. A provider refresh that
    returns the same facts should not spend another model call.
    """
    # Imported lazily to keep this shared cache utility independent from the
    # deep-provider package initialization order.
    from .deep.drivers import earnings_bridge

    by_category: dict[str, list] = {}
    for claim in sorted(evidence.claims, key=lambda item: (item.authority_tier, -item.independent_source_count)):
        group = by_category.setdefault(claim.category, [])
        if len(group) < 4:
            group.append(claim)

    compact_claims = []
    for claims in by_category.values():
        for claim in claims:
            item = {
                "id": claim.id,
                "category": claim.category,
                "claim": claim.claim[:1800],
                "as_of": claim.as_of.isoformat() if claim.as_of and claim.category != "metric" else None,
                "authority_tier": claim.authority_tier,
                "retrieval_depth": claim.retrieval_depth,
                "confidence": claim.confidence,
                "independent_source_count": claim.independent_source_count,
                "duplicate_count": claim.duplicate_count,
                "references": [reference.model_dump(exclude_none=True, mode="json") for reference in claim.references[:2]],
            }
            compact_claims.append(item)

    metadata = {
        key: value for key, value in evidence.metadata.items()
        if key in {"sec_cik", "sec_filing_transport", "sec_rag", "earnings_call", "evidence_router"}
    }
    if isinstance(metadata.get("evidence_router"), dict):
        metadata["evidence_router"] = {
            key: value for key, value in metadata["evidence_router"].items()
            if key not in {"collected_at", "evidence_version"}
        }

    return {
        "input_version": ANALYSIS_INPUT_VERSION,
        "metrics": metrics.model_dump(exclude={"fetched_at"}, exclude_none=True, mode="json"),
        "scores": scores.model_dump(mode="json"),
        "earnings_bridge": earnings_bridge(metrics),
        "evidence": {
            "claims": compact_claims,
            "source_status": [item.model_dump(exclude_none=True, mode="json") for item in evidence.source_status],
            "metadata": metadata,
        },
    }
