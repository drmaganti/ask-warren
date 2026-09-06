from __future__ import annotations

import asyncio
import hashlib
import json
import threading
import time
from copy import deepcopy
from typing import Callable, Generic, Hashable, TypeVar

from .models import CategoryScores, DeepAnalysis, EvidenceBundle, MetricSnapshot
from .protocols import DeepAnalysisProvider, EvidenceProvider, MarketDataProvider


K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class TTLCache(Generic[K, V]):
    """Small thread-safe TTL cache for warm serverless instances."""

    def __init__(self, ttl_seconds: float, max_entries: int = 512):
        self.ttl_seconds = max(0.0, ttl_seconds)
        self.max_entries = max(1, max_entries)
        self._items: dict[K, tuple[float, V]] = {}
        self._lock = threading.Lock()

    def get(self, key: K) -> V | None:
        now = time.monotonic()
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at <= now:
                self._items.pop(key, None)
                return None
            return deepcopy(value)

    def set(self, key: K, value: V) -> None:
        with self._lock:
            if len(self._items) >= self.max_entries:
                oldest = min(self._items, key=lambda candidate: self._items[candidate][0])
                self._items.pop(oldest, None)
            self._items[key] = (time.monotonic() + self.ttl_seconds, deepcopy(value))


class CachedMarketDataProvider:
    def __init__(self, upstream: MarketDataProvider, ttl_seconds: float = 300):
        self.upstream = upstream
        self.cache: TTLCache[str, MetricSnapshot] = TTLCache(ttl_seconds)
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def fetch_metrics(self, ticker: str) -> MetricSnapshot:
        key = ticker.strip().upper()
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        with self._locks_guard:
            lock = self._locks.setdefault(key, threading.Lock())
        with lock:
            cached = self.cache.get(key)
            if cached is not None:
                return cached
            value = self.upstream.fetch_metrics(key)
            self.cache.set(key, value)
            return value


class CachedEvidenceProvider:
    def __init__(
        self,
        upstream: EvidenceProvider,
        ttl_seconds: float,
        key: Callable[[str, MetricSnapshot], str] | None = None,
    ):
        self.upstream = upstream
        self.key = key or (lambda ticker, metrics: ticker.strip().upper())
        self.cache: TTLCache[str, EvidenceBundle] = TTLCache(ttl_seconds)
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def fetch_evidence(self, ticker: str, metrics: MetricSnapshot) -> EvidenceBundle:
        key = self.key(ticker, metrics)
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        with self._locks_guard:
            lock = self._locks.setdefault(key, threading.Lock())
        with lock:
            cached = self.cache.get(key)
            if cached is not None:
                return cached
            value = self.upstream.fetch_evidence(ticker, metrics)
            self.cache.set(key, value)
            return value


class CachedDeepAnalysisProvider:
    def __init__(self, upstream: DeepAnalysisProvider, ttl_seconds: float = 1800):
        self.upstream = upstream
        self.cache: TTLCache[str, tuple[DeepAnalysis, str | None]] = TTLCache(ttl_seconds)
        self._locks: dict[str, asyncio.Lock] = {}

    @staticmethod
    def _key(metrics: MetricSnapshot, scores: CategoryScores, evidence: EvidenceBundle) -> str:
        payload = {
            "metrics": metrics.model_dump(exclude_none=True, mode="json"),
            "scores": scores.model_dump(mode="json"),
            "evidence_version": evidence.evidence_version,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def analyze(
        self,
        metrics: MetricSnapshot,
        scores: CategoryScores,
        evidence: EvidenceBundle,
    ) -> tuple[DeepAnalysis, str | None]:
        key = self._key(metrics, scores, evidence)
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached = self.cache.get(key)
            if cached is not None:
                return cached
            value = await self.upstream.analyze(metrics, scores, evidence)
            self.cache.set(key, value)
            return value
