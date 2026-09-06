from __future__ import annotations

from ..models import CategoryScores, DeepAnalysis, EvidenceBundle, MetricSnapshot, SourceStatus
from ..protocols import DeepAnalysisProvider


class ResilientDeepAnalysisProvider:
    """Use a deterministic fallback when the configured model is unavailable."""

    def __init__(self, primary: DeepAnalysisProvider, fallback: DeepAnalysisProvider):
        self.primary = primary
        self.fallback = fallback

    async def analyze(
        self,
        metrics: MetricSnapshot,
        scores: CategoryScores,
        evidence: EvidenceBundle,
    ) -> tuple[DeepAnalysis, str | None]:
        try:
            return await self.primary.analyze(metrics, scores, evidence)
        except Exception as exc:
            evidence.source_status.append(
                SourceStatus(
                    source=self.primary.__class__.__name__,
                    status="partial",
                    detail=f"Model synthesis unavailable ({type(exc).__name__}); deterministic fallback used.",
                )
            )
            return await self.fallback.analyze(metrics, scores, evidence)
