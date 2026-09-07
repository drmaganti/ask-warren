from __future__ import annotations

import json
import logging

from ..models import CategoryScores, DeepAnalysis, EvidenceBundle, MetricSnapshot, SourceStatus
from ..protocols import DeepAnalysisProvider


logger = logging.getLogger(__name__)


class ResilientDeepAnalysisProvider:
    """Use a deterministic fallback when the configured model is unavailable."""

    def __init__(self, primary: DeepAnalysisProvider, fallback: DeepAnalysisProvider):
        self.primary = primary
        self.fallback = fallback

    @staticmethod
    def _diagnostic(exc: Exception) -> tuple[str, int | None]:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)
        categories = {
            400: "invalid provider request",
            401: "provider authentication failed",
            403: "provider permission or quota access denied",
            404: "configured model or endpoint unavailable",
            408: "provider request timed out",
            429: "provider rate or quota limit reached",
        }
        if status_code in categories:
            return categories[status_code], status_code
        if isinstance(status_code, int) and status_code >= 500:
            return "temporary provider service failure", status_code
        error_type = type(exc).__name__
        if "Timeout" in error_type:
            return "provider request timed out", status_code
        if error_type == "JSONDecodeError":
            return "provider returned invalid JSON", status_code
        if error_type == "ValidationError":
            return "provider response did not match the analysis schema", status_code
        return "unexpected provider error", status_code

    async def analyze(
        self,
        metrics: MetricSnapshot,
        scores: CategoryScores,
        evidence: EvidenceBundle,
    ) -> tuple[DeepAnalysis, str | None]:
        try:
            return await self.primary.analyze(metrics, scores, evidence)
        except Exception as exc:
            category, status_code = self._diagnostic(exc)
            error_type = type(exc).__name__
            logger.warning(json.dumps({
                "level": "warning",
                "event": "deep_analysis_fallback",
                "provider": self.primary.__class__.__name__,
                "ticker": metrics.ticker,
                "category": category,
                "http_status": status_code,
                "error_type": error_type,
            }, separators=(",", ":")))
            status = f"HTTP {status_code}, {error_type}" if status_code else error_type
            evidence.source_status.append(
                SourceStatus(
                    source=self.primary.__class__.__name__,
                    status="partial",
                    detail=f"Model synthesis unavailable: {category} ({status}); deterministic fallback used.",
                )
            )
            return await self.fallback.analyze(metrics, scores, evidence)
