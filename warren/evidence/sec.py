from __future__ import annotations

import re
from datetime import date

import yfinance as yf

from ..models import EvidenceBundle, FilingEvidence, MetricSnapshot, SourceStatus


class SecFilingEvidenceProvider:
    """Recent SEC filing documents delivered through Yahoo Finance's filing mirror.

    The mirror preserves SEC filing documents while avoiding unreliable direct
    requests from shared serverless addresses. Full-text interpretation is
    performed by ``SecRagEvidenceProvider``.
    """

    cache_namespace = "sec-filing-mirror-v1"
    FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A", "20-F", "40-F", "6-K"}

    def __init__(self, max_filings: int = 8, **_: object):
        self.max_filings = max(0, max_filings)

    @staticmethod
    def _parse_date(raw: str | None) -> date | None:
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None

    def fetch_evidence(self, ticker: str, metrics: MetricSnapshot) -> EvidenceBundle:
        symbol = ticker.strip().upper()
        bundle = EvidenceBundle()
        if symbol.endswith(".TO"):
            bundle.source_status.append(SourceStatus(
                source="Company filings",
                status="unavailable",
                detail="Canadian issuer; US SEC filings are not assumed for this ticker.",
            ))
            return bundle

        try:
            rows = yf.Ticker(symbol).sec_filings or []
        except Exception as exc:
            bundle.source_status.append(SourceStatus(
                source="Company filings",
                status="error",
                detail=f"Filing retrieval failed ({type(exc).__name__}).",
            ))
            return bundle

        cik: int | None = None
        for row in rows:
            form = str(row.get("type") or "")
            if form not in self.FORMS:
                continue
            edgar_url = str(row.get("edgarUrl") or "")
            accession_match = re.search(r"/([0-9]{10}-[0-9]{2}-[0-9]{6})_([0-9]+)$", edgar_url)
            accession = accession_match.group(1) if accession_match else None
            if accession_match:
                cik = int(accession_match.group(2))
            exhibits = row.get("exhibits") or {}
            document_url = exhibits.get(form) or next(iter(exhibits.values()), None)
            if not document_url:
                continue
            bundle.filings.append(FilingEvidence(
                form=form,
                filed_at=row.get("date") if isinstance(row.get("date"), date) else self._parse_date(str(row.get("date") or "")),
                accession_number=accession,
                primary_document=str(document_url).rsplit("/", 1)[-1],
                url=str(document_url),
            ))

        essentials: list[FilingEvidence] = []
        family_counts = {"annual": 0, "quarterly": 0}
        for filing in bundle.filings:
            family = "annual" if filing.form in {"10-K", "20-F", "40-F"} else "quarterly" if filing.form == "10-Q" else None
            if family and family_counts[family] < 2:
                essentials.append(filing)
                family_counts[family] += 1
        chosen = essentials + [filing for filing in bundle.filings if filing not in essentials]
        bundle.filings = sorted(chosen[: self.max_filings], key=lambda item: item.filed_at or date.min, reverse=True)
        bundle.metadata.update({"sec_cik": cik, "filing_transport": "Yahoo Finance SEC filing mirror"})
        bundle.source_status.append(SourceStatus(
            source="Company filings",
            status="ok" if bundle.filings else "unavailable",
            detail=f"{len(bundle.filings)} recent SEC filing documents available." if bundle.filings else "No recent SEC filing documents were available.",
        ))
        return bundle
