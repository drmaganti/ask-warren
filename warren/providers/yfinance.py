from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

import yfinance as yf

from ..models import MetricComparison, MetricSnapshot


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


class YFinanceMarketDataProvider:
    """Free development provider. Replaceable through the MarketDataProvider protocol."""

    @staticmethod
    def _quarterly_comparisons(income: Any, cashflow: Any) -> list[MetricComparison]:
        def periods(frame: Any) -> list[Any]:
            if frame is None or getattr(frame, "empty", True):
                return []
            return sorted(list(frame.columns), reverse=True)

        def values(frame: Any, row: str) -> dict[Any, float]:
            if frame is None or getattr(frame, "empty", True) or row not in frame.index:
                return {}
            return {
                column: number
                for column in periods(frame)
                if (number := _number(frame.at[row, column])) is not None
            }

        def ratio(numerator: dict[Any, float], denominator: dict[Any, float]) -> dict[Any, float]:
            return {
                period: numerator[period] / denominator[period]
                for period in numerator.keys() & denominator.keys()
                if denominator[period]
            }

        revenue = values(income, "Total Revenue")
        series = [
            ("quarterly_revenue", "Quarterly revenue", "money", revenue),
            ("quarterly_net_income", "Quarterly net income", "money", values(income, "Net Income")),
            ("quarterly_operating_margin", "Quarterly operating margin", "percent", ratio(values(income, "Operating Income"), revenue)),
            ("quarterly_gross_margin", "Quarterly gross margin", "percent", ratio(values(income, "Gross Profit"), revenue)),
            ("quarterly_operating_cash_flow", "Quarterly operating cash flow", "money", values(cashflow, "Operating Cash Flow")),
            ("quarterly_free_cash_flow", "Quarterly free cash flow", "money", values(cashflow, "Free Cash Flow")),
        ]
        comparisons: list[MetricComparison] = []
        for metric, label, unit, observations in series:
            ordered = sorted(observations, reverse=True)
            if not ordered:
                continue
            current_period = ordered[0]
            previous_period = ordered[1] if len(ordered) > 1 else None
            year_ago_period = ordered[4] if len(ordered) > 4 else None
            comparisons.append(MetricComparison(
                metric=metric,
                label=label,
                unit=unit,
                current=observations[current_period],
                current_period=current_period.date() if hasattr(current_period, "date") else current_period,
                previous_quarter=observations.get(previous_period),
                previous_period=previous_period.date() if hasattr(previous_period, "date") else previous_period,
                year_ago=observations.get(year_ago_period),
                year_ago_period=year_ago_period.date() if hasattr(year_ago_period, "date") else year_ago_period,
            ))
        return comparisons

    def fetch_metrics(self, ticker: str) -> MetricSnapshot:
        symbol = ticker.strip().upper()
        if not symbol:
            raise ValueError("ticker is required")

        stock = yf.Ticker(symbol)
        info = stock.info or {}
        price = _number(info.get("currentPrice") or info.get("regularMarketPrice"))
        if price is None:
            try:
                price = _number(stock.fast_info.last_price)
            except Exception:
                price = None

        historical_fcf: list[float] = []
        quarterly_comparisons: list[MetricComparison] = []
        try:
            cashflow = stock.cashflow
            if cashflow is not None and not cashflow.empty and "Free Cash Flow" in cashflow.index:
                historical_fcf = [
                    number
                    for value in cashflow.loc["Free Cash Flow"].tolist()
                    if (number := _number(value)) is not None
                ]
                historical_fcf.reverse()
        except Exception:
            historical_fcf = []
        try:
            quarterly_comparisons = self._quarterly_comparisons(
                stock.quarterly_income_stmt,
                stock.quarterly_cashflow,
            )
        except Exception:
            quarterly_comparisons = []

        return MetricSnapshot(
            ticker=symbol,
            company_name=info.get("longName") or info.get("shortName"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            currency=info.get("currency"),
            price=price,
            market_cap=_number(info.get("marketCap")),
            total_revenue=_number(info.get("totalRevenue")),
            trailing_pe=_number(info.get("trailingPE")),
            forward_pe=_number(info.get("forwardPE")),
            peg_ratio=_number(info.get("pegRatio")),
            price_to_book=_number(info.get("priceToBook")),
            enterprise_to_ebitda=_number(info.get("enterpriseToEbitda")),
            free_cash_flow=_number(info.get("freeCashflow")),
            operating_cash_flow=_number(info.get("operatingCashflow")),
            total_cash=_number(info.get("totalCash")),
            total_debt=_number(info.get("totalDebt")),
            shares_outstanding=_number(info.get("sharesOutstanding")),
            fetched_at=datetime.now(timezone.utc),
            historical_free_cash_flow=historical_fcf,
            quarterly_comparisons=quarterly_comparisons,
            revenue_growth=_number(info.get("revenueGrowth")),
            earnings_growth=_number(info.get("earningsGrowth")),
            gross_margin=_number(info.get("grossMargins")),
            operating_margin=_number(info.get("operatingMargins")),
            profit_margin=_number(info.get("profitMargins")),
            return_on_equity=_number(info.get("returnOnEquity")),
            return_on_assets=_number(info.get("returnOnAssets")),
            debt_to_equity=_number(info.get("debtToEquity")),
            current_ratio=_number(info.get("currentRatio")),
            beta=_number(info.get("beta")),
            fifty_two_week_high=_number(info.get("fiftyTwoWeekHigh")),
            fifty_two_week_low=_number(info.get("fiftyTwoWeekLow")),
            fifty_day_average=_number(info.get("fiftyDayAverage")),
            two_hundred_day_average=_number(info.get("twoHundredDayAverage")),
        )
