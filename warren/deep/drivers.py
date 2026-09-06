"""Arithmetic diagnostics; explanations of causes still require primary evidence."""

from ..models import MetricSnapshot


def earnings_bridge(metrics: MetricSnapshot) -> dict:
    rows = {row.metric: row for row in metrics.quarterly_comparisons}
    names = ("operating_income", "pretax_income", "tax_provision", "net_income")
    selected = [rows.get("quarterly_" + name) for name in names]
    if any(row is None or row.year_ago is None for row in selected):
        return {"status": "unavailable", "reason": "Comparable operating income, pretax income, tax and net income are required."}
    if len({(row.current_period, row.year_ago_period) for row in selected}) != 1:
        return {"status": "unavailable", "reason": "Statement periods do not align."}
    operating, pretax, tax, net = selected
    op_change = operating.current - operating.year_ago
    pretax_change = pretax.current - pretax.year_ago
    tax_effect = tax.year_ago - tax.current
    net_change = net.current - net.year_ago
    return {
        "status": "available", "source": "Yahoo Finance quarterly statements; verify against company filing",
        "current_period": str(net.current_period), "year_ago_period": str(net.year_ago_period),
        "operating_income_change": op_change,
        "below_operating_income_change": pretax_change - op_change,
        "tax_expense_effect": tax_effect,
        "net_income_change": net_change,
        "unreconciled_change": net_change - pretax_change - tax_effect,
        "interpretation_rule": "Below-operating changes include interest and other gains/losses; do not label them efficiency. Residuals require attribution/minority-interest checks. Do not add overlapping line items."
    }
