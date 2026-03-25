from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base
import uuid
from datetime import datetime


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(String, unique=True, index=True)
    symbol = Column(String, index=True)
    strategy = Column(String)
    parameters = Column(JSON)
    initial_capital = Column(Float)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    trades = relationship(
        "Trade", back_populates="backtest_run", cascade="all, delete-orphan"
    )
    performance = relationship(
        "PerformanceResult",
        uselist=False,
        back_populates="backtest_run",
        cascade="all, delete-orphan",
    )


class Trade(Base):
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backtest_id = Column(UUID(as_uuid=True), ForeignKey("backtest_runs.id"))
    timestamp = Column(DateTime)
    symbol = Column(String)
    direction = Column(String)
    quantity = Column(Integer)
    price = Column(Float)
    commission = Column(Float, default=0.0)

    backtest_run = relationship("BacktestRun", back_populates="trades")


class PerformanceResult(Base):
    __tablename__ = "performance_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backtest_id = Column(
        UUID(as_uuid=True), ForeignKey("backtest_runs.id"), unique=True
    )
    total_return = Column(Float)  # as percentage
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float)  # as percentage
    final_equity = Column(Float)
    equity_curve = Column(JSON, nullable=True)  # [{time, equity, cash}, ...]
    fills = Column(JSON, nullable=True)          # [{time, direction}, ...]

    backtest_run = relationship("BacktestRun", back_populates="performance")
