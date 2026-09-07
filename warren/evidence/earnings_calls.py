from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import httpx

from ..models import EarningsCallQAEvidence, EvidenceBundle, MetricSnapshot, SourceStatus


class AlphaVantageEarningsCallProvider:
    """Retrieve a bounded set of material analyst Q&A excerpts.

    Raw transcripts are not retained. The provider keeps short question/answer
    excerpts with speaker attribution and a source link for investment analysis.
    """

    ENDPOINT = "https://www.alphavantage.co/query"
    SOURCE_URL = "https://www.alphavantage.co/documentation/#earnings-call-transcript"
    cache_namespace = "alpha-vantage-earnings-calls-v3"
    MATERIAL_TERMS = (
        "guidance", "demand", "traffic", "volume", "pricing", "price", "margin",
        "cost", "investment", "return", "growth", "revenue", "earnings", "cash flow",
        "backlog", "orders", "customer", "competition", "capacity", "inventory",
    )

    def __init__(self, api_key: str | None = None, timeout: float = 25.0, max_questions: int = 6):
        configured_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        self.api_key = configured_key.strip() if configured_key else None
        self.timeout = timeout
        self.max_questions = min(max(1, max_questions), 10)

    @staticmethod
    def _quarters(now: datetime | None = None) -> list[str]:
        today = now or datetime.now(UTC)
        # Fiscal calendars and provider publication dates differ. Probe the
        # current year first, then the prior year, stopping as soon as a call is
        # found. The result is cached for a week, so this fallback does not
        # repeatedly consume the free API allowance.
        return [
            f"{year}Q{quarter}"
            for year in (today.year, today.year - 1)
            for quarter in (4, 3, 2, 1)
        ]

    def _request(self, ticker: str, quarter: str) -> dict[str, Any]:
        response = httpx.get(
            self.ENDPOINT,
            params={
                "function": "EARNINGS_CALL_TRANSCRIPT",
                "symbol": ticker,
                "quarter": quarter,
                "apikey": self.api_key,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _is_analyst(turn: dict[str, Any]) -> bool:
        role = " ".join(str(turn.get(key) or "") for key in ("title", "speaker")).lower()
        return "analyst" in role or "research" in role

    @classmethod
    def _material(cls, text: str) -> bool:
        lowered = text.lower()
        return any(term in lowered for term in cls.MATERIAL_TERMS)

    def _extract(self, quarter: str, turns: list[dict[str, Any]]) -> list[EarningsCallQAEvidence]:
        results: list[EarningsCallQAEvidence] = []
        for index, turn in enumerate(turns):
            question = str(turn.get("content") or "").strip()
            if not question or not self._is_analyst(turn) or not self._material(question):
                continue
            answers: list[dict[str, Any]] = []
            for candidate in turns[index + 1:]:
                if self._is_analyst(candidate):
                    break
                content = str(candidate.get("content") or "").strip()
                speaker = str(candidate.get("speaker") or "").lower()
                if content and "operator" not in speaker:
                    answers.append(candidate)
                if len(answers) >= 2:
                    break
            if not answers:
                continue
            answer_text = " ".join(str(item.get("content") or "").strip() for item in answers)
            first = answers[0]
            results.append(EarningsCallQAEvidence(
                quarter=quarter,
                analyst=str(turn.get("speaker") or "").strip() or None,
                analyst_title=str(turn.get("title") or "").strip() or None,
                question=question[:700],
                responder=str(first.get("speaker") or "").strip() or None,
                responder_title=str(first.get("title") or "").strip() or None,
                answer=answer_text[:1400],
                source_url=self.SOURCE_URL,
            ))
            if len(results) >= self.max_questions:
                break
        return results

    def fetch_evidence(self, ticker: str, metrics: MetricSnapshot) -> EvidenceBundle:
        bundle = EvidenceBundle()
        if not self.api_key:
            bundle.source_status.append(SourceStatus(
                source="Earnings-call transcripts",
                status="unavailable",
                detail="ALPHA_VANTAGE_API_KEY is not configured; earnings-call Q&A skipped.",
            ))
            return bundle

        symbol = ticker.strip().upper()
        attempted = 0
        try:
            for quarter in self._quarters():
                attempted += 1
                payload = self._request(symbol, quarter)
                provider_message = next(
                    (
                        str(payload.get(key) or "").strip()
                        for key in ("Error Message", "Information", "Note")
                        if payload.get(key)
                    ),
                    None,
                )
                if provider_message:
                    raise RuntimeError(f"Alpha Vantage: {provider_message[:500]}")
                turns = payload.get("transcript") if isinstance(payload, dict) else None
                if not isinstance(turns, list) or not turns:
                    continue
                bundle.earnings_call_qa = self._extract(quarter, turns)
                bundle.metadata["earnings_call"] = {
                    "quarter": quarter,
                    "provider": "Alpha Vantage",
                    "raw_transcript_retained": False,
                    "questions_retained": len(bundle.earnings_call_qa),
                }
                break
            bundle.source_status.append(SourceStatus(
                source="Earnings-call transcripts",
                status="ok" if bundle.earnings_call_qa else "partial",
                detail=(
                    f"{len(bundle.earnings_call_qa)} material analyst Q&A excerpts returned"
                    if bundle.earnings_call_qa else
                    f"No material transcript Q&A found after {attempted} bounded fiscal-quarter checks"
                ),
            ))
        except Exception as exc:
            bundle.source_status.append(SourceStatus(
                source="Earnings-call transcripts",
                status="error",
                detail=f"{type(exc).__name__}: {exc}",
            ))
        return bundle
