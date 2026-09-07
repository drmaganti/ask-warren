from __future__ import annotations

import json
import os

import httpx

from ..models import CategoryScores, DeepAnalysis, EvidenceBundle, MetricSnapshot
from .drivers import earnings_bridge


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
                "earnings_bridge": earnings_bridge(metrics),
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
            "When practical, identify the source or claim category supporting an argument. Do not mention numerical category "
            "scores or describe them as high, low, strong, weak, above average or below average in the thesis, positives, concerns, "
            "Bull Case, Bear Case or risks. Scores are internal decision aids, not investor-facing evidence. Each Bull Case and "
            "Bear Case item must lead with a specific finding, give the relevant metrics or evidence, compare with the previous "
            "quarter and same quarter last year when compatible comparisons exist, and explain why the finding matters to an "
            "investor. Include the strongest supported forward-demand or future-earnings argument on each side using analyst "
            "estimates and revisions, management guidance, demand indicators, capacity/investment plans or industry-demand "
            "evidence when available. State the condition that must hold for the future claim to be true. Never invent an "
            "industry or peer benchmark. Treat earnings_call claims as Q&A excerpts: identify the analyst's underlying concern, "
            "whether management answered it directly, and the implication for future demand or earnings. Do not infer honesty, "
            "emotion or tone. Cite the earnings-call claim for every call-derived point. Build bull_insights and bear_insights "
            "as competing investment theses, not metric summaries. Every insight must contain a plain-language headline, finding, "
            "supported cause, durability, time horizon, investor implication, concrete monitoring items, qualitative likelihood and "
            "impact, confidence, and exact supporting claim IDs. Numbers support the interpretation; they are not the headline. "
            "If the cause or horizon is not established, use unresolved and name the missing evidence. Use industry-specific demand "
            "drivers when supplied by the evidence; otherwise do not invent them. A lawsuit or regulatory event belongs in Bear only "
            "when its potential financial or strategic materiality can be explained. Evaluate these lenses on every run: future demand, "
            "earnings quality, operating leverage, capital allocation, market expectations/valuation, market positioning/technical extension, "
            "and company-specific risk. Do not force an unsupported visible insight. Rank supported candidates by financial impact, likelihood, "
            "evidence confidence and decision relevance, then return only the strongest 3-4 insights per side. For technically stretched shares, "
            "use RSI, distance from moving averages, Bollinger position and volume versus its 20-day average; never call a stock crowded or "
            "overtraded from price appreciation alone. Each visible insight should explain the expectation gap and a plausible success or failure path."
        )

        final_prompt = f"""You are Warren's investment research evaluator. {shared}
Evidence packet: {packet}

Perform an internal bull, bear, and risk review before forming the final view. Build the strongest evidence-grounded case on each side, then synthesize rather than vote. Weight source facts above rhetoric. A strong company can still be an unattractive stock if valuation or expectations are unfavorable. If filings are only metadata or news is only headline-level, state the limitation rather than pretending the underlying documents were read. Reduce confidence when important source_status entries are partial/unavailable/error, high-authority evidence is missing, or key metrics are missing. Do not return high confidence when any source material to the central thesis is partial, unavailable or errored.

Before writing, reconcile revenue, operating income, pretax income, taxes, net income and cash flow. Use earnings_bridge for arithmetic only. Investigate divestitures, acquisitions, deconsolidation, restructuring, impairment, tax changes, interest, share count, working capital and capital spending using retrieved statements and notes. Separate recurring operations from transaction gains and accounting effects. Revenue contraction alone does not establish weaker demand; check segment scope, currency, pricing and transactions. A lower tax rate does not necessarily mean lower tax expense.

Prefer company-reported GAAP values to conflicting aggregator values for the same period and scope. Explicitly disclose unresolved discrepancies; never silently mix GAAP, adjusted, segment and consolidated margins. Do not infer efficiency from net-income growth or claim that margin expansion explains the entire earnings change. Distinguish net income from EPS and evaluate buybacks only with share-count evidence.

Lead Bull/Bear with the most material supported causal findings. Each point should state the quantified driver, whether it is recurring or one-time, the investor implication, and what to watch. Cite the exact claim supporting the cause, not a related earnings headline. Use 'The filing attributes...' for management explanations and 'The statements show...' for arithmetic. If causation is unresolved, state the specific missing evidence. Avoid vague 'maybe' language while retaining explicit uncertainty about forecasts. Do not force a causal explanation when evidence is insufficient.

The verdict MUST be exactly one of:
- "attractive" — favorable quality + valuation + risk/reward at the current price;
- "watch" — credible thesis but not compelling enough today, or evidence is mixed/incomplete;
- "avoid" — business, valuation, balance-sheet, structural-risk or evidence concerns make the setup unattractive.
Do not output buy, hold, sell, strong buy, neutral, outperform, underperform or any other verdict vocabulary.

For every conclusion that relies on evidence.claims, add a citation entry. Use only claim IDs present in the packet. item_index is zero-based; use 0 for thesis. Do not cite a claim merely because it is topically related, and do not cite deterministic metrics or scores as evidence claims.

Return JSON only with exactly:
{{"thesis":"string","positives":[3-5 strings],"concerns":[3-5 strings],"bull_case":[2-4 concise strings],"bear_case":[2-4 concise strings],"risks":[2-5 strings],"what_would_change_view":[2-4 strings],"verdict":"attractive|watch|avoid","confidence":"low|medium|high","citations":[{{"section":"thesis|positives|concerns|bull_case|bear_case|risks|what_would_change_view","item_index":0,"claim_ids":["exact-claim-id"]}}],"bull_insights":[{{"headline":"string","lens":"future_demand|earnings_quality|operating_leverage|capital_allocation|market_expectations|market_positioning|company_risk|other","finding":"string","cause":"string","durability":"recurring|temporary|one_time|unresolved","time_horizon":"near_term|medium_term|long_term|unresolved","investor_implication":"string","expectation_gap":"string or null","scenario_path":"string or null","what_to_watch":["observable signal"],"catalyst":"string or null","likelihood":"low|medium|high|unresolved","impact":"low|medium|high|unresolved","confidence":"low|medium|high","claim_ids":["exact-claim-id"]}}],"bear_insights":[{{"headline":"string","lens":"future_demand|earnings_quality|operating_leverage|capital_allocation|market_expectations|market_positioning|company_risk|other","finding":"string","cause":"string","durability":"recurring|temporary|one_time|unresolved","time_horizon":"near_term|medium_term|long_term|unresolved","investor_implication":"string","expectation_gap":"string or null","scenario_path":"string or null","what_to_watch":["observable signal"],"catalyst":"string or null","likelihood":"low|medium|high|unresolved","impact":"low|medium|high|unresolved","confidence":"low|medium|high","claim_ids":["exact-claim-id"]}}]}}."""
        final = await self._generate(final_prompt)
        return DeepAnalysis.model_validate(final), self.model
