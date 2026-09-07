from __future__ import annotations

from ..models import AnalysisCitation, CategoryScores, DeepAnalysis, EvidenceBundle, InvestmentInsight, MetricSnapshot
from .drivers import earnings_bridge


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
        unavailable_sources = sum(
            status.status in {"unavailable", "error"} for status in evidence.source_status
        )
        partial_sources = sum(status.status == "partial" for status in evidence.source_status)
        if missing <= 2 and unavailable_sources == 0 and partial_sources == 0:
            return "high"
        if missing <= 5 and unavailable_sources <= 2:
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
    def _rank_insights(items: list[InvestmentInsight]) -> list[InvestmentInsight]:
        """Show only the most decision-relevant, well-supported arguments."""
        weight = {"high": 3, "medium": 2, "low": 1, "unresolved": 0}
        ranked = sorted(
            enumerate(items),
            key=lambda pair: (
                weight.get(pair[1].impact, 0),
                weight.get(pair[1].confidence, 0),
                weight.get(pair[1].likelihood, 0),
                -pair[0],
            ),
            reverse=True,
        )
        return [item for _, item in ranked[:6]]

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

    @classmethod
    def _forward_estimate_context(
        cls, evidence: EvidenceBundle
    ) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        """Turn structured consensus data into sourced forward-looking arguments."""
        bullish: list[tuple[str, str]] = []
        bearish: list[tuple[str, str]] = []
        horizon_labels = {
            "0q": "the current quarter",
            "+1q": "the next quarter",
            "0y": "the current year",
            "+1y": "the next year",
        }
        claim_by_horizon = {
            claim.metadata.get("horizon"): claim.id
            for claim in evidence.claims
            if claim.category == "estimate_revision" and claim.metadata.get("horizon")
        }

        for item in evidence.estimate_revisions:
            claim_id = claim_by_horizon.get(item.horizon)
            if not claim_id:
                continue
            label = horizon_labels.get(item.horizon, item.horizon)
            estimate_parts: list[str] = []
            if item.revenue_growth is not None:
                estimate_parts.append(f"revenue growth of {cls._pct(item.revenue_growth)}")
            if item.earnings_growth is not None:
                estimate_parts.append(f"earnings growth of {cls._pct(item.earnings_growth)}")
            revision_text = None
            revision_change = None
            if item.eps_current is not None and item.eps_30d_ago not in (None, 0):
                revision_change = item.eps_current / item.eps_30d_ago - 1
                revision_text = (
                    f"the consensus EPS estimate moved {abs(revision_change) * 100:.1f}% "
                    f"{'higher' if revision_change >= 0 else 'lower'} over the past 30 days"
                )
            breadth_text = None
            if item.eps_up_30d is not None or item.eps_down_30d is not None:
                breadth_text = (
                    f"{item.eps_up_30d or 0} analysts raised estimates and "
                    f"{item.eps_down_30d or 0} lowered them"
                )

            details = "; ".join(estimate_parts + [x for x in (revision_text, breadth_text) if x])
            if not details:
                continue
            if revision_change is not None and revision_change >= 0.02:
                bullish.append((
                    f"Earnings expectations are improving: for {label}, analysts report {details}. "
                    "Why it matters: rising estimates suggest that expected future earnings have improved, although estimates can still change.",
                    claim_id,
                ))
            elif (
                item.revenue_growth is not None and item.revenue_growth >= 0.05
                and item.earnings_growth is not None and item.earnings_growth >= 0.05
                and item.horizon in {"0y", "+1y"}
            ):
                bullish.append((
                    f"Analysts expect continued growth: for {label}, analysts report {details}. "
                    "Why it matters: simultaneous revenue and earnings growth would support the operating outlook, although the estimates may already be reflected in the share price.",
                    claim_id,
                ))
            if item.revenue_growth is not None and item.revenue_growth < 0:
                bearish.append((
                    f"Revenue expectations are contracting: for {label}, analysts report {details}. "
                    "Why it matters: check transaction effects, currency and customer volumes before attributing the forecast to weaker demand.",
                    claim_id,
                ))
        return bullish, bearish

    @classmethod
    def _structured_insights(
        cls,
        metrics: MetricSnapshot,
        evidence: EvidenceBundle,
        forward_support: list[tuple[str, str]],
        forward_caution: list[tuple[str, str]],
    ) -> tuple[list[InvestmentInsight], list[InvestmentInsight]]:
        bull: list[InvestmentInsight] = []
        bear: list[InvestmentInsight] = []

        if forward_support:
            text, claim_id = forward_support[0]
            raised = text.startswith("Earnings expectations are improving")
            bull.append(InvestmentInsight(
                headline=(
                    "Analysts are raising near-term earnings expectations"
                    if raised else "Analysts expect revenue and earnings to keep growing"
                ),
                lens="future_demand",
                finding=text.split(" Why it matters:", 1)[0],
                cause=(
                    "The structured consensus data shows upward EPS revisions; the operating cause still requires confirmation from guidance and company filings."
                    if raised else "The structured consensus forecast expects both sales and earnings to grow; company guidance and reported results must confirm the operating drivers."
                ),
                durability="unresolved",
                time_horizon="near_term",
                investor_implication="If revenue and operating performance begin supporting the higher estimates, future earnings could improve faster than previously expected. Estimate increases without stronger demand would be less durable.",
                expectation_gap="The revisions indicate that consensus earnings expectations are moving higher, but the price may already reflect part of that improvement.",
                scenario_path="The Bull case strengthens if revenue estimates, customer demand and margins improve together; it weakens if EPS rises only through cost reductions.",
                what_to_watch=["Revenue-estimate revisions", "Customer demand or volume", "Management guidance", "Operating margin"],
                catalyst="The next earnings report and guidance update",
                likelihood="medium",
                impact="medium",
                confidence="medium",
                claim_ids=[claim_id],
            ))

        margin = next((x for x in metrics.quarterly_comparisons if x.metric == "quarterly_operating_margin"), None)
        if margin and any(value is not None and margin.current > value for value in (margin.previous_quarter, margin.year_ago)):
            finding = cls._comparison_text(metrics, "quarterly_operating_margin") or "Operating margin improved."
            bull.append(InvestmentInsight(
                headline="The company is retaining more operating profit from each sales dollar",
                lens="operating_leverage",
                finding=f"The statements show {finding}.",
                cause="The available statements establish the margin improvement but do not by themselves identify whether pricing, mix, labor, restructuring or other costs caused it.",
                durability="unresolved",
                time_horizon="medium_term",
                investor_implication="If the higher margin is operational and persists when demand grows, earnings and cash flow can rise faster than revenue. If it came from temporary reductions, the benefit may fade.",
                expectation_gap="Durable margin expansion can exceed market expectations when revenue resumes growing, but temporary savings do not justify a lasting rerating.",
                scenario_path="Margins remain higher as revenue grows in the Bull path; margins retreat when temporary savings end in the failure path.",
                what_to_watch=["Operating expense disclosures", "Gross margin", "Revenue and transaction growth", "Operating cash flow"],
                catalyst="The next filing's margin and operating-expense disclosures",
                likelihood="medium",
                impact="medium",
                confidence="medium",
            ))

        if forward_caution:
            text, claim_id = forward_caution[0]
            bear.append(InvestmentInsight(
                headline="Revenue expectations indicate that demand still needs to prove itself",
                lens="future_demand",
                finding=text.split(" Why it matters:", 1)[0],
                cause="Consensus revenue expectations are contracting, but revenue alone cannot distinguish customer demand from currency, pricing, mix or portfolio changes.",
                durability="unresolved",
                time_horizon="near_term",
                investor_implication="If customer volumes remain weak, cost improvements have a ceiling and optimistic earnings expectations become harder to sustain.",
                expectation_gap="Current earnings expectations require demand to stabilize; continued revenue contraction would make those expectations harder to achieve.",
                scenario_path="The Bear path is confirmed if revenue estimates, volumes or transactions continue falling while earnings rely on cost reductions.",
                what_to_watch=["Customer traffic, transactions or units", "Revenue revisions", "Pricing versus volume", "Management demand guidance"],
                catalyst="The next revenue forecast and earnings call",
                likelihood="medium",
                impact="high",
                confidence="medium",
                claim_ids=[claim_id],
            ))

        bridge = earnings_bridge(metrics)
        if metrics.revenue_growth is not None and metrics.revenue_growth < 0 and metrics.earnings_growth is not None and metrics.earnings_growth > 0:
            if bridge.get("status") == "available":
                operating = bridge["operating_income_change"]
                non_operating = bridge["below_operating_income_change"]
                if abs(non_operating) > abs(operating):
                    cause = (
                        "Most of the year-over-year profit change occurred below operating income rather than in the core business. "
                        "The available statement data does not identify the specific gain or adjustment, so that portion should not be treated as recurring until the filing explains it."
                    )
                else:
                    cause = (
                        "Most of the year-over-year profit improvement came from operating income, indicating that the core business contributed more than non-operating items. "
                        "The next filing should confirm whether the improvement came from durable margins, pricing, volume or temporary cost reductions."
                    )
            else:
                cause = "Aligned statement data is missing, so the analysis cannot yet separate operating improvement from taxes, gains or other non-operating effects."
            bear.append(InvestmentInsight(
                headline="Profit growth is running ahead of sales growth",
                lens="earnings_quality",
                finding=f"Revenue growth was {cls._pct(metrics.revenue_growth)} while earnings growth was {cls._pct(metrics.earnings_growth)}.",
                cause=cause,
                durability="unresolved",
                time_horizon="medium_term",
                investor_implication="The earnings recovery is not yet confirmed by top-line growth. Its durability depends on whether the improvement came from repeatable operations rather than taxes, transactions or finite cost reductions.",
                expectation_gap="Investors may be valuing the earnings increase as recurring before the statements establish that the improvement came from repeatable operations.",
                scenario_path="The concern fades if operating income and cash flow confirm the improvement; it grows if future profit falls after one-time benefits disappear.",
                what_to_watch=["Revenue growth", "Operating income", "Tax and other-income disclosures", "Free cash flow"],
                catalyst="The next income statement, cash-flow statement and explanatory filing notes",
                likelihood="high",
                impact="high",
                confidence="medium" if bridge.get("status") == "available" else "low",
            ))

        if metrics.trailing_pe is not None and metrics.trailing_pe >= 35:
            bear.append(InvestmentInsight(
                headline="The valuation leaves limited room for execution disappointment",
                lens="market_expectations",
                finding=f"The shares trade at {metrics.trailing_pe:.1f}x trailing earnings" + (f" and {metrics.forward_pe:.1f}x forward earnings." if metrics.forward_pe is not None else "."),
                cause="The market is assigning a demanding earnings multiple, which implies confidence in future growth, margin durability or both.",
                durability="recurring",
                time_horizon="medium_term",
                investor_implication="Even improving results may not support the share price if growth or margins fall short of the expectations embedded in the multiple.",
                expectation_gap="The multiple implies sustained growth and margin execution; merely meeting historical performance may not be enough.",
                scenario_path="A rerating is possible if growth exceeds expectations, while slower growth or lower margins could compress the multiple even if the company remains profitable.",
                what_to_watch=["Forward earnings estimates", "Revenue growth", "Operating margin", "Valuation after earnings updates"],
                catalyst="Earnings releases and material estimate revisions",
                likelihood="medium",
                impact="high",
                confidence="high",
            ))

        if evidence.technical:
            technical = evidence.technical[0]
            price_extension = (
                technical.close / technical.sma_50 - 1
                if technical.close is not None and technical.sma_50 not in (None, 0)
                else None
            )
            volume_ratio = (
                technical.latest_volume / technical.avg_volume_20
                if technical.latest_volume is not None and technical.avg_volume_20 not in (None, 0)
                else None
            )
            stretched = (
                (technical.rsi_14 is not None and technical.rsi_14 >= 70)
                or (price_extension is not None and price_extension >= 0.12)
                or (volume_ratio is not None and volume_ratio >= 1.5 and technical.rsi_14 is not None and technical.rsi_14 >= 65)
            )
            if stretched:
                observations = []
                if technical.rsi_14 is not None:
                    observations.append(f"14-day RSI is {technical.rsi_14:.1f}")
                if price_extension is not None:
                    observations.append(f"the price is {price_extension * 100:.1f}% above its 50-day average")
                if volume_ratio is not None:
                    observations.append(f"latest volume is {volume_ratio:.1f}x its 20-day average")
                finding = "; ".join(observations)
                finding = finding[:1].upper() + finding[1:] + "."
                bear.append(InvestmentInsight(
                    headline="Trading enthusiasm looks stretched",
                    lens="market_positioning",
                    finding=finding,
                    cause="Elevated momentum and trading activity indicate strong near-term investor demand for the shares, not an improvement in the company's underlying cash flows.",
                    durability="temporary",
                    time_horizon="near_term",
                    investor_implication="A crowded or extended trade can fall sharply when results merely meet expectations, even when the long-term business remains strong.",
                    expectation_gap="The share price may be discounting near-perfect near-term execution while technical momentum leaves less room for incremental buyers.",
                    scenario_path="The risk recedes if earnings and estimates rise enough to support the price; it increases if momentum reverses after an earnings or guidance disappointment.",
                    what_to_watch=["RSI returning below 70", "Distance from the 50-day average", "Volume after earnings", "Estimate revisions"],
                    catalyst="The next earnings report, guidance update or material estimate revision",
                    likelihood="medium",
                    impact="medium",
                    confidence="high",
                ))
            weakening = (
                technical.close is not None
                and technical.sma_50 is not None
                and technical.sma_200 is not None
                and technical.close < technical.sma_50
                and technical.close < technical.sma_200
                and (
                    technical.rsi_14 is None or technical.rsi_14 < 45
                )
            )
            if weakening:
                bear.append(InvestmentInsight(
                    headline="Market momentum is weakening",
                    lens="market_positioning",
                    finding=(
                        f"The shares trade below both the 50-day and 200-day averages"
                        + (f", while 14-day RSI is {technical.rsi_14:.1f}." if technical.rsi_14 is not None else ".")
                    ),
                    cause="Recent selling pressure has been stronger than the stock's intermediate- and long-term price trends, although price action alone does not establish weaker business fundamentals.",
                    durability="temporary",
                    time_horizon="near_term",
                    investor_implication="Weak momentum can amplify a decline if earnings or guidance disappoint, especially when the valuation already requires strong execution.",
                    expectation_gap="The market may be reducing the premium it is willing to pay before analysts materially lower their published forecasts.",
                    scenario_path="Momentum can recover if results exceed expectations; the risk increases if estimates fall while the price remains below both averages.",
                    what_to_watch=["Price versus the 50-day average", "Price versus the 200-day average", "RSI", "Estimate revisions"],
                    catalyst="The next earnings report or material estimate revision",
                    likelihood="medium",
                    impact="medium",
                    confidence="high",
                ))

        if metrics.free_cash_flow is not None and metrics.free_cash_flow > 0:
            bull.append(InvestmentInsight(
                headline="Positive cash generation provides strategic flexibility",
                lens="capital_allocation",
                finding=f"The company generated {cls._money(metrics.free_cash_flow)} of free cash flow.",
                cause="The available cash-flow data confirms positive cash generation, but its recurring operating drivers require filing-level attribution.",
                durability="unresolved",
                time_horizon="medium_term",
                investor_implication="Sustained cash generation can fund reinvestment, debt reduction or shareholder returns without relying on new financing.",
                expectation_gap="Value creation depends on management earning attractive returns on the cash it retains or returning excess cash responsibly.",
                scenario_path="The Bull path requires cash to fund profitable reinvestment, debt reduction or disciplined shareholder returns rather than low-return spending.",
                what_to_watch=["Free cash flow across subsequent quarters", "Working capital", "Capital expenditure", "Net debt"],
                confidence="medium",
            ))

        if metrics.revenue_growth is not None and metrics.revenue_growth >= 0.05:
            bull.append(InvestmentInsight(
                headline="Customer spending is supporting meaningful sales growth",
                lens="future_demand",
                finding=f"Reported revenue growth is {cls._pct(metrics.revenue_growth)}.",
                cause="The reported top-line growth shows that demand, pricing, mix or a combination of them is expanding sales; the available aggregate data does not separate those drivers.",
                durability="unresolved", time_horizon="near_term",
                investor_implication="Continued sales growth gives future earnings more room to expand without relying only on cost cutting.",
                expectation_gap="The investment case is stronger if volume or customer activity—not price alone—is sustaining this growth.",
                scenario_path="The Bull path requires sales growth to persist while margins and cash conversion remain stable.",
                what_to_watch=["Customer traffic, transactions or units", "Revenue-estimate revisions", "Pricing versus volume"],
                likelihood="medium", impact="high", confidence="medium",
            ))

        if metrics.return_on_assets is not None and metrics.return_on_assets >= 0.07:
            bull.append(InvestmentInsight(
                headline="The business earns a productive return on its asset base",
                lens="capital_allocation",
                finding=f"Return on assets is {cls._pct(metrics.return_on_assets)}.",
                cause="The company is producing meaningful profit relative to the assets required to operate the business.",
                durability="recurring", time_horizon="long_term",
                investor_implication="Productive assets can support compounding when management reinvests at similar returns.",
                expectation_gap="Future value creation depends on new investment earning returns close to the existing business.",
                scenario_path="The advantage strengthens if returns remain stable as the asset base grows; it weakens if expansion requires progressively more capital.",
                what_to_watch=["Return on assets", "Capital expenditure", "Revenue generated per dollar of assets"],
                likelihood="medium", impact="medium", confidence="medium",
            ))

        if metrics.total_cash is not None and metrics.total_debt is not None and metrics.total_cash >= metrics.total_debt:
            bull.append(InvestmentInsight(
                headline="Cash covers the reported debt balance",
                lens="company_risk",
                finding=f"Reported cash of {cls._money(metrics.total_cash)} is at least as large as debt of {cls._money(metrics.total_debt)}.",
                cause="The balance sheet currently shows more cash than debt.",
                durability="unresolved", time_horizon="medium_term",
                investor_implication="This financial cushion can protect reinvestment plans and reduce refinancing pressure during weaker periods.",
                expectation_gap="The benefit lasts only if cash is not consumed by acquisitions, buybacks or operating deterioration.",
                scenario_path="The cushion remains valuable if operating cash flow replenishes spending and distributions.",
                what_to_watch=["Net cash or net debt", "Operating cash flow", "Acquisition and buyback spending"],
                likelihood="medium", impact="medium", confidence="high",
            ))

        fcf_yield = metrics.free_cash_flow / metrics.market_cap if metrics.free_cash_flow is not None and metrics.market_cap not in (None, 0) else None
        if fcf_yield is not None and fcf_yield < 0.025:
            bear.append(InvestmentInsight(
                headline="The current price offers a low cash-flow yield",
                lens="market_expectations",
                finding=f"Free-cash-flow yield is approximately {cls._pct(fcf_yield)}.",
                cause="The market capitalization is large relative to the cash the business currently generates.",
                durability="recurring", time_horizon="medium_term",
                investor_implication="The shares need substantial future cash-flow growth to produce an attractive return from today's price.",
                expectation_gap="A low starting yield leaves little protection if growth disappoints.",
                scenario_path="The concern fades if cash flow compounds rapidly; it worsens if cash generation stalls while the valuation remains elevated.",
                what_to_watch=["Free-cash-flow growth", "Free-cash-flow margin", "Market value relative to cash flow"],
                likelihood="medium", impact="high", confidence="high",
            ))

        if metrics.profit_margin is not None and metrics.profit_margin < 0.05:
            bear.append(InvestmentInsight(
                headline="Thin profit margins leave less room for operating shocks",
                lens="operating_leverage",
                finding=f"Net profit margin is {cls._pct(metrics.profit_margin)}.",
                cause="Only a small portion of each sales dollar reaches net income after operating costs, interest and taxes.",
                durability="recurring", time_horizon="medium_term",
                investor_implication="Wage, merchandise, tariff or other cost pressure can materially affect earnings unless it is offset by pricing or productivity.",
                expectation_gap="A premium valuation is harder to defend if modest cost pressure compresses an already thin margin.",
                scenario_path="The risk recedes if pricing power and productivity expand margins without weakening customer demand.",
                what_to_watch=["Gross margin", "Operating expenses as a share of sales", "Pricing versus customer volume"],
                likelihood="medium", impact="medium", confidence="high",
            ))

        quarterly_fcf = next((x for x in metrics.quarterly_comparisons if x.metric == "quarterly_free_cash_flow"), None)
        if quarterly_fcf and quarterly_fcf.year_ago not in (None, 0) and quarterly_fcf.current < quarterly_fcf.year_ago * 0.95:
            decline = 1 - quarterly_fcf.current / quarterly_fcf.year_ago
            bear.append(InvestmentInsight(
                headline="Cash conversion is weaker than a year ago",
                lens="earnings_quality",
                finding=f"Quarterly free cash flow declined {decline * 100:.1f}% from the same quarter last year.",
                cause="The cash-flow statement shows that less operating cash remained after capital spending than in the comparable prior-year quarter.",
                durability="unresolved", time_horizon="near_term",
                investor_implication="Earnings growth is less valuable to shareholders if it does not translate into growing free cash flow.",
                expectation_gap="A premium share price requires accounting earnings to convert into durable and growing cash generation.",
                scenario_path="The concern fades if cash conversion recovers; it strengthens if working capital or investment needs continue absorbing a larger share of operating cash.",
                what_to_watch=["Free-cash-flow conversion", "Working-capital use", "Capital expenditure relative to operating cash flow"],
                likelihood="medium", impact="medium", confidence="high",
            ))

        capex = next((x for x in metrics.quarterly_comparisons if x.metric == "quarterly_capital_expenditure"), None)
        if capex and capex.year_ago not in (None, 0) and abs(capex.current) > abs(capex.year_ago) * 1.15:
            increase = abs(capex.current) / abs(capex.year_ago) - 1
            bear.append(InvestmentInsight(
                headline="Investment spending is rising faster than a year ago",
                lens="capital_allocation",
                finding=f"Quarterly capital expenditure increased {increase * 100:.1f}% from the same quarter last year.",
                cause="The cash-flow statement shows a larger outlay for property, equipment or other capital investment.",
                durability="unresolved", time_horizon="medium_term",
                investor_implication="Higher investment can create growth, but it reduces near-term free cash flow until the new capacity earns an adequate return.",
                expectation_gap="The market must ultimately see enough incremental sales and profit to justify the added spending.",
                scenario_path="The spending becomes constructive if returns and demand rise; it becomes a drag if expansion outpaces profitable demand.",
                what_to_watch=["Capital expenditure", "New capacity utilization", "Return on assets", "Free-cash-flow conversion"],
                likelihood="medium", impact="medium", confidence="high",
            ))

        if metrics.price is not None and metrics.analyst_target_median is not None and metrics.analyst_target_median < metrics.price:
            downside = metrics.analyst_target_median / metrics.price - 1
            bear.append(InvestmentInsight(
                headline="The median analyst target is below the current share price",
                lens="market_expectations",
                finding=f"The median analyst target is {cls._money(metrics.analyst_target_median)}, or {abs(downside) * 100:.1f}% below the current price.",
                cause="The shares trade above the middle of the published analyst target range.",
                durability="unresolved", time_horizon="near_term",
                investor_implication="Even analysts who follow the company may see limited near-term upside at the current price.",
                expectation_gap="Targets can lag new information, but the gap shows that current market expectations are ahead of the median published view.",
                scenario_path="The concern fades if analysts raise targets because earnings expectations improve, not merely because valuation multiples expand.",
                what_to_watch=["Median analyst price target", "Target changes after new business evidence", "Forward earnings revisions"],
                likelihood="medium", impact="medium", confidence="medium",
            ))

        return cls._rank_insights(bull), cls._rank_insights(bear)

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
        forward_support, forward_caution = self._forward_estimate_context(evidence)
        bull_insights, bear_insights = self._structured_insights(
            metrics, evidence, forward_support, forward_caution
        )

        bull_case = [item for item, _ in forward_support[:1]] + positives[:2]
        bull_case.extend(technical_support[:1])
        if len(bull_case) < 4:
            bull_case.extend(insider_support[: 4 - len(bull_case)])
        if len(bull_case) < 4 and evidence.estimate_revisions:
            bull_case.append("Analyst estimate/revision evidence is available for review in the evidence packet.")

        bear_case = [item for item, _ in forward_caution[:1]] + concerns[:2]
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
        citations: list[AnalysisCitation] = []
        if forward_support:
            citations.append(AnalysisCitation(section="bull_case", item_index=0, claim_ids=[forward_support[0][1]]))
        if forward_caution:
            citations.append(AnalysisCitation(section="bear_case", item_index=0, claim_ids=[forward_caution[0][1]]))

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
            tension: list[str] = []
            margin_comparison = next(
                (item for item in metrics.quarterly_comparisons if item.metric == "quarterly_operating_margin"),
                None,
            )
            if metrics.revenue_growth is not None and metrics.revenue_growth < 0 and metrics.earnings_growth is not None and metrics.earnings_growth > 0:
                tension.append("earnings are improving while revenue remains under pressure")
            if metrics.forward_pe is not None and metrics.forward_pe >= 30:
                tension.append(f"the {metrics.forward_pe:.1f}x forward earnings multiple requires meaningful execution")
            if margin_comparison and (margin_comparison.year_ago is not None and margin_comparison.current > margin_comparison.year_ago):
                tension.append("operating margins have improved but their durability still needs confirmation")
            central_tension = "; ".join(tension[:2]) or "the operating evidence and valuation do not yet point in the same direction"
            thesis = (
                f"{metrics.company_name or metrics.ticker} is a Watch because {central_tension}. "
                "The next decision turns on whether demand begins supporting the earnings recovery without requiring more valuation expansion."
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
                citations=citations,
                bull_insights=bull_insights,
                bear_insights=bear_insights,
            ),
            "deterministic-v1.3-ranked-lenses",
        )
