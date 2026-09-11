from __future__ import annotations

from collections.abc import Iterable

from .models import CategoryScores, MetricSnapshot


def _avg(values: Iterable[float | None], default: float = 50.0) -> float:
    clean = [float(v) for v in values if v is not None]
    return round(sum(clean) / len(clean), 1) if clean else default


def _higher(value: float | None, bands: list[tuple[float, float]]) -> float | None:
    if value is None:
        return None
    for index, (threshold, score) in enumerate(bands):
        if value >= threshold:
            if index == 0:
                return score
            upper_threshold, upper_score = bands[index - 1]
            position = (value - threshold) / (upper_threshold - threshold)
            return round(score + position * (upper_score - score), 1)
    return 10.0


def _lower(value: float | None, bands: list[tuple[float, float]]) -> float | None:
    if value is None or value < 0:
        return None
    for index, (threshold, score) in enumerate(bands):
        if value <= threshold:
            if index == 0:
                return score
            lower_threshold, lower_score = bands[index - 1]
            position = (value - lower_threshold) / (threshold - lower_threshold)
            return round(lower_score + position * (score - lower_score), 1)
    return 10.0


def _positive(value: float | None) -> float | None:
    if value is None:
        return None
    return 90.0 if value > 0 else 15.0


def _fcf_yield(m: MetricSnapshot) -> float | None:
    if m.free_cash_flow is None or not m.market_cap or m.market_cap <= 0:
        return None
    return m.free_cash_flow / m.market_cap


def score_metrics(m: MetricSnapshot) -> CategoryScores:
    fundamentals = _avg([
        _positive(m.free_cash_flow),
        _positive(m.operating_cash_flow),
        _higher(m.current_ratio, [(2.0, 95), (1.5, 85), (1.0, 65), (0.75, 40)]),
        _lower(m.debt_to_equity, [(25, 95), (50, 85), (100, 65), (200, 40)]),
        _higher(m.profit_margin, [(0.20, 95), (0.12, 85), (0.07, 70), (0.03, 55), (0.0, 35)]),
    ])
    valuation = _avg([
        _lower(m.trailing_pe, [(15, 95), (22, 82), (30, 68), (40, 50), (55, 30)]),
        _lower(m.forward_pe, [(15, 95), (22, 82), (30, 68), (40, 50), (55, 30)]),
        _lower(m.peg_ratio, [(1.0, 95), (1.5, 82), (2.0, 68), (3.0, 45)]),
        _lower(m.enterprise_to_ebitda, [(10, 95), (15, 82), (20, 68), (30, 45)]),
        _higher(_fcf_yield(m), [(0.08, 95), (0.06, 85), (0.04, 70), (0.02, 50), (0.0, 30)]),
    ])
    business_quality = _avg([
        _higher(m.return_on_equity, [(0.25, 95), (0.18, 85), (0.12, 70), (0.07, 55), (0.0, 35)]),
        _higher(m.return_on_assets, [(0.12, 95), (0.08, 85), (0.05, 70), (0.02, 50), (0.0, 35)]),
        _higher(m.gross_margin, [(0.60, 95), (0.45, 85), (0.30, 70), (0.20, 55), (0.0, 35)]),
        _higher(m.operating_margin, [(0.25, 95), (0.18, 85), (0.12, 70), (0.05, 50), (0.0, 35)]),
        _positive(m.free_cash_flow),
    ])
    growth = _avg([
        _higher(m.revenue_growth, [(0.25, 95), (0.15, 85), (0.08, 70), (0.03, 55), (0.0, 40)]),
        _higher(m.earnings_growth, [(0.25, 95), (0.15, 85), (0.08, 70), (0.03, 55), (0.0, 40)]),
    ])
    risk_resilience = _avg([
        _lower(m.beta, [(0.8, 90), (1.0, 80), (1.2, 70), (1.5, 55), (2.0, 35)]),
        _lower(m.debt_to_equity, [(25, 95), (50, 85), (100, 65), (200, 40)]),
        _higher(m.current_ratio, [(2.0, 95), (1.5, 85), (1.0, 65), (0.75, 40)]),
        _positive(m.free_cash_flow),
    ])
    market_factors: list[float | None] = []
    if m.price and m.two_hundred_day_average:
        market_factors.append(_higher(m.price / m.two_hundred_day_average, [(1.15, 90), (1.05, 80), (0.95, 65), (0.85, 45)]))
    if m.price and m.fifty_two_week_high:
        market_factors.append(_lower(1 - (m.price / m.fifty_two_week_high), [(0.05, 85), (0.15, 75), (0.25, 60), (0.40, 40)]))
    market_context = _avg(market_factors)
    overall = round(
        fundamentals * 0.30 + valuation * 0.25 + business_quality * 0.20
        + growth * 0.10 + risk_resilience * 0.10 + market_context * 0.05,
        1,
    )
    return CategoryScores(
        fundamentals=fundamentals,
        valuation=valuation,
        business_quality=business_quality,
        growth=growth,
        risk_resilience=risk_resilience,
        market_context=market_context,
        overall=overall,
    )
