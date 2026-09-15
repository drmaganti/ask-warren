from __future__ import annotations

from datetime import date, datetime, timezone

from .models import DeepAnalysis, EvidenceBundle, EvidenceClaim, MetricSnapshot


_AUTHORITY = {1: 1.0, 2: 0.88, 3: 0.70, 4: 0.48, 5: 0.28}
_DEPTH = {"full_text": 1.0, "structured": 0.92, "excerpt": 0.82, "headline": 0.48, "metadata": 0.32}
_CLAIM_CONFIDENCE = {"high": 1.0, "medium": 0.72, "low": 0.42}
_CRITICAL_METRICS = (
    "trailing_pe", "forward_pe", "free_cash_flow", "revenue_growth",
    "earnings_growth", "operating_margin", "return_on_equity",
    "debt_to_equity", "current_ratio",
)


def _age_days(value: date | datetime | None, reference: datetime) -> int | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        moment = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    else:
        moment = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return max(0, (reference - moment.astimezone(timezone.utc)).days)


def _freshness(claim: EvidenceClaim, reference: datetime) -> float:
    age = _age_days(claim.as_of, reference)
    if age is None:
        return 0.62
    if claim.category in {"filing", "sec_fact", "earnings"}:
        return 1.0 if age <= 120 else 0.82 if age <= 400 else 0.48
    if claim.category in {"technical", "news", "web", "insider"}:
        return 1.0 if age <= 14 else 0.78 if age <= 60 else 0.40
    return 1.0 if age <= 60 else 0.80 if age <= 180 else 0.48


def _key_claim_groups(analysis: DeepAnalysis) -> list[list[str]]:
    groups: list[list[str]] = []
    thesis_ids = [
        claim_id
        for citation in analysis.citations
        if citation.section == "thesis"
        for claim_id in citation.claim_ids
    ]
    if thesis_ids:
        groups.append(list(dict.fromkeys(thesis_ids)))
    for insight in [*analysis.bull_insights[:3], *analysis.bear_insights[:3]]:
        groups.append(list(dict.fromkeys(insight.claim_ids)))
    return groups


def assess_analysis_confidence(
    analysis: DeepAnalysis,
    evidence: EvidenceBundle,
    metrics: MetricSnapshot,
) -> DeepAnalysis:
    """Calculate confidence from the evidence behind the visible investment view."""
    claims = {claim.id: claim for claim in evidence.claims}
    groups = _key_claim_groups(analysis)
    supported_groups = [group for group in groups if any(claim_id in claims for claim_id in group)]
    cited = list(dict.fromkeys(
        claim_id for group in supported_groups for claim_id in group if claim_id in claims
    ))
    cited_claims = [claims[claim_id] for claim_id in cited]

    coverage = len(supported_groups) / len(groups) if groups else 0.0
    if cited_claims:
        quality = sum(
            _AUTHORITY[claim.authority_tier]
            * _DEPTH[claim.retrieval_depth]
            * _CLAIM_CONFIDENCE[claim.confidence]
            for claim in cited_claims
        ) / len(cited_claims)
        corroboration = sum(
            1.0 if claim.independent_source_count >= 3 else 0.84 if claim.independent_source_count == 2 else 0.58
            for claim in cited_claims
        ) / len(cited_claims)
        reference = evidence.collected_at or datetime.now(timezone.utc)
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)
        freshness = sum(_freshness(claim, reference) for claim in cited_claims) / len(cited_claims)
    else:
        quality = corroboration = freshness = 0.0

    present_metrics = sum(getattr(metrics, name) is not None for name in _CRITICAL_METRICS)
    completeness = present_metrics / len(_CRITICAL_METRICS)
    score = round(30 * coverage + 25 * quality + 20 * corroboration + 15 * freshness + 10 * completeness)

    unresolved = sum(
        insight.durability == "unresolved" or insight.time_horizon == "unresolved"
        for insight in [*analysis.bull_insights[:3], *analysis.bear_insights[:3]]
    )
    if unresolved:
        score -= min(8, unresolved * 2)
    score = max(0, min(100, score))
    level = "high" if score >= 80 else "medium" if score >= 60 else "low"

    reasons: list[str] = []
    gaps: list[str] = []
    if groups:
        reasons.append(f"{len(supported_groups)} of {len(groups)} key investment points have cited support.")
    else:
        gaps.append("The investment view does not identify cited, thesis-driving points.")
    strong_claims = sum(claim.authority_tier <= 2 and claim.retrieval_depth in {"structured", "excerpt", "full_text"} for claim in cited_claims)
    if strong_claims:
        reasons.append(f"{strong_claims} cited claims use primary or structured evidence.")
    else:
        gaps.append("No key point is backed by primary or structured evidence.")
    corroborated = sum(claim.independent_source_count >= 2 for claim in cited_claims)
    if corroborated:
        reasons.append(f"{corroborated} cited claims are independently corroborated.")
    elif cited_claims:
        gaps.append("Key claims currently rely on one source each.")
    if coverage < 1 and groups:
        gaps.append(f"{len(groups) - len(supported_groups)} key investment points lack cited support.")
    missing_metrics = len(_CRITICAL_METRICS) - present_metrics
    if missing_metrics:
        gaps.append(f"{missing_metrics} important financial inputs are unavailable.")
    if unresolved:
        gaps.append(f"{unresolved} leading insights have an unresolved duration or time horizon.")

    return analysis.model_copy(update={
        "confidence": level,
        "confidence_score": score,
        "confidence_reasons": reasons[:3],
        "confidence_gaps": gaps[:3],
    })
