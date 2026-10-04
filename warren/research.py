"""Bounded, source-checked reviews; interpretation never changes scoring."""
from datetime import UTC, datetime
from math import isfinite

from .models import DeepAnalysis, EvidenceBundle, MetricSnapshot, SavedThesis, ThesisCheck


def finalize_research_review(
    analysis: DeepAnalysis, evidence: EvidenceBundle,
    metrics: MetricSnapshot, saved_thesis: SavedThesis | None,
) -> DeepAnalysis:
    review = analysis.research_review.model_copy(deep=True)
    review.version = "research-review-v1"
    review.reviewed_at = datetime.now(UTC)
    review.saved_thesis = saved_thesis
    claims = {item.id: item for item in evidence.claims}
    checks = {item.statement_index: item for item in review.thesis_checks}
    clean_checks = []
    for index, _ in enumerate(saved_thesis.statements if saved_thesis else []):
        item = checks.get(index)
        usable = [cid for cid in (item.claim_ids if item else []) if cid in claims
                  and claims[cid].retrieval_depth in {"structured", "excerpt", "full_text"}]
        quote = item.evidence_quote.strip() if item else ""
        verified = len(quote) >= 12 and any(quote in claims[cid].claim for cid in usable)
        if not item or item.status == "unresolved" or not verified:
            clean_checks.append(ThesisCheck(
                statement_index=index, status="unresolved",
                explanation="The supplied evidence does not establish a source-backed assessment of this statement.",
            ))
        else:
            clean_checks.append(item.model_copy(update={"claim_ids": usable}))
    review.thesis_checks = clean_checks

    changes = []
    for item in review.language_changes:
        current, previous = claims.get(item.current_claim_id), claims.get(item.previous_claim_id)
        if not current or not previous or current.category != "earnings_call" or previous.category != "earnings_call":
            continue
        cq, pq = current.metadata.get("quarter", ""), previous.metadata.get("quarter", "")
        if not cq or not pq or cq <= pq:
            continue
        if item.current_quote not in current.metadata.get("answer", ""):
            continue
        if item.previous_quote not in previous.metadata.get("answer", ""):
            continue
        changes.append(item)
    review.language_changes = changes

    gaps = [f"{item.source}: {item.status}." for item in evidence.source_status if item.status != "ok"]
    if not any(c.retrieval_depth == "full_text" and c.authority_tier == 1 for c in evidence.claims):
        gaps.append("Readable primary filing passages were not available in this research packet.")
    quarters = sorted({q.quarter for q in evidence.earnings_call_qa}, reverse=True)
    if len(quarters) < 2:
        gaps.append("Comparable current and previous earnings-call excerpts are unavailable; management language changes cannot be established.")
    if not saved_thesis:
        gaps.append("No saved company thesis was supplied. Save your view to enable statement-by-statement review.")
    gaps.append("Broker-level research explaining individual analyst target disagreements is not supplied.")
    review.missing_evidence = list(dict.fromkeys(gaps))

    low, median, high = metrics.analyst_target_low, metrics.analyst_target_median, metrics.analyst_target_high
    valid = all(v is not None and isfinite(v) for v in (low, median, high))
    valid = valid and 0 < low <= median <= high
    review.analyst_context = {
        "available": bool(valid), "source": "Yahoo Finance", "as_of": metrics.fetched_at.isoformat() if metrics.fetched_at else None,
        "low": low if valid else None, "median": median if valid else None, "high": high if valid else None,
        "range_as_fraction_of_median": (high - low) / median if valid else None,
        "analyst_count": metrics.analyst_opinion_count,
        "interpretation": "Target dispersion shows variation in estimates; it does not establish the reasons analysts disagree.",
    }
    if not valid:
        review.missing_evidence.append("A complete, consistently ordered analyst target range is unavailable.")
    history = sorted(evidence.earnings_history, key=lambda item: item.period.isoformat() if item.period else "", reverse=True)
    latest = history[0] if history else None
    if not latest or latest.eps_actual is None or latest.eps_estimate is None:
        review.missing_evidence.append("Comparable reported EPS and consensus observations are unavailable.")
    review.earnings_context = {
        "call_quarters": quarters, "coverage": "bounded Q&A excerpts, not complete transcripts",
        "latest_reported_eps": latest.eps_actual if latest else None,
        "consensus_eps": latest.eps_estimate if latest else None,
        "eps_difference": latest.eps_actual - latest.eps_estimate if latest and latest.eps_actual is not None and latest.eps_estimate is not None else None,
        "reported_period": latest.period.isoformat() if latest and latest.period else None,
    }
    review.limitations = [
        "Thesis assessments are model interpretations. Exact quote and claim checks do not independently verify the interpretation.",
        "Source references and dates come from the supplied providers. No complete historical pre-announcement consensus snapshot is guaranteed.",
        "Call excerpts cannot establish that a topic was omitted from an entire transcript or reveal management motives.",
        "Six-month analyst target history is not backfilled. Research history begins when reports are saved in this browser.",
    ]
    if saved_thesis:
        review.limitations.append("The saved thesis timestamp is browser-supplied; this comparison is research, not a validated historical backtest.")
    return analysis.model_copy(update={"research_review": review})
