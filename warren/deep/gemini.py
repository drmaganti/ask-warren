from __future__ import annotations

import asyncio
import json
import os

import httpx

from ..models import CategoryScores, DeepAnalysis, EvidenceBundle, MetricSnapshot


class GeminiDeepAnalysisProvider:
    """TradingAgents-inspired bull/bear/risk debate followed by final synthesis."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    async def _generate(self, prompt: str) -> dict:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required for Warren deep mode")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.15, "responseMimeType": "application/json"},
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": self.api_key},
                json=body,
            )
            response.raise_for_status()
            payload = response.json()
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)

    @staticmethod
    def _evidence(metrics: MetricSnapshot, scores: CategoryScores, evidence: EvidenceBundle) -> str:
        return json.dumps(
            {
                "metrics": metrics.model_dump(exclude_none=True, mode="json"),
                "scores": scores.model_dump(mode="json"),
                "evidence": evidence.model_dump(exclude_none=True, mode="json"),
            },
            separators=(",", ":"),
        )

    async def analyze(
        self,
        metrics: MetricSnapshot,
        scores: CategoryScores,
        evidence: EvidenceBundle,
    ) -> tuple[DeepAnalysis, str | None]:
        packet = self._evidence(metrics, scores, evidence)
        shared = (
            "Use ONLY the supplied packet. Do not invent news, filing contents, forecasts, competitors, "
            "prices, ratios, catalysts, or facts. Prefer evidence.claims as the interpretation-ready evidence layer: "
            "claims have already been normalized and exact duplicate headlines have been collapsed. Do not count raw evidence "
            "and its corresponding normalized claim as separate corroboration. Respect each claim's authority_tier, retrieval_depth, "
            "confidence, independent_source_count and duplicate_count. A duplicated or syndicated headline is not independent evidence. "
            "SEC entries with retrieval_depth=metadata prove filing metadata only: do not claim what a filing says. "
            "News entries with retrieval_depth=headline prove only that the headline was published: do not infer unseen article contents. "
            "Structured analyst revisions, earnings observations and FRED observations may be compared directly. "
            "Explicitly identify missing or unavailable evidence. Distinguish business quality from stock attractiveness. "
            "When practical, identify the source or claim category supporting an argument."
        )

        bull_prompt = f"""You are Warren's independent BULL analyst. {shared}
Evidence packet: {packet}
Build the strongest evidence-grounded case FOR further investment interest, while acknowledging weaknesses.
Return JSON only: {{"arguments":[3-5 concise strings],"weaknesses":[1-3 strings]}}."""

        bear_prompt = f"""You are Warren's independent BEAR analyst. {shared}
Evidence packet: {packet}
Build the strongest evidence-grounded case AGAINST investment interest, including valuation and thesis-break risks.
Return JSON only: {{"arguments":[3-5 concise strings],"weaknesses":[1-3 strings]}}."""

        risk_prompt = f"""You are Warren's independent RISK reviewer. {shared}
Evidence packet: {packet}
Focus on downside, evidence gaps, balance-sheet resilience, expectation risk, and whether current evidence is stale or incomplete.
Return JSON only: {{"risks":[3-5 concise strings],"missing_evidence":[0-7 strings],"summary":"string"}}."""

        bull, bear, risk = await asyncio.gather(
            self._generate(bull_prompt),
            self._generate(bear_prompt),
            self._generate(risk_prompt),
        )

        final_prompt = f"""You are Warren's FINAL investment research evaluator. {shared}
Evidence packet: {packet}
Bull analyst: {json.dumps(bull)}
Bear analyst: {json.dumps(bear)}
Risk reviewer: {json.dumps(risk)}

Synthesize rather than vote. Weight source facts above agent rhetoric. A strong company can still be an unattractive stock if valuation or expectations are unfavorable. If filings are only metadata or news is only headline-level, state the limitation rather than pretending the underlying documents were read. Reduce confidence when important source_status entries are unavailable/error, high-authority evidence is missing, or key metrics are missing.

The verdict MUST be exactly one of:
- "attractive" — favorable quality + valuation + risk/reward at the current price;
- "watch" — credible thesis but not compelling enough today, or evidence is mixed/incomplete;
- "avoid" — business, valuation, balance-sheet, structural-risk or evidence concerns make the setup unattractive.
Do not output buy, hold, sell, strong buy, neutral, outperform, underperform or any other verdict vocabulary.

For every conclusion that relies on evidence.claims, add a citation entry. Use only claim IDs present in the packet. item_index is zero-based; use 0 for thesis. Do not cite a claim merely because it is topically related, and do not cite deterministic metrics or scores as evidence claims.

Return JSON only with exactly:
{{"thesis":"string","positives":[3-5 strings],"concerns":[3-5 strings],"bull_case":[2-4 strings],"bear_case":[2-4 strings],"risks":[2-5 strings],"what_would_change_view":[2-4 strings],"verdict":"attractive|watch|avoid","confidence":"low|medium|high","citations":[{{"section":"thesis|positives|concerns|bull_case|bear_case|risks|what_would_change_view","item_index":0,"claim_ids":["exact-claim-id"]}}]}}."""
        final = await self._generate(final_prompt)
        return DeepAnalysis.model_validate(final), self.model
