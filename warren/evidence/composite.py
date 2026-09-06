from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from ..models import EvidenceBundle, MetricSnapshot, SourceStatus
from ..protocols import EvidenceProvider


class CompositeEvidenceProvider:
    """Combines independent evidence sources without making Deep all-or-nothing.

    A failed source is recorded in `source_status`; evidence from other sources
    remains usable. This is deliberate because filings, news, estimates and macro
    data have different availability and failure modes.
    """

    def __init__(self, providers: list[EvidenceProvider]):
        self.providers = providers

    def fetch_evidence(self, ticker: str, metrics: MetricSnapshot) -> EvidenceBundle:
        bundle = EvidenceBundle()
        if not self.providers:
            return bundle

        # Providers are independent network sources. Fetch them concurrently so
        # one slow upstream does not consume the entire serverless request window.
        with ThreadPoolExecutor(max_workers=len(self.providers)) as executor:
            futures = [executor.submit(provider.fetch_evidence, ticker, metrics) for provider in self.providers]

        for provider, future in zip(self.providers, futures, strict=True):
            try:
                bundle = bundle.merge(future.result())
            except Exception as exc:
                bundle.source_status.append(
                    SourceStatus(
                        source=provider.__class__.__name__,
                        status="error",
                        detail=f"{type(exc).__name__}: {exc}",
                    )
                )
        return bundle
