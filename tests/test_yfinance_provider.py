from __future__ import annotations

import pandas as pd

from warren.providers.yfinance import YFinanceMarketDataProvider


def test_quarterly_comparisons_use_prior_and_same_quarter_last_year():
    periods = pd.to_datetime(["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30"])
    income = pd.DataFrame(
        {
            period: values
            for period, values in zip(
                periods,
                zip(
                    [110, 100, 95, 90, 80],
                    [22, 18, 17, 16, 12],
                    [15, 12, 11, 10, 8],
                    [55, 48, 45, 42, 38],
                ),
            )
        },
        index=["Total Revenue", "Operating Income", "Net Income", "Gross Profit"],
    )
    cashflow = pd.DataFrame(
        {period: values for period, values in zip(periods, zip([20, 18, 17, 16, 14], [12, 10, 9, 8, 7]))},
        index=["Operating Cash Flow", "Free Cash Flow"],
    )

    comparisons = YFinanceMarketDataProvider._quarterly_comparisons(income, cashflow)
    by_metric = {item.metric: item for item in comparisons}

    revenue = by_metric["quarterly_revenue"]
    assert revenue.current == 110
    assert revenue.previous_quarter == 100
    assert revenue.year_ago == 80
    margin = by_metric["quarterly_operating_margin"]
    assert margin.current == 0.2
    assert margin.year_ago == 0.15
