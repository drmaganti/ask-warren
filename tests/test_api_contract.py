from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models import AnalyzeRequest


def test_screen_requires_tickers():
    with pytest.raises(ValidationError):
        AnalyzeRequest(mode="screen")


def test_screen_rejects_single_ticker():
    with pytest.raises(ValidationError):
        AnalyzeRequest(mode="screen", ticker="AAPL", tickers=["MSFT"])


def test_deep_requires_ticker():
    with pytest.raises(ValidationError):
        AnalyzeRequest(mode="deep")


def test_deep_rejects_ticker_list():
    with pytest.raises(ValidationError):
        AnalyzeRequest(mode="deep", ticker="AAPL", tickers=["MSFT"])


def test_valid_mode_shapes():
    screen = AnalyzeRequest(mode="screen", tickers=["AAPL", "MSFT"])
    deep = AnalyzeRequest(mode="deep", ticker="AAPL")

    assert screen.mode == "screen"
    assert deep.mode == "deep"


def test_analyze_page_is_served():
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "Ask Warren about a stock." in response.text
    assert "U.S. equities V1" in response.text
    assert "Run Analysis" in response.text
    assert "Sources and Data Quality" in response.text
    assert "Filing Insights and Recent Research" in response.text
    assert "Supporting Evidence" in response.text
    assert "SEC-Reported Fundamentals" in response.text
    assert "Technical Snapshot" in response.text
    assert "Insider Activity" in response.text
    assert "Methodology" in response.text
    assert "Roadmap" in response.text
    assert 'aria-live="polite"' in response.text
    assert "Missing Information" in response.text
    assert "history.replaceState" in response.text
    assert "Sensitivity" in response.text
    assert "What caused it" in response.text
    assert "What to watch" in response.text
    assert "Next decision point" in response.text
    assert "View detailed analysis" in response.text
    assert "firstSentences" in response.text
    assert "What Matters Next" in response.text
    assert "Evidence confidence" in response.text
    assert "Analysis updated" in response.text
    assert "Watchlist" not in response.text
    assert "0.69936" not in response.text


def test_methodology_page_is_served():
    client = TestClient(app)
    response = client.get("/methodology")

    assert response.status_code == 200
    assert "Understand the reasoning, not just the rating." in response.text
    assert "Attractive" in response.text
    assert "Watch" in response.text
    assert "Avoid" in response.text
    assert "DCF" in response.text


def test_roadmap_page_is_served():
    client = TestClient(app)
    response = client.get("/roadmap")

    assert response.status_code == 200
    assert "Build trust first. Add breadth second." in response.text
    assert "Transparent DCF" in response.text
    assert "Watchlist" in response.text
    assert "Portfolio research" in response.text
