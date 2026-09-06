from __future__ import annotations

from ..models import CategoryScores, DeepAnalysis, EvidenceBundle, MetricSnapshot


class DeterministicDeepAnalysisProvider:
    """Evidence-aware fallback used when an LLM provider is not configured.

    The fallback deliberately does not invent facts. It converts Warren's
    deterministic category scores and retrieved evidence into a concise,
    explainable research summary so Deep mode remains usable without an API key.
    Technical and insider observations can enrich the narrative but do not alter
    the current uncalibrated verdict thresholds.
    """

    @staticmethod
    def _pct(value: float | None) -> str | None:
        if value is None:
            return None
        return f"{value * 100:.1f}%"

    @staticmethod
    def _money(value: float | None) -> str | None:
        if value is None:
            return None
        absolute = abs(value)
        if absolute >= 1_000_000_000:
            return f"${value / 1_000_000_000:.1f}B"
        if absolute >= 1_000_000:
            return f"${value / 1_000_000:.1f}M"
        return f"${value:,.0f}"

    @classmethod
    def _comparison_text(cls, metrics: MetricSnapshot, metric_name: str) -> str | None:
        comparison = next(
            (item for item in metrics.quarterly_comparisons if item.metric == metric_name),
            None,
        )
        if comparison is None:
            return None
        current = cls._money(comparison.current) if comparison.unit == "money" else cls._pct(comparison.current)
        changes: list[str] = []
        for label, prior in (
            ("last quarter", comparison.previous_quarter),
            ("the same quarter last year", comparison.year_ago),
        ):
            if prior is None:
                continue
            if comparison.unit == "percent":
                difference = (comparison.current - prior) * 100
                changes.append(f"{abs(difference):.1f} percentage points {'above' if difference >= 0 else 'below'} {label}")
            elif prior:
                change = comparison.current / prior - 1
                changes.append(f"{abs(change) * 100:.1f}% {'above' if change >= 0 else 'below'} {label}")
        suffix = f" ({'; '.join(changes)})" if changes else ""
        return f"{comparison.label.lower()} {current}{suffix}"

    @classmethod
    def _category_inputs(cls, label: str, metrics: MetricSnapshot) -> str:
        fcf_yield = (
            metrics.free_cash_flow / metrics.market_cap
            if metrics.free_cash_flow is not None and metrics.market_cap and metrics.market_cap > 0
            else None
        )
        inputs: dict[str, list[str | None]] = {
            "fundamentals": [
                f"free cash flow {cls._money(metrics.free_cash_flow)} ({'positive and supportive' if metrics.free_cash_flow > 0 else 'negative and a concern'})" if metrics.free_cash_flow is not None else None,
                f"operating cash flow {cls._money(metrics.operating_cash_flow)} ({'positive and supportive' if metrics.operating_cash_flow > 0 else 'negative and a concern'})" if metrics.operating_cash_flow is not None else None,
                f"current ratio {metrics.current_ratio:.2f} ({'healthy short-term cushion' if metrics.current_ratio >= 1.5 else 'adequate' if metrics.current_ratio >= 1 else 'below 1.0, indicating limited short-term cushion'})" if metrics.current_ratio is not None else None,
                f"debt-to-equity {metrics.debt_to_equity:.0f} ({'conservative' if metrics.debt_to_equity <= 50 else 'moderate' if metrics.debt_to_equity <= 100 else 'elevated'})" if metrics.debt_to_equity is not None else None,
                f"profit margin {cls._pct(metrics.profit_margin)} ({'strong' if metrics.profit_margin >= .12 else 'moderate' if metrics.profit_margin >= .07 else 'thin'})" if metrics.profit_margin is not None else None,
            ],
            "valuation": [
                f"trailing P/E {metrics.trailing_pe:.1f}x ({'inexpensive' if metrics.trailing_pe <= 22 else 'moderate' if metrics.trailing_pe <= 40 else 'demanding'})" if metrics.trailing_pe is not None else None,
                f"forward P/E {metrics.forward_pe:.1f}x ({'inexpensive' if metrics.forward_pe <= 22 else 'moderate' if metrics.forward_pe <= 40 else 'demanding'})" if metrics.forward_pe is not None else None,
                f"PEG {metrics.peg_ratio:.1f} ({'supportive' if metrics.peg_ratio <= 1.5 else 'demanding relative to growth'})" if metrics.peg_ratio is not None else None,
                f"EV/EBITDA {metrics.enterprise_to_ebitda:.1f}x ({'supportive' if metrics.enterprise_to_ebitda <= 15 else 'moderate' if metrics.enterprise_to_ebitda <= 20 else 'demanding'})" if metrics.enterprise_to_ebitda is not None else None,
                f"FCF yield {cls._pct(fcf_yield)} ({'strong cash-flow value' if fcf_yield >= .06 else 'moderate' if fcf_yield >= .04 else 'low cash-flow yield'})" if fcf_yield is not None else None,
            ],
            "business quality": [
                f"ROE {cls._pct(metrics.return_on_equity)} ({'strong' if metrics.return_on_equity >= .18 else 'moderate' if metrics.return_on_equity >= .12 else 'weak'})" if metrics.return_on_equity is not None else None,
                f"ROA {cls._pct(metrics.return_on_assets)} ({'strong' if metrics.return_on_assets >= .08 else 'moderate' if metrics.return_on_assets >= .05 else 'weak'})" if metrics.return_on_assets is not None else None,
                f"gross margin {cls._pct(metrics.gross_margin)} ({'strong' if metrics.gross_margin >= .45 else 'moderate' if metrics.gross_margin >= .30 else 'lower'})" if metrics.gross_margin is not None else None,
                f"operating margin {cls._pct(metrics.operating_margin)} ({'strong' if metrics.operating_margin >= .18 else 'healthy' if metrics.operating_margin >= .12 else 'lower'})" if metrics.operating_margin is not None else None,
                f"free cash flow {cls._money(metrics.free_cash_flow)} ({'positive and supportive' if metrics.free_cash_flow > 0 else 'negative and a concern'})" if metrics.free_cash_flow is not None else None,
            ],
            "growth": [
                f"revenue growth {cls._pct(metrics.revenue_growth)} ({'strong' if metrics.revenue_growth >= .08 else 'modest' if metrics.revenue_growth >= .03 else 'flat or declining'})" if metrics.revenue_growth is not None else None,
                f"earnings growth {cls._pct(metrics.earnings_growth)} ({'strong' if metrics.earnings_growth >= .08 else 'modest' if metrics.earnings_growth >= .03 else 'flat or declining'})" if metrics.earnings_growth is not None else None,
            ],
            "risk resilience": [
                f"beta {metrics.beta:.2f}" if metrics.beta is not None else None,
                f"debt-to-equity {metrics.debt_to_equity:.0f}" if metrics.debt_to_equity is not None else None,
                f"current ratio {metrics.current_ratio:.2f}" if metrics.current_ratio is not None else None,
                f"free cash flow {cls._money(metrics.free_cash_flow)}" if metrics.free_cash_flow is not None else None,
            ],
            "market context": [
                f"share price {cls._money(metrics.price)}" if metrics.price is not None else None,
                f"50-day average {cls._money(metrics.fifty_day_average)}" if metrics.fifty_day_average is not None else None,
                f"200-day average {cls._money(metrics.two_hundred_day_average)}" if metrics.two_hundred_day_average is not None else None,
                f"52-week high {cls._money(metrics.fifty_two_week_high)}" if metrics.fifty_two_week_high is not None else None,
            ],
        }
        comparison_metrics = {
            "fundamentals": ["quarterly_free_cash_flow", "quarterly_operating_cash_flow"],
            "business quality": ["quarterly_operating_margin", "quarterly_gross_margin"],
            "growth": ["quarterly_revenue", "quarterly_net_income"],
            "risk resilience": ["quarterly_free_cash_flow"],
        }
        comparisons = [
            value
            for metric_name in comparison_metrics.get(label, [])
            if (value := cls._comparison_text(metrics, metric_name))
        ]
        available = [value for value in inputs.get(label, []) if value] + comparisons
        return "; ".join(available) if available else "underlying inputs were unavailable"

    @staticmethod
    def _category_label(score: float) -> str:
        if score >= 80:
            return "strong"
        if score >= 65:
            return "above average"
        if score >= 50:
            return "mixed"
        if score >= 35:
            return "weak"
        return "very weak"

    @classmethod
    def _category_argument(cls, label: str, metrics: MetricSnapshot, supportive: bool) -> str:
        titles = {
            "fundamentals": "Cash generation and financial position",
            "valuation": "The current valuation",
            "business quality": "Profitability and business quality",
            "growth": "The growth trend",
            "risk resilience": "Financial resilience",
            "market context": "The share-price trend",
        }
        implications = {
            "fundamentals": (
                "Positive cash generation gives the company more capacity to reinvest, repay debt or return capital."
                if supportive else
                "Weak cash generation or limited balance-sheet flexibility leaves less room for setbacks."
            ),
            "valuation": (
                "A less demanding price gives investors more room for imperfect results."
                if supportive else
                "A demanding price leaves less room for earnings or growth to disappoint."
            ),
            "business quality": (
                "Healthy returns and margins can make earnings more durable through changing conditions."
                if supportive else
                "Lower returns or margins can make earnings more vulnerable to cost and demand pressure."
            ),
            "growth": (
                "Improving sales and earnings can support future cash flow if the trend continues."
                if supportive else
                "Slower or uneven growth makes it harder to justify optimistic expectations."
            ),
            "risk resilience": (
                (
                    "Positive cash generation provides support, but a current ratio below 1.0 limits the short-term liquidity cushion."
                    if metrics.current_ratio is not None and metrics.current_ratio < 1 else
                    "The observed financial cushion can help the company absorb normal business volatility."
                )
                if supportive else
                "The observed financial cushion may be limited if operating conditions deteriorate."
            ),
            "market context": (
                "The market trend is supportive, although price momentum does not establish business value."
                if supportive else
                "Weak price momentum can signal investor caution, although it does not establish business value."
            ),
        }
        return f"{titles[label]}: {cls._category_inputs(label, metrics)}. Why it matters: {implications[label]}"

    @staticmethod
    def _verdict(scores: CategoryScores) -> str:
        if (
            scores.overall >= 72
            and scores.valuation >= 58
            and scores.fundamentals >= 62
            and scores.business_quality >= 60
            and scores.risk_resilience >= 50
        ):
            return "attractive"
        if (
            scores.overall < 45
            or scores.fundamentals < 35
            or scores.business_quality < 35
            or scores.risk_resilience < 30
        ):
            return "avoid"
        return "watch"

    @staticmethod
    def _confidence(metrics: MetricSnapshot, evidence: EvidenceBundle) -> str:
        fields = [
            metrics.trailing_pe,
            metrics.forward_pe,
            metrics.free_cash_flow,
            metrics.revenue_growth,
            metrics.earnings_growth,
            metrics.operating_margin,
            metrics.return_on_equity,
            metrics.debt_to_equity,
            metrics.current_ratio,
        ]
        missing = sum(v is None for v in fields)
        problematic_sources = sum(
            status.status in {"unavailable", "error"} for status in evidence.source_status
        )
        if missing <= 2 and problematic_sources == 0:
            return "high"
        if missing <= 5 and problematic_sources <= 2:
            return "medium"
        return "low"

    @staticmethod
    def _top_categories(scores: CategoryScores) -> list[tuple[str, float]]:
        values = [
            ("fundamentals", scores.fundamentals),
            ("valuation", scores.valuation),
            ("business quality", scores.business_quality),
            ("growth", scores.growth),
            ("risk resilience", scores.risk_resilience),
            ("market context", scores.market_context),
        ]
        return sorted(values, key=lambda item: item[1], reverse=True)

    @staticmethod
    def _technical_context(evidence: EvidenceBundle) -> tuple[list[str], list[str]]:
        if not evidence.technical:
            return [], []
        technical = evidence.technical[0]
        supportive: list[str] = []
        cautious: list[str] = []

        if technical.close is not None and technical.sma_200 is not None:
            if technical.close >= technical.sma_200:
                supportive.append(
                    f"Price is above the 200-day moving average ({technical.close:.2f} vs {technical.sma_200:.2f}). Why it matters: this suggests supportive long-term momentum, but it does not establish that the shares are undervalued."
                )
            else:
                cautious.append(
                    f"Price is below the 200-day moving average ({technical.close:.2f} vs {technical.sma_200:.2f}). Why it matters: this suggests cautious long-term momentum, but it does not establish that the business is weak."
                )
        if technical.close is not None and technical.sma_50 is not None:
            if technical.close >= technical.sma_50:
                supportive.append(
                    f"Price is above the 50-day moving average ({technical.close:.2f} vs {technical.sma_50:.2f}). Why it matters: recent market momentum is supportive, although it can change quickly."
                )
            else:
                cautious.append(
                    f"Price is below the 50-day moving average ({technical.close:.2f} vs {technical.sma_50:.2f}). Why it matters: recent market momentum is cautious, although it can change quickly."
                )
        if technical.rsi_14 is not None:
            if technical.rsi_14 >= 70:
                cautious.append(f"14-day RSI is {technical.rsi_14:.1f}, an elevated short-term momentum reading.")
            elif technical.rsi_14 <= 30:
                cautious.append(f"14-day RSI is {technical.rsi_14:.1f}, reflecting weak/oversold short-term momentum.")
        if technical.macd is not None and technical.macd_signal is not None:
            if technical.macd >= technical.macd_signal:
                supportive.append(
                    f"MACD is above its signal line ({technical.macd:.3f} vs {technical.macd_signal:.3f})."
                )
            else:
                cautious.append(
                    f"MACD is below its signal line ({technical.macd:.3f} vs {technical.macd_signal:.3f})."
                )
        return supportive, cautious

    @staticmethod
    def _insider_context(evidence: EvidenceBundle) -> tuple[list[str], list[str]]:
        supportive: list[str] = []
        cautious: list[str] = []
        for item in evidence.insider_transactions[:5]:
            transaction = (item.transaction or "").lower()
            actor = item.insider or "an insider"
            date_text = item.start_date.isoformat() if item.start_date else "an unspecified date"
            if "purchase" in transaction or "buy" in transaction:
                supportive.append(
                    f"Structured insider data reports a purchase by {actor} on {date_text}; insider activity is contextual evidence, not a standalone thesis."
                )
            elif "sale" in transaction or "sell" in transaction:
                cautious.append(
                    f"Structured insider data reports a sale by {actor} on {date_text}; insider sales may be scheduled or liquidity-driven and are not independently decisive."
                )
        return supportive, cautious

    async def analyze(
        self,
        metrics: MetricSnapshot,
        scores: CategoryScores,
        evidence: EvidenceBundle,
    ) -> tuple[DeepAnalysis, str | None]:
        ranked = self._top_categories(scores)
        verdict = self._verdict(scores)
        confidence = self._confidence(metrics, evidence)

        positives: list[str] = []
        concerns: list[str] = []

        for label, score in ranked[:3]:
            if score >= 60:
                positives.append(self._category_argument(label, metrics, supportive=True))

        if metrics.free_cash_flow is not None:
            positives.append(
                "Free cash flow is positive."
                if metrics.free_cash_flow > 0
                else "Free cash flow is negative, which weakens the investment case."
            )
        if metrics.operating_margin is not None and metrics.operating_margin >= 0.15:
            positives.append(f"Operating margin is {self._pct(metrics.operating_margin)}, supporting business-quality resilience.")
        if metrics.revenue_growth is not None and metrics.revenue_growth >= 0.08:
            positives.append(f"Reported revenue growth is {self._pct(metrics.revenue_growth)}.")

        for label, score in reversed(ranked[-3:]):
            if score < 55:
                concerns.append(self._category_argument(label, metrics, supportive=False))

        if metrics.trailing_pe is not None and metrics.trailing_pe >= 35:
            concerns.append(f"Trailing P/E is {metrics.trailing_pe:.1f}x, so the current price embeds a relatively demanding earnings multiple.")
        if metrics.debt_to_equity is not None and metrics.debt_to_equity >= 150:
            concerns.append(f"Debt-to-equity is {metrics.debt_to_equity:.0f}, which warrants closer balance-sheet review.")
        if metrics.current_ratio is not None and metrics.current_ratio < 1:
            concerns.append(f"Current ratio is {metrics.current_ratio:.2f}, indicating limited short-term balance-sheet cushion by this measure.")
        if metrics.earnings_growth is not None and metrics.earnings_growth < 0:
            concerns.append(f"Reported earnings growth is {self._pct(metrics.earnings_growth)}, a negative growth signal.")

        positives = positives[:5] or ["No strong positive signal is available from the currently observed metrics."]
        concerns = concerns[:5] or ["No major quantitative weakness is dominant, but the evidence set remains incomplete and should be reviewed alongside primary sources."]

        technical_support, technical_caution = self._technical_context(evidence)
        insider_support, insider_caution = self._insider_context(evidence)

        bull_case = positives[:3]
        bull_case.extend(technical_support[:1])
        if len(bull_case) < 4:
            bull_case.extend(insider_support[: 4 - len(bull_case)])
        if len(bull_case) < 4 and evidence.estimate_revisions:
            bull_case.append("Analyst estimate/revision evidence is available for review in the evidence packet.")

        bear_case = concerns[:3]
        bear_case.extend(technical_caution[:1])
        if len(bear_case) < 4:
            bear_case.extend(insider_caution[: 4 - len(bear_case)])
        if len(bear_case) < 4 and evidence.source_status:
            unavailable = [s.source for s in evidence.source_status if s.status in {"unavailable", "error"}]
            if unavailable:
                bear_case.append(f"Some evidence sources are unavailable or errored: {', '.join(unavailable[:3])}.")

        risks = concerns[:3]
        risks.extend(insider_caution[:1])
        if not evidence.filings:
            risks.append("No filing evidence is available in the current packet; primary-source review remains important.")
        if not evidence.news and len(risks) < 5:
            risks.append("No recent headline evidence is available in the current packet.")
        risks = risks[:5]

        if verdict == "attractive":
            thesis = (
                f"{metrics.company_name or metrics.ticker} currently screens as Attractive because business quality, "
                "fundamentals, valuation and financial resilience are sufficiently supportive at the current price. "
                "The conclusion is research-oriented and should be revisited when price, earnings, filings or estimate revisions change."
            )
            changes = [
                "A material deterioration in free cash flow, margins or balance-sheet resilience.",
                "Valuation becoming materially more demanding without a corresponding improvement in growth or fundamentals.",
                "New primary-source evidence that weakens the business-quality or risk thesis.",
            ]
        elif verdict == "avoid":
            thesis = (
                f"{metrics.company_name or metrics.ticker} currently screens as Avoid because one or more fundamental, "
                "business-quality or financial-resilience concerns make the risk/reward unfavorable at the current price."
            )
            changes = [
                "Clear improvement in the weakest fundamental or business-quality factors.",
                "A materially better valuation with evidence that the underlying business is stabilizing.",
                "New filings, earnings or estimate evidence that resolves the dominant downside risks.",
            ]
        else:
            thesis = (
                f"{metrics.company_name or metrics.ticker} currently belongs on Watch because the evidence does not yet "
                "support an Attractive or Avoid conclusion. "
                "The setup has meaningful strengths and unresolved trade-offs."
            )
            changes = [
                "A more attractive valuation or stronger free-cash-flow yield without deterioration in quality.",
                "Improving earnings/revenue trends or estimate revisions that strengthen the growth case.",
                "Material deterioration in fundamentals, risk resilience or primary-source evidence, which could move the view to Avoid.",
            ]

        return (
            DeepAnalysis(
                thesis=thesis,
                positives=positives,
                concerns=concerns,
                bull_case=bull_case[:4],
                bear_case=bear_case[:4],
                risks=risks,
                what_would_change_view=changes,
                verdict=verdict,
                confidence=confidence,
            ),
            "deterministic-v1.1",
        )
