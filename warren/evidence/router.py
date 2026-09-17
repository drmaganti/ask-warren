from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import date, datetime, timezone
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
    MaterialDevelopment,
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

    VERSION = "1.6"

    def __init__(self, upstream: EvidenceProvider):
        self.upstream = upstream

    def fetch_evidence(self, ticker: str, metrics: MetricSnapshot) -> EvidenceBundle:
        bundle = self.upstream.fetch_evidence(ticker, metrics)
        claims, duplicate_count = normalize_claims(bundle, metrics)
        bundle.claims = claims
        bundle.material_developments = rank_material_developments(claims, metrics)
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
            "material_developments": len(bundle.material_developments),
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


_POSITIVE_TERMS = ("raises", "raised", "growth", "accelerates", "expands", "wins", "strong demand", "record", "approval")
_NEGATIVE_TERMS = ("cuts", "lowered", "decline", "slows", "weak", "lawsuit", "investigation", "antitrust", "recall", "loses")


def _token_set(value: str) -> set[str]:
    ignored = {"the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with", "company", "latest"}
    return {token for token in _normalize_text(value).split() if len(token) > 2 and token not in ignored}


def _similar_event(left: EvidenceClaim, right: EvidenceClaim) -> bool:
    a, b = _token_set(str(left.metadata.get("title") or left.claim)), _token_set(str(right.metadata.get("title") or right.claim))
    return bool(a and b) and len(a & b) / len(a | b) >= .45


def _event_implication(themes: list[str], stance: str) -> str:
    if "legal_regulatory" in themes:
        return "This could change costs, operating freedom or the timing of growth; the financial exposure and case milestones determine whether it becomes material."
    if "demand" in themes or "forecast" in themes:
        return "This is a forward demand signal that can change future revenue expectations; confirmation should come through guidance, orders, usage or customer growth."
    if "investment_capacity" in themes:
        return "The investment can expand future capacity, but returns depend on demand growing enough to cover higher capital and operating costs."
    if "competition" in themes:
        return "This may affect market share, pricing power and the growth assumptions investors currently expect."
    if "earnings_quality" in themes or "pricing_mix" in themes:
        return "This may change margins and cash conversion, so investors should separate durable operating improvement from temporary effects."
    return "This development could affect the investment thesis, but its financial magnitude needs confirmation in company results or guidance."


def _event_score(claim: EvidenceClaim, metrics: MetricSnapshot | None, now: datetime) -> tuple[int, dict[str, int], str, str]:
    text = f"{claim.metadata.get('title', '')} {claim.claim}".lower()
    themes = claim.metadata.get("themes") or _themes(text)
    financial = min(25, 7 + 5 * len(set(themes) & {"demand", "forecast", "pricing_mix", "earnings_quality", "capital_allocation"}))
    forward = min(20, 5 + 7 * len(set(themes) & {"demand", "forecast", "investment_capacity", "competition", "legal_regulatory"}))
    thesis = min(15, 4 + 4 * min(3, len(themes)))
    host = (urlsplit(claim.references[0].url or "").hostname or "").lower() if claim.references else ""
    company_token = _normalize_text(metrics.company_name or "").split()[0] if metrics and metrics.company_name else ""
    official = host.endswith(".gov") or (company_token and company_token in host)
    quality = 15 if official else 11 if claim.retrieval_depth in {"excerpt", "full_text"} else 5
    quantified = bool(re.search(r"(?:\$|%|\b\d+(?:\.\d+)?\s*(?:billion|million|bn|m)\b)", text))
    magnitude = min(10, 4 + (3 if quantified else 0) + (3 if any(x in text for x in ("major", "material", "companywide", "global", "billion")) else 0))
    surprise = min(10, 2 + (5 if any(x in text for x in ("raises", "cuts", "beats", "misses", "unexpected", "surprise", "lowered")) else 0))
    as_of = claim.as_of.date() if isinstance(claim.as_of, datetime) else claim.as_of
    age = (now.date() - as_of).days if isinstance(as_of, date) else None
    immediacy = 5 if age is not None and age <= 30 else 3 if age is not None and age <= 90 else 1
    breakdown = {"financial_impact": financial, "forward_relevance": forward, "thesis_impact": thesis, "evidence_quality": quality, "magnitude_scope": magnitude, "expectation_surprise": surprise, "immediacy": immediacy}
    score = min(100, sum(breakdown.values()) + min(5, max(0, claim.independent_source_count - 1) * 3))
    positive, negative = any(x in text for x in _POSITIVE_TERMS), any(x in text for x in _NEGATIVE_TERMS)
    stance = "mixed" if positive == negative else "bullish" if positive else "bearish"
    horizon = "near_term" if age is not None and age <= 90 else "medium_term" if themes else "unresolved"
    return score, breakdown, stance, horizon


