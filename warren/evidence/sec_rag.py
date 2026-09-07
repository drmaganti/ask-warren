from __future__ import annotations

import hashlib
import html
import os
import re
import time
from html.parser import HTMLParser
from typing import Any

import httpx

from ..models import EvidenceBundle, FilingEvidence, MetricSnapshot, SourceStatus, WebEvidence
from ..protocols import EvidenceProvider


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored = 0

    def handle_starttag(self, tag: str, attrs):
        if tag in {"script", "style", "noscript"}:
            self._ignored += 1
        elif tag in {"p", "div", "br", "tr", "h1", "h2", "h3", "h4", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str):
        if tag in {"script", "style", "noscript"} and self._ignored:
            self._ignored -= 1
        elif tag in {"p", "div", "tr", "h1", "h2", "h3", "h4", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str):
        if not self._ignored:
            self.parts.append(data)

    def text(self) -> str:
        value = html.unescape(" ".join(self.parts))
        value = re.sub(r"[ \t\r\f\v]+", " ", value)
        return re.sub(r"\n\s*\n+", "\n", value).strip()


class UpstashVectorClient:
    def __init__(self, url: str, token: str, timeout: float = 20.0):
        self.url = url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> UpstashVectorClient | None:
        url = os.getenv("UPSTASH_VECTOR_REST_URL")
        token = os.getenv("UPSTASH_VECTOR_REST_TOKEN")
        return cls(url, token) if url and token else None

    def _request(self, method: str, endpoint: str, payload: Any) -> Any:
        response = httpx.request(
            method,
            f"{self.url}/{endpoint}",
            headers=self.headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        body = response.json()
        if body.get("error"):
            raise RuntimeError(str(body["error"]))
        return body.get("result")

    def replace_ticker(self, ticker: str, chunks: list[dict[str, Any]]) -> None:
        # Upstash Vector has no per-vector TTL. Prune inactive ticker corpora on
        # every refresh so a free index cannot accumulate stale filings forever.
        self._request("DELETE", "delete", {"filter": f"expires_at < {int(time.time())}"})
        self._request("DELETE", "delete", {"prefix": f"sec:{ticker}:"})
        if chunks:
            self._request("POST", "upsert-data", chunks)

    def query(self, ticker: str, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        result = self._request(
            "POST",
            "query-data",
            {
                "data": query,
                "topK": top_k,
                "includeData": True,
                "includeMetadata": True,
                "filter": f"ticker = '{ticker}'",
            },
        )
        return result or []


class SecRagEvidenceProvider:
    """Adds citation-ready full-text SEC passages to normal SEC evidence."""

    cache_namespace = "sec-rag-direct-cik-v3"
    QUERY = (
        "What materially changed in business risks, demand, competition, strategy, margins, "
        "liquidity, capital allocation, guidance, or management's outlook? Explain revenue and earnings changes: "
        "divestiture gains, deconsolidation, acquisitions, restructuring, taxes, interest, working capital, "
        "capital expenditure, segment transactions and GAAP versus adjusted reconciliations."
    )
    MATERIAL_TERMS = (
        "risk", "competition", "demand", "margin", "liquidity", "capital allocation",
        "strategy", "outlook", "guidance", "supplier", "customer concentration",
        "cybersecurity", "regulation", "impairment", "restructuring",
        "divestiture", "deconsolidation", "effective tax rate", "gain on", "net gain",
        "working capital", "capital expenditure", "reconciliation", "sales leverage",
    )
    CORPUS_TTL_SECONDS = 30 * 24 * 60 * 60

    def __init__(
        self,
        upstream: EvidenceProvider,
        vector: UpstashVectorClient | None = None,
        max_filings: int = 4,
        max_chunks_per_filing: int = 12,
        timeout: float = 20.0,
    ):
        self.upstream = upstream
        self.vector = vector if vector is not None else UpstashVectorClient.from_env()
        self.max_filings = max_filings
        self.max_chunks_per_filing = max_chunks_per_filing
        self.timeout = timeout

    @staticmethod
    def _selected_filings(filings: list[FilingEvidence], limit: int) -> list[FilingEvidence]:
        selected: list[FilingEvidence] = []
        counts = {"annual": 0, "quarterly": 0}
        for filing in filings:
            family = "annual" if filing.form in {"10-K", "20-F", "40-F"} else "quarterly" if filing.form == "10-Q" else None
            if family and counts[family] < 2 and filing.url and filing.accession_number:
                selected.append(filing)
                counts[family] += 1
            if len(selected) >= limit:
                break
        return selected

    @staticmethod
    def _chunks(text: str, size: int = 1800, overlap: int = 180) -> list[str]:
        paragraphs = [part.strip() for part in text.split("\n") if len(part.strip()) >= 80]
        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if len(current) + len(paragraph) + 1 <= size:
                current = f"{current}\n{paragraph}".strip()
                continue
            if current:
                chunks.append(current)
            current = f"{current[-overlap:]}\n{paragraph}".strip() if current else paragraph
        if current:
            chunks.append(current)
        return chunks

    def _download_chunks(self, ticker: str, filing: FilingEvidence) -> list[dict[str, Any]]:
        response = httpx.get(
            filing.url,
            headers={"User-Agent": os.getenv("SEC_USER_AGENT", "AskWarren/0.5 https://github.com/drmaganti/ask-warren")},
            follow_redirects=True,
            timeout=self.timeout,
        )
        response.raise_for_status()
        parser = _VisibleTextParser()
        parser.feed(response.text)
        all_chunks = self._chunks(parser.text())
        ranked = sorted(
            enumerate(all_chunks),
            key=lambda item: (
                -sum(item[1].lower().count(term) for term in self.MATERIAL_TERMS),
                item[0],
            ),
        )
        lead_indexes = range(min(2, len(all_chunks)))
        selected_indexes = sorted({*lead_indexes, *(index for index, _ in ranked[: self.max_chunks_per_filing])})
        chunks = [all_chunks[index] for index in selected_indexes[: self.max_chunks_per_filing]]
        accession = filing.accession_number or "unknown"
        expires_at = int(time.time()) + self.CORPUS_TTL_SECONDS
        return [
            {
                "id": f"sec:{ticker}:{accession}:{index}",
                "data": chunk,
                "metadata": {
                    "ticker": ticker,
                    "accession": accession,
                    "form": filing.form,
                    "filed_at": filing.filed_at.isoformat() if filing.filed_at else None,
                    "url": filing.url,
                    "chunk": index,
                    "expires_at": expires_at,
                },
            }
            for index, chunk in enumerate(chunks)
        ]

    def fetch_evidence(self, ticker: str, metrics: MetricSnapshot) -> EvidenceBundle:
        bundle = self.upstream.fetch_evidence(ticker, metrics)
        if self.vector is None:
            return bundle
        symbol = ticker.strip().upper()
        filings = self._selected_filings(bundle.filings, self.max_filings)
        if len(filings) < 2:
            bundle.source_status.append(SourceStatus(source="SEC filing RAG", status="unavailable", detail="Fewer than two comparable SEC filings were available."))
            return bundle
        try:
            chunks = [chunk for filing in filings for chunk in self._download_chunks(symbol, filing)]
        except Exception as exc:
            bundle.source_status.append(SourceStatus(source="SEC filing RAG", status="error", detail=f"{type(exc).__name__}: {exc}"))
            return bundle

        vector_error: str | None = None
        try:
            self.vector.replace_ticker(symbol, chunks)
            results = self.vector.query(symbol, self.QUERY)
            # The hosted index is eventually consistent immediately after an
            # upsert. One short retry prevents an empty first result from being
            # cached for the six-hour SEC freshness window.
            if not results:
                time.sleep(0.4)
                results = self.vector.query(symbol, self.QUERY)
            retrieval_backend = "upstash-hybrid"
            if not results:
                # A newly created namespace can take longer than the request
                # budget to become queryable. Keep the first analysis grounded
                # with the same bounded, materiality-ranked filing chunks.
                results = chunks[:10]
                retrieval_backend = "materiality-ranked-first-run-fallback"
        except Exception as exc:
            vector_error = f"{type(exc).__name__}: {exc}"
            results = chunks[:10]
            retrieval_backend = "materiality-ranked-vector-error-fallback"

        seen: set[str] = set()
        for result in results:
            metadata = result.get("metadata") or {}
            data = str(result.get("data") or "").strip()
            vector_id = str(result.get("id") or hashlib.sha256(data.encode()).hexdigest())
            if not data or vector_id in seen:
                continue
            seen.add(vector_id)
            form = metadata.get("form") or "filing"
            filed_at = metadata.get("filed_at") or "unknown date"
            bundle.web.append(
                WebEvidence(
                    title=f"{form} filing passage ({filed_at})",
                    url=str(metadata.get("url") or "https://www.sec.gov/edgar/search/"),
                    highlights=[data],
                    query=self.QUERY,
                    source="SEC EDGAR full-text retrieval",
                )
            )
        bundle.metadata["sec_rag"] = {
            "indexed_filings": len(filings),
            "indexed_chunks": len(chunks),
            "retrieved_passages": len(seen),
            "strategy": "latest-and-prior annual/quarterly filings",
            "retrieval_backend": retrieval_backend,
        }
        if vector_error:
            bundle.metadata["sec_rag"]["vector_warning"] = vector_error
        status = "partial" if vector_error or not seen else "ok"
        detail = f"Retrieved {len(seen)} full-text passages from {len(filings)} filings."
        if vector_error:
            detail += " Vector indexing was temporarily unavailable, so bounded local retrieval was used."
        bundle.source_status.append(SourceStatus(source="SEC filing RAG", status=status, detail=detail))
        return bundle
