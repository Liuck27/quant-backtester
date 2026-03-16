"""
Pydantic schemas for API request/response validation.
Provides type-safe data structures for backtest configuration and results.
"""

from datetime import datetime, date
from typing import Optional, Dict, List, Any
from enum import Enum
from pydantic import BaseModel, Field, model_validator


class JobStatus(str, Enum):
    """Status of a backtest job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StrategyType(str, Enum):
    """Available trading strategies."""

    MA_CROSSOVER = "ma_crossover"


# ============================================================
# Request Schemas
# ============================================================


class BacktestRequest(BaseModel):
    """Request schema for starting a new backtest."""

    symbol: str = Field(..., description="Ticker symbol (e.g., 'AAPL')")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    strategy: StrategyType = Field(..., description="Strategy to use")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Strategy-specific parameters"
    )
    initial_capital: float = Field(default=100000.0, gt=0, description="Starting capital")

    @model_validator(mode="after")
    def validate_dates(self) -> "BacktestRequest":
        try:
            start = date.fromisoformat(self.start_date)
            end = date.fromisoformat(self.end_date)
        except ValueError as e:
            raise ValueError(f"Invalid date format. Use YYYY-MM-DD. Detail: {e}")
        if start >= end:
            raise ValueError(
                f"start_date ({self.start_date}) must be before end_date ({self.end_date})"
            )
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "symbol": "AAPL",
                    "start_date": "2023-01-01",
                    "end_date": "2024-01-01",
                    "strategy": "ma_crossover",
                    "parameters": {"short_window": 10, "long_window": 50},
                    "initial_capital": 100000.0,
                }
            ]
        }
    }


# ============================================================
# Response Schemas
# ============================================================


class TradeRecord(BaseModel):
    """A single trade execution record."""

    timestamp: datetime
    symbol: str
    direction: str
    quantity: int
    price: float
    commission: float = 0.0


class PerformanceMetrics(BaseModel):
    """Performance metrics for a completed backtest."""

    total_return: float = Field(..., description="Total return percentage")
    sharpe_ratio: Optional[float] = Field(None, description="Risk-adjusted return")
    max_drawdown: float = Field(..., description="Maximum drawdown percentage")
    win_rate: Optional[float] = Field(None, description="Percentage of winning trades")
    total_trades: int = Field(..., description="Total number of trades executed")
    final_equity: float = Field(..., description="Final portfolio value")


class BacktestResult(BaseModel):
    """Complete backtest result including metrics and trades."""

    job_id: str
    status: JobStatus
    symbol: str
    strategy: str
    parameters: Dict[str, Any]
    metrics: Optional[PerformanceMetrics] = None
    trades: Optional[List[TradeRecord]] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class JobStatusResponse(BaseModel):
    """Lightweight response for job status checks."""

    job_id: str
    status: JobStatus
    progress: Optional[str] = None


class StrategyInfo(BaseModel):
    """Information about an available strategy."""

    name: str
    description: str
    parameters: Dict[str, str]  # param_name -> description


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    timestamp: datetime
