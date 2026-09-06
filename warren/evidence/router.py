from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

from ..models import (
    EarningsHistoryEvidence,
    EarningsCallQAEvidence,
    EstimateRevisionEvidence,
    EvidenceBundle,
    EvidenceClaim,
    EvidenceReference,
    FilingEvidence,
    InsiderTransactionEvidence,
    MacroEvidence,
    MetricSnapshot,
    NewsEvidence,
    SecFactEvidence,
    TechnicalEvidence,
    WebEvidence,
)
from ..protocols import EvidenceProvider


class EvidenceRouter:
    """Normalizes heterogeneous evidence into reusable, deduplicated claims.

    Raw provider objects remain in the EvidenceBundle for transparency and
    backward compatibility. `claims` is the interpretation-ready layer shared by
    Bull, Bear, Risk and Final analysis.
    """

    VERSION = "1.3"

    def __init__(self, upstream: EvidenceProvider):
        self.upstream = upstream

    def fetch_evidence(self, ticker: str, metrics: MetricSnapshot) -> EvidenceBundle:
        bundle = self.upstream.fetch_evidence(ticker, metrics)
        claims, duplicate_count = normalize_claims(bundle)
        bundle.claims = claims
        bundle.collected_at = datetime.now(timezone.utc)
        fingerprint_payload = [claim.model_dump(mode="json") for claim in claims]
        bundle.evidence_version = hashlib.sha256(
            json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:16]
        bundle.metadata["evidence_router"] = {
            "version": self.VERSION,
            "raw_items": _raw_item_count(bundle),
            "normalized_claims": len(claims),
            "deduplicated_items": duplicate_count,
            "claim_categories": sorted({claim.category for claim in claims}),
            "collected_at": bundle.collected_at.isoformat(),
            "evidence_version": bundle.evidence_version,
        }
        return bundle


def _raw_item_count(bundle: EvidenceBundle) -> int:
    return (
        len(bundle.filings)
        + len(bundle.sec_facts)
        + len(bundle.news)
        + len(bundle.web)
        + len(bundle.estimate_revisions)
        + len(bundle.earnings_history)
        + len(bundle.earnings_call_qa)
        + len(bundle.technical)
        + len(bundle.insider_transactions)
        + len(bundle.macro)
    )


def _stable_id(category: str, key: str) -> str:
    digest = hashlib.sha256(f"{category}:{key}".encode("utf-8")).hexdigest()[:16]
    return f"{category}:{digest}"


def _canonical_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parts = urlsplit(url)
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))
    except ValueError:
        return url


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def _reference(
    source: str,
    *,
    publisher: str | None = None,
    url: str | None = None,
    authority_tier: int,
    retrieval_depth: str,
) -> EvidenceReference:
    return EvidenceReference(
        source=source,
        publisher=publisher,
        url=_canonical_url(url),
        authority_tier=authority_tier,
        retrieval_depth=retrieval_depth,
    )


def _confidence(authority_tier: int, retrieval_depth: str, independent_sources: int = 1) -> str:
    if retrieval_depth == "structured" and authority_tier <= 2:
        return "high"
    if retrieval_depth == "full_text" and authority_tier <= 3:
        return "high"
    if independent_sources >= 2 and authority_tier <= 3:
        return "high"
    if retrieval_depth in {"headline", "excerpt"}:
        return "low"
    if authority_tier <= 2:
        return "medium"
    return "low"


def _filing_claim(item: FilingEvidence) -> EvidenceClaim:
    filed = item.filed_at.isoformat() if item.filed_at else "an unknown date"
    key = item.accession_number or f"{item.form}:{filed}:{item.primary_document or ''}"
    return EvidenceClaim(
        id=_stable_id("filing", key),
        category="filing",
        claim=f"SEC filing metadata shows a {item.form} filed on {filed}.",
        as_of=item.filed_at,
        authority_tier=1,
        retrieval_depth="metadata",
        confidence="medium",
        references=[_reference(item.source, url=item.url, authority_tier=1, retrieval_depth="metadata")],
        metadata={
            "form": item.form,
            "accession_number": item.accession_number,
            "primary_document": item.primary_document,
            "content_retrieved": False,
        },
    )


def _sec_fact_claim(item: SecFactEvidence) -> EvidenceClaim:
    period = item.period_end.isoformat() if item.period_end else "an unspecified period"
    key = f"{item.concept}:{period}:{item.accession_number or ''}"
    return EvidenceClaim(
        id=_stable_id("sec_fact", key),
        category="sec_fact",
        claim=f"SEC XBRL reports {item.label} of {item.value:g} {item.unit} for the period ending {period}.",
        as_of=item.period_end,
        authority_tier=1,
        retrieval_depth="structured",
        confidence="high",
        references=[_reference(item.source, url=item.url, authority_tier=1, retrieval_depth="structured")],
        metadata=item.model_dump(exclude_none=True, mode="json"),
    )


