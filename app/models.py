from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from warren.models import CategoryScores, DcfResult, DeepAnalysis, EvidenceBundle, MetricSnapshot, ScreenResult, SavedThesis


class AnalyzeRequest(BaseModel):
    mode: Literal["screen", "deep"]
    ticker: str | None = Field(default=None, min_length=1, max_length=20)
    tickers: list[str] | None = Field(default=None, min_length=1, max_length=1000)
    top_n: int = Field(default=25, ge=1, le=100)
    min_score: float = Field(default=0, ge=0, le=100)
    saved_thesis: SavedThesis | None = None

    @model_validator(mode="after")
    def validate_mode_inputs(self):
        if self.mode == "deep":
            if not self.ticker:
                raise ValueError("ticker is required when mode='deep'")
            if self.tickers:
                raise ValueError("tickers is only valid when mode='screen'")
        else:
            if self.saved_thesis:
                raise ValueError("saved_thesis is only valid when mode='deep'")
            if not self.tickers:
                raise ValueError("tickers is required when mode='screen'")
            if self.ticker:
                raise ValueError("ticker is only valid when mode='deep'")
        return self


class AnalyzeResponse(BaseModel):
    mode: Literal["screen", "deep"]
    ticker: str | None = None
    screened_count: int | None = None
    failed_tickers: list[str] = Field(default_factory=list)
    results: list[ScreenResult] | None = None
    metrics: MetricSnapshot | None = None
    scores: CategoryScores | None = None
    dcf: DcfResult | None = None
    evidence: EvidenceBundle | None = None
    missing_data: list[str] = Field(default_factory=list)
    analysis: DeepAnalysis | None = None
    model: str | None = None
    disclaimer: str = "For research purposes only. Not financial advice."
