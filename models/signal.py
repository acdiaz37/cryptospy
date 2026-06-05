from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


class ExpectedMove(BaseModel):
    min: float
    max: float


class Signal(BaseModel):
    rank: int
    pair: str
    asset_name: str
    direction: Literal["LONG", "SHORT"]
    bullish_score: int = Field(..., ge=0, le=100)
    bearish_score: int = Field(..., ge=0, le=100)
    confidence_score: int = Field(..., ge=0, le=100)
    expected_move_pct: ExpectedMove
    expected_edge: float
    primary_catalyst: str
    narrative: str
    supporting_evidence: list[str]
    key_accounts_involved: list[str]
    institutional_or_whale_signal: str
    risk_factors: list[str]
    reason_for_selection: str


class SelectionSummary(BaseModel):
    assets_screened: int
    signals_selected: int
    long_signals: int
    short_signals: int
    selection_method: str


class MarketOverview(BaseModel):
    overall_sentiment: str
    risk_level: str


class SignalResponse(BaseModel):
    timestamp_utc: str
    analysis_window_hours: int
    market_overview: MarketOverview
    signals: list[Signal]
    selection_summary: SelectionSummary


class SignalRecord(BaseModel):
    rank: int = 0
    signal_id: str
    timestamp_utc: str
    analysis_window_hours: int
    pair: str
    asset_name: str
    direction: Literal["LONG", "SHORT"]
    entry_price: float | None = None
    expected_min_pct: float
    expected_max_pct: float
    target_price_min: float | None = None
    target_price_max: float | None = None
    confidence_score: int
    bullish_score: int
    bearish_score: int
    expected_edge: float
    primary_catalyst: str
    narrative: str
    status: Literal["PENDING", "HIT_MIN", "HIT_MAX", "PARTIAL", "MISS", "STALE"] = "PENDING"
    exit_price: float | None = None
    actual_move_pct: float | None = None
    accuracy: Literal["CORRECT", "PARTIAL", "INCORRECT", ""] | None = ""
    check_timestamp_utc: str | None = ""
    notes: str | None = ""