def _news_claim(group: list[NewsEvidence]) -> EvidenceClaim:
    first = group[0]
    publishers = {item.publisher or item.source for item in group}
    references = [
        _reference(
            item.source,
            publisher=item.publisher,
            url=item.url,
            authority_tier=4,
            retrieval_depth="headline",
        )
        for item in group
    ]
    return EvidenceClaim(
        id=_stable_id("news", _normalize_text(first.title)),
        category="news",
        claim=f'Published headline: "{first.title}"',
        as_of=first.published_at,
        authority_tier=4,
        retrieval_depth="headline",
        confidence="low",
        references=references,
        independent_source_count=1,
        duplicate_count=max(0, len(group) - 1),
        metadata={
            "headline_only": True,
            "publisher_count": len(publishers),
            "possible_syndication": len(group) > 1,
            "content_retrieved": False,
        },
    )


def _web_authority(url: str) -> int:
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return 4
    if host == "sec.gov" or host.endswith(".sec.gov") or host.endswith(".gov"):
        return 1
    return 4


def _web_claim(group: list[WebEvidence]) -> EvidenceClaim:
    first = group[0]
    canonical = _canonical_url(first.url) or first.url
    authority = _web_authority(first.url)
    is_sec_full_text = first.source == "SEC EDGAR full-text retrieval" and bool(first.highlights)
    retrieval_depth = "full_text" if is_sec_full_text else "excerpt"
    highlights = [text.strip() for item in group for text in item.highlights if text.strip()]
    excerpt = highlights[0] if highlights else None
    claim = f'Retrieved web result: "{first.title}".'
    if excerpt:
        claim += f' Query-relevant excerpt: "{excerpt}"'
    return EvidenceClaim(
        id=_stable_id("web", canonical),
        category="web",
        claim=claim,
        as_of=first.published_at,
        authority_tier=authority,
        retrieval_depth=retrieval_depth,
        confidence=_confidence(authority, retrieval_depth),
        references=[
            _reference(
                item.source,
                publisher=item.author,
                url=item.url,
                authority_tier=_web_authority(item.url),
                retrieval_depth=retrieval_depth,
            )
            for item in group
        ],
        independent_source_count=1,
        duplicate_count=max(0, len(group) - 1),
        metadata={
            "retrieved_via": first.source,
            "title": first.title,
            "highlights": highlights[:5],
            "query": first.query,
            "excerpt_only": not is_sec_full_text,
            "content_retrieved": bool(highlights),
        },
    )


def _estimate_claim(item: EstimateRevisionEvidence) -> EvidenceClaim:
    parts = [f"For {item.horizon}, the current EPS estimate is {item.eps_current!r}."]
    if item.eps_30d_ago is not None:
        parts.append(f"The 30-day-ago EPS estimate was {item.eps_30d_ago!r}.")
    if item.analyst_count is not None:
        parts.append(f"The reported analyst count is {item.analyst_count}.")
    return EvidenceClaim(
        id=_stable_id("estimate_revision", item.horizon),
        category="estimate_revision",
        claim=" ".join(parts),
        authority_tier=2,
        retrieval_depth="structured",
        confidence="high",
        references=[_reference(item.source, authority_tier=2, retrieval_depth="structured")],
        metadata=item.model_dump(exclude_none=True, mode="json"),
    )


def _earnings_claim(item: EarningsHistoryEvidence) -> EvidenceClaim:
    period = item.period.date().isoformat() if item.period else "unknown period"
    return EvidenceClaim(
        id=_stable_id("earnings", period),
        category="earnings",
        claim=f"For the earnings period {period}, reported EPS was {item.eps_actual!r} versus an estimate of {item.eps_estimate!r}.",
        as_of=item.period,
        authority_tier=2,
        retrieval_depth="structured",
        confidence="high",
        references=[_reference(item.source, authority_tier=2, retrieval_depth="structured")],
        metadata=item.model_dump(exclude_none=True, mode="json"),
    )


def _earnings_call_claim(item: EarningsCallQAEvidence, index: int) -> EvidenceClaim:
    analyst = item.analyst or "An analyst"
    responder = item.responder or "Management"
    return EvidenceClaim(
        id=_stable_id("earnings_call", f"{item.quarter}:{analyst}:{index}"),
        category="earnings_call",
        claim=(
            f"During the {item.quarter} earnings-call Q&A, {analyst} asked: {item.question} "
            f"{responder} answered: {item.answer}"
        ),
        authority_tier=3,
        retrieval_depth="excerpt",
        confidence="medium",
        references=[_reference(
            item.source,
            url=item.source_url,
            authority_tier=3,
            retrieval_depth="excerpt",
        )],
        metadata=item.model_dump(exclude_none=True, mode="json"),
    )


