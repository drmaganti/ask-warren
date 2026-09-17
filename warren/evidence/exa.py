from __future__ import annotations

import os
import math
from datetime import datetime
from typing import Any

import httpx

from ..models import EvidenceBundle, MetricSnapshot, SourceStatus, WebEvidence


class ExaWebEvidenceProvider:
    """Optional pay-as-you-go web discovery for material company developments.

    Warren requests query-relevant excerpts rather than full pages to constrain
    latency, provider cost and prompt size. Exa is an additional discovery layer,
    not a replacement for primary SEC/company evidence.
    """

    SEARCH_URL = "https://api.exa.ai/search"
    cache_namespace = "exa-web-v2-targeted-lenses"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        num_results: int = 6,
        highlight_characters: int = 700,
        timeout: float = 20.0,
    ):
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        self.num_results = min(max(1, num_results), 10)
        self.highlight_characters = min(max(200, highlight_characters), 2000)
        self.timeout = timeout

    @staticmethod
    def _published_at(raw: Any) -> datetime | None:
        if not isinstance(raw, str) or not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _queries(ticker: str, metrics: MetricSnapshot) -> list[str]:
        company = metrics.company_name or ticker
        prefix = f"Latest material developments for {company} ({ticker}) relevant to an investor"
        return [
            f"{prefix}: future customer demand, bookings, backlog, market share, major products and growth catalysts.",
            f"{prefix}: earnings guidance, analyst expectations, margins, capital spending, pricing and cash flow.",
            f"{prefix}: competition, regulation, litigation, investigations, technology disruption and structural risks.",
        ]

    def fetch_evidence(self, ticker: str, metrics: MetricSnapshot) -> EvidenceBundle:
        bundle = EvidenceBundle()
        if not self.api_key:
            bundle.source_status.append(
                SourceStatus(
                    source="Exa web discovery",
                    status="unavailable",
                    detail="EXA_API_KEY is not configured; web discovery skipped.",
                )
            )
            return bundle

        queries = self._queries(ticker.strip().upper(), metrics)
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        seen_urls: set[str] = set()
        costs: list[float] = []
        request_ids: list[str] = []
        # Keep the total result budget close to the original single-search budget.
        per_query = max(1, math.ceil(self.num_results / len(queries)))
        failures: list[str] = []
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            for query in queries:
                body = {
                    "query": query,
                    "type": "auto",
                    "numResults": per_query,
                    "userLocation": "US",
                    "moderation": True,
                    "contents": {"highlights": True},
                    "systemPrompt": (
                        "Prefer official company investor-relations pages, SEC/government sources and reputable "
                        "financial journalism. Prefer recent original reporting and avoid duplicate or syndicated coverage."
                    ),
                }
                try:
                    response = client.post(self.SEARCH_URL, headers=headers, json=body)
                    response.raise_for_status()
                    payload = response.json()
                except (httpx.HTTPError, ValueError) as exc:
                    failures.append(type(exc).__name__)
                    continue
                cost = ((payload.get("costDollars") or {}).get("total"))
                if isinstance(cost, (int, float)):
                    costs.append(float(cost))
                if payload.get("requestId"):
                    request_ids.append(str(payload["requestId"]))
                for result in payload.get("results") or []:
                    url = str(result.get("url") or "").strip()
                    title = str(result.get("title") or "").strip()
                    if not url or not title or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    highlights = [str(value).strip()[: self.highlight_characters] for value in result.get("highlights") or [] if str(value).strip()][:3]
                    bundle.web.append(WebEvidence(
                        title=title,
                        url=url,
                        published_at=self._published_at(result.get("publishedDate")),
                        author=str(result.get("author")).strip() if result.get("author") else None,
                        highlights=highlights,
                        query=query,
                    ))

        if costs:
            bundle.metadata["exa_cost_dollars"] = sum(costs)
        if request_ids:
            bundle.metadata["exa_request_ids"] = request_ids
        bundle.metadata["exa_query_count"] = len(queries)
        bundle.metadata["exa_failed_query_count"] = len(failures)

        bundle.source_status.append(
            SourceStatus(
                source="Exa web discovery",
                status="ok" if bundle.web and not failures else "partial",
                detail=(
                    f"{len(bundle.web)} web results returned across {len(queries) - len(failures)} of "
                    f"{len(queries)} investor-focused searches"
                ),
            )
        )
        return bundle