def rank_material_developments(claims: list[EvidenceClaim], metrics: MetricSnapshot | None = None) -> list[MaterialDevelopment]:
    """Rank retrieved news/excerpts by explainable investment materiality."""
    candidates = [claim for claim in claims if claim.category in {"news", "web"} and claim.metadata.get("retrieved_via") != "SEC EDGAR full-text retrieval"]
    groups: list[list[EvidenceClaim]] = []
    for claim in candidates:
        match = next((group for group in groups if _similar_event(group[0], claim)), None)
        if match is not None:
            match.append(claim)
        else:
            groups.append([claim])
    now = datetime.now(timezone.utc)
    developments: list[MaterialDevelopment] = []
    for group in groups:
        primary = max(group, key=lambda item: (item.retrieval_depth in {"excerpt", "full_text"}, -item.authority_tier))
        # Headline repetition is not independent corroboration. Count distinct
        # domains only when the event group contains retrieved excerpts.
        excerpt_claims = [claim for claim in group if claim.retrieval_depth in {"excerpt", "full_text"}]
        independent = len({(urlsplit(ref.url).hostname or ref.source).lower() for claim in excerpt_claims for ref in claim.references if ref.url or ref.source}) or 1
        primary = primary.model_copy(update={"independent_source_count": independent})
        score, breakdown, stance, horizon = _event_score(primary, metrics, now)
        themes = primary.metadata.get("themes") or _themes(primary.claim)
        highlights = primary.metadata.get("highlights") or []
        summary = str(highlights[0]).strip()[:320] if highlights else None
        level = "critical" if score >= 80 else "material" if score >= 60 else "relevant" if score >= 40 else "background"
        developments.append(MaterialDevelopment(
            id=_stable_id("development", ":".join(sorted(claim.id for claim in group))),
            title=str(primary.metadata.get("title") or primary.claim.removeprefix('Published headline: ').strip('"')),
            summary=summary,
            investor_implication=_event_implication(themes, stance),
            stance=stance,
            published_at=primary.as_of if isinstance(primary.as_of, datetime) else None,
            materiality_score=score,
            materiality_level=level,
            time_horizon=horizon,
            themes=themes,
            score_breakdown=breakdown,
            claim_ids=[claim.id for claim in group],
            references=[ref for claim in group for ref in claim.references],
            independent_source_count=independent,
        ))
    return sorted(developments, key=lambda item: (item.materiality_score, item.published_at or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)


_THEME_TERMS = {
    "demand": ("demand", "traffic", "transaction", "volume", "orders", "bookings", "backlog", "retention", "churn", "market share"),
    "forecast": ("guidance", "outlook", "forecast", "estimate", "expects", "projected"),
    "pricing_mix": ("pricing", "price increase", "mix", "average ticket"),
    "investment_capacity": ("investment", "capital expenditure", "capacity", "new store", "expansion", "hiring", "inventory"),
    "competition": ("competition", "competitor", "market share"),
    "legal_regulatory": ("lawsuit", "litigation", "investigation", "regulator", "regulatory", "antitrust", "patent", "court", "settlement"),
    "earnings_quality": ("margin", "restructuring", "impairment", "tax", "interest", "working capital", "cash flow", "divestiture", "acquisition"),
    "capital_allocation": ("buyback", "repurchase", "dividend", "debt", "refinancing", "acquisition"),
}


def _themes(text: str) -> list[str]:
    normalized = _normalize_text(text)
    return [theme for theme, terms in _THEME_TERMS.items() if any(term in normalized for term in terms)]


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


def _metric_claims(metrics: MetricSnapshot) -> list[EvidenceClaim]:
    fields = (
        "price", "market_cap", "total_revenue", "trailing_pe", "forward_pe",
        "free_cash_flow", "total_cash", "total_debt", "revenue_growth",
        "earnings_growth", "operating_margin", "profit_margin",
        "return_on_equity", "return_on_assets", "debt_to_equity",
        "current_ratio", "analyst_target_median",
    )
    claims: list[EvidenceClaim] = []
    for field in fields:
        value = getattr(metrics, field)
        if value is None:
            continue
        label = field.replace("_", " ")
        claims.append(EvidenceClaim(
            id=_stable_id("metric", field),
            category="metric",
            claim=f"Yahoo Finance structured company data reports {label} of {value:g}.",
            as_of=metrics.fetched_at or metrics.most_recent_quarter,
            authority_tier=2,
            retrieval_depth="structured",
            confidence="high",
            references=[_reference("Yahoo Finance", authority_tier=2, retrieval_depth="structured")],
            metadata={"field": field, "value": value},
        ))
    for item in metrics.quarterly_comparisons:
        field = f"quarterly_comparisons.{item.metric}"
        claims.append(EvidenceClaim(
            id=_stable_id("metric", field),
            category="metric",
            claim=f"Yahoo Finance statement data reports {item.label} of {item.current:g} for the current period.",
            as_of=item.current_period or metrics.fetched_at,
            authority_tier=2,
            retrieval_depth="structured",
            confidence="high",
            references=[_reference("Yahoo Finance", authority_tier=2, retrieval_depth="structured")],
            metadata={"field": field, **item.model_dump(exclude_none=True, mode="json")},
        ))
    return claims


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


def normalize_claims(bundle: EvidenceBundle, metrics: MetricSnapshot | None = None) -> tuple[list[EvidenceClaim], int]:
    claims: list[EvidenceClaim] = _metric_claims(metrics) if metrics is not None else []
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

    claims = [
        claim.model_copy(update={"metadata": {**claim.metadata, "themes": _themes(claim.claim)}})
        for claim in claims
    ]
    claims.sort(key=lambda claim: (claim.authority_tier, claim.category, claim.id))
    duplicate_count = sum(claim.duplicate_count for claim in claims)
    return claims, duplicate_count
