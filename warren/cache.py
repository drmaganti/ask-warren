from __future__ import annotations

import asyncio
import hashlib
import json
import threading
import time
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Callable, Generic, Hashable, TypeVar

import httpx

from .models import CategoryScores, DeepAnalysis, EvidenceBundle, MetricSnapshot
from .protocols import DeepAnalysisProvider, EvidenceProvider, MarketDataProvider


K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class RedisJSONStore:
    """Small Upstash REST client with bounded, best-effort persistence."""

    def __init__(self, url: str, token: str, timeout_seconds: float = 2.0):
        self.url = url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> RedisJSONStore | None:
        import os

        url = os.getenv("UPSTASH_REDIS_REST_URL") or os.getenv("KV_REST_API_URL")
        token = os.getenv("UPSTASH_REDIS_REST_TOKEN") or os.getenv("KV_REST_API_TOKEN")
        return cls(url, token) if url and token else None

    def _command(self, *parts: object) -> Any:
        response = httpx.post(
            self.url,
            headers=self.headers,
            json=list(parts),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            raise RuntimeError(str(payload["error"]))
        return payload.get("result")

    def get(self, key: str) -> dict[str, Any] | None:
        try:
            raw = self._command("GET", key)
            return json.loads(raw) if raw else None
        except (httpx.HTTPError, RuntimeError, ValueError, TypeError):
            return None

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        try:
            self._command("SET", key, json.dumps(value, separators=(",", ":")), "EX", ttl_seconds)
        except (httpx.HTTPError, RuntimeError, ValueError, TypeError):
            # Persistence is an optimization; upstream analysis must remain available.
            return


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


class PersistentTTLCache(Generic[V]):
    """Memory-first cache backed by Redis, with a bounded last-known copy."""

    def __init__(
        self,
        namespace: str,
        ttl_seconds: float,
        encode: Callable[[V], Any],
        decode: Callable[[Any], V],
        store: RedisJSONStore | None = None,
    ):
        self.namespace = namespace
        self.ttl_seconds = max(1, int(ttl_seconds))
        self.encode = encode
        self.decode = decode
        self.store = store if store is not None else RedisJSONStore.from_env()
        self.memory: TTLCache[str, V] = TTLCache(ttl_seconds)

    def _key(self, key: str) -> str:
        return f"ask-warren:v1:{self.namespace}:{key}:fresh"

    def _decode(self, envelope: dict[str, Any] | None) -> V | None:
        if not envelope:
            return None
        try:
            return self.decode(envelope["value"])
        except (KeyError, TypeError, ValueError):
            return None

    def get(self, key: str) -> V | None:
        cached = self.memory.get(key)
        if cached is not None:
            return cached
        if self.store is None:
            return None
        value = self._decode(self.store.get(self._key(key)))
        if value is not None:
            self.memory.set(key, value)
        return value

    def set(self, key: str, value: V) -> None:
        self.memory.set(key, value)
        if self.store is None:
            return
        envelope = {
            "cached_at": datetime.now(UTC).isoformat(),
            "value": self.encode(value),
        }
        self.store.set(self._key(key), envelope, self.ttl_seconds)


def _model_encoder(value: Any) -> Any:
    return value.model_dump(mode="json")


class CachedMarketDataProvider:
    def __init__(self, upstream: MarketDataProvider, ttl_seconds: float = 300):
        self.upstream = upstream
        self.cache: PersistentTTLCache[MetricSnapshot] = PersistentTTLCache(
            "market", ttl_seconds, _model_encoder, MetricSnapshot.model_validate
        )
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
        namespace = getattr(upstream, "cache_namespace", upstream.__class__.__name__.lower())
        self.cache: PersistentTTLCache[EvidenceBundle] = PersistentTTLCache(
            f"evidence:{namespace}", ttl_seconds, _model_encoder, EvidenceBundle.model_validate
        )
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
        self.cache: PersistentTTLCache[tuple[DeepAnalysis, str | None]] = PersistentTTLCache(
            "analysis-v5",
            ttl_seconds,
            lambda value: {"analysis": _model_encoder(value[0]), "model": value[1]},
            lambda value: (DeepAnalysis.model_validate(value["analysis"]), value.get("model")),
        )
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
            # A resilient provider can return its deterministic fallback after a
            # transient model error. Do not preserve that degraded result for the
            # full synthesis TTL; the next request should be allowed to retry.
            if not (value[1] or "").startswith("deterministic"):
                self.cache.set(key, value)
            return value