def _technical_claim(item: TechnicalEvidence) -> EvidenceClaim:
    as_of = item.as_of.isoformat() if item.as_of else "the latest trading day"
    parts = [f"Technical snapshot as of {as_of}."]
    if item.close is not None:
        parts.append(f"Close {item.close:.2f}.")
    if item.sma_50 is not None:
        parts.append(f"50-day SMA {item.sma_50:.2f}.")
    if item.sma_200 is not None:
        parts.append(f"200-day SMA {item.sma_200:.2f}.")
    if item.rsi_14 is not None:
        parts.append(f"14-day RSI {item.rsi_14:.1f}.")
    if item.macd is not None and item.macd_signal is not None:
        parts.append(f"MACD {item.macd:.3f} versus signal {item.macd_signal:.3f}.")
    return EvidenceClaim(
        id=_stable_id("technical", as_of),
        category="technical",
        claim=" ".join(parts),
        as_of=item.as_of,
        authority_tier=2,
        retrieval_depth="structured",
        confidence="high",
        references=[_reference(item.source, authority_tier=2, retrieval_depth="structured")],
        metadata=item.model_dump(exclude_none=True, mode="json"),
    )


def _insider_claim(item: InsiderTransactionEvidence, index: int) -> EvidenceClaim:
    when = item.start_date.isoformat() if item.start_date else "unknown date"
    actor = item.insider or "An insider"
    action = item.transaction or "a reported transaction"
    parts = [f"Yahoo Finance structured insider data reports {actor}: {action} on {when}."]
    if item.shares is not None:
        parts.append(f"Shares: {item.shares:.0f}.")
    if item.value is not None:
        parts.append(f"Reported value: {item.value:.2f}.")
    key = f"{actor}:{action}:{when}:{item.shares}:{item.value}:{index}"
    return EvidenceClaim(
        id=_stable_id("insider", key),
        category="insider",
        claim=" ".join(parts),
        as_of=item.start_date,
        authority_tier=2,
        retrieval_depth="structured",
        confidence="medium",
        references=[_reference(item.source, authority_tier=2, retrieval_depth="structured")],
        metadata=item.model_dump(exclude_none=True, mode="json"),
    )


def _macro_claim(item: MacroEvidence) -> EvidenceClaim:
    units = f" {item.units}" if item.units else ""
    return EvidenceClaim(
        id=_stable_id("macro", f"{item.series_id}:{item.as_of or ''}"),
        category="macro",
        claim=f"FRED series {item.series_id} ({item.label}) is {item.value}{units} as of {item.as_of or 'the reported date'}.",
        as_of=item.as_of,
        authority_tier=1,
        retrieval_depth="structured",
        confidence="high",
        references=[_reference(item.source, authority_tier=1, retrieval_depth="structured")],
        metadata=item.model_dump(exclude_none=True, mode="json"),
    )


def normalize_claims(bundle: EvidenceBundle) -> tuple[list[EvidenceClaim], int]:
    claims: list[EvidenceClaim] = []
    claims.extend(_filing_claim(item) for item in bundle.filings)
    claims.extend(_sec_fact_claim(item) for item in bundle.sec_facts)
    claims.extend(_estimate_claim(item) for item in bundle.estimate_revisions)
    claims.extend(_earnings_claim(item) for item in bundle.earnings_history)
    claims.extend(_earnings_call_claim(item, idx) for idx, item in enumerate(bundle.earnings_call_qa))
    claims.extend(_technical_claim(item) for item in bundle.technical)
    claims.extend(_insider_claim(item, idx) for idx, item in enumerate(bundle.insider_transactions))
    claims.extend(_macro_claim(item) for item in bundle.macro)

    grouped_news: dict[str, list[NewsEvidence]] = defaultdict(list)
    for item in bundle.news:
        grouped_news[_normalize_text(item.title)].append(item)
    claims.extend(_news_claim(group) for group in grouped_news.values())

    grouped_web: dict[str, list[WebEvidence]] = defaultdict(list)
    for item in bundle.web:
        grouped_web[_canonical_url(item.url) or _normalize_text(item.title)].append(item)
    claims.extend(_web_claim(group) for group in grouped_web.values())

    claims.sort(key=lambda claim: (claim.authority_tier, claim.category, claim.id))
    duplicate_count = sum(claim.duplicate_count for claim in claims)
    return claims, duplicate_count
