"""
FastAPI routes for the backtesting API.
Provides endpoints for running backtests, checking status, and retrieving results.
"""

import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, BackgroundTasks

from src.api.schemas import (
    BacktestRequest,
    BacktestResult,
    JobStatusResponse,
    StrategyInfo,
    StrategyType,
    PerformanceMetrics,
    TradeRecord,
    JobStatus,
)
from src.api.jobs import job_manager, BacktestJob
from src.db.database import SessionLocal
from src.db import models

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# Backtest Execution Logic
# ============================================================


def execute_backtest(job: BacktestJob) -> dict:
    """
    Execute a backtest job using the existing engine.

    This function runs in a background thread and uses the core
    backtesting components to run the simulation.
    """
    from src.data_fetcher import DataFetcher
    from src.data_handler import DataHandler
    from src.strategy import MovingAverageCrossStrategy
    from src.portfolio import Portfolio
    from src.engine import BacktestEngine
    from src.performance import (
        create_equity_curve,
        calculate_drawdown,
        calculate_sharpe_ratio,
        calculate_total_return,
    )
    from src.events import FillEvent

    logger.info(f"Starting backtest execution for job {job.job_id}")

    # 1. Fetch data
    fetcher = DataFetcher()
    data_path = fetcher.get_data(job.symbol, job.start_date, job.end_date)

    # 2. Setup components
    data_handler = DataHandler(data_path, job.symbol)

    # 3. Create strategy based on type
    if job.strategy == StrategyType.MA_CROSSOVER.value:
        short_window = job.parameters.get("short_window", 10)
        long_window = job.parameters.get("long_window", 50)
        strategy = MovingAverageCrossStrategy(
            short_window=short_window, long_window=long_window
        )
    else:
        raise ValueError(f"Unknown strategy: {job.strategy}")

    portfolio = Portfolio(initial_capital=job.initial_capital)

    # 4. Run backtest
    engine = BacktestEngine(
        data_handler=data_handler, strategy=strategy, portfolio=portfolio
    )
    engine.run()

    # 5. Calculate metrics using individual functions
    equity_curve = create_equity_curve(portfolio.history)

    metrics = {}
    if not equity_curve.empty:
        metrics["total_return"] = (
            calculate_total_return(equity_curve) * 100
        )  # as percentage
        metrics["sharpe_ratio"] = calculate_sharpe_ratio(equity_curve)
        drawdown = calculate_drawdown(equity_curve)
        metrics["max_drawdown"] = (
            float(drawdown.min()) * 100 if len(drawdown) > 0 else 0.0
        )
    else:
        metrics["total_return"] = 0.0
        metrics["sharpe_ratio"] = 0.0
        metrics["max_drawdown"] = 0.0

    # 6. Extract trades from processed events
    trades = []
    for event in engine.processed_events:
        if isinstance(event, FillEvent):
            trades.append(
                {
                    "timestamp": (
                        event.time.isoformat()
                        if hasattr(event.time, "isoformat")
                        else str(event.time)
                    ),
                    "symbol": event.symbol,
                    "direction": event.direction,
                    "quantity": event.quantity,
                    "price": event.price,
                    "commission": getattr(event, "commission", 0.0),
                }
            )

    save_results_to_db(
        job,
        metrics,
        trades,
        portfolio.history[-1]["equity"] if portfolio.history else job.initial_capital,
    )

    return {
        "metrics": metrics,
        "trades": trades,
        "final_equity": (
            portfolio.history[-1]["equity"]
            if portfolio.history
            else job.initial_capital
        ),
    }


def save_results_to_db(
    job: BacktestJob, metrics: dict, trades_data: list, final_equity: float
):
    """
    Helper to persist backtest results to PostgreSQL.
    """
    db = SessionLocal()
    try:
        # 1. Update BacktestRun record
        db_run = (
            db.query(models.BacktestRun)
            .filter(models.BacktestRun.job_id == job.job_id)
            .first()
        )
        if db_run:
            db_run.status = "completed"
            db_run.completed_at = datetime.utcnow()

            # 2. Save PerformanceResult
            perf = models.PerformanceResult(
                backtest_id=db_run.id,
                total_return=float(metrics.get("total_return", 0.0)),
                sharpe_ratio=(
                    float(metrics.get("sharpe_ratio"))
                    if metrics.get("sharpe_ratio") is not None
                    else None
                ),
                max_drawdown=float(metrics.get("max_drawdown", 0.0)),
                final_equity=float(final_equity),
            )
            db.add(perf)

            # 3. Save Trades
            for t in trades_data:
                db_trade = models.Trade(
                    backtest_id=db_run.id,
                    timestamp=datetime.fromisoformat(t["timestamp"]),
                    symbol=t["symbol"],
                    direction=t["direction"],
                    quantity=int(t["quantity"]),
                    price=float(t["price"]),
                    commission=float(t.get("commission", 0.0)),
                )
                db.add(db_trade)

            db.commit()
            logger.info(f"Results for job {job.job_id} persisted to database")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save results to DB for job {job.job_id}: {e}")
    finally:
        db.close()


# ============================================================
# API Endpoints
# ============================================================


@router.post("/backtest/run", response_model=JobStatusResponse, tags=["Backtest"])
async def run_backtest(request: BacktestRequest, background_tasks: BackgroundTasks):
    """
    Start a new backtest job.

    The backtest runs asynchronously in the background.
    Use the returned job_id to check status and retrieve results.
    """
    # Create job in memory
    job = job_manager.create_job(
        symbol=request.symbol,
        start_date=request.start_date,
        end_date=request.end_date,
        strategy=request.strategy.value,
        parameters=request.parameters,
        initial_capital=request.initial_capital,
    )

    # Persist initial record to DB
    db = SessionLocal()
    try:
        db_run = models.BacktestRun(
            job_id=job.job_id,
            symbol=job.symbol,
            strategy=job.strategy,
            parameters=job.parameters,
            initial_capital=job.initial_capital,
            status="running",
        )
        db.add(db_run)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to create DB record for job {job.job_id}: {e}")
    finally:
        db.close()

    # Submit for background execution
    job_manager.submit_job(job.job_id, execute_backtest)

    return JobStatusResponse(
        job_id=job.job_id, status=JobStatus.RUNNING, progress="Backtest started"
    )


@router.get("/backtest/{job_id}", response_model=JobStatusResponse, tags=["Backtest"])
async def get_backtest_status(job_id: str):
    """
    Get the current status of a backtest job.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    progress = None
    if job.status == JobStatus.RUNNING:
        progress = "Processing..."
    elif job.status == JobStatus.COMPLETED:
        progress = "Completed successfully"
    elif job.status == JobStatus.FAILED:
        progress = f"Failed: {job.error}"

    return JobStatusResponse(job_id=job.job_id, status=job.status, progress=progress)


@router.get("/results/{job_id}", response_model=BacktestResult, tags=["Backtest"])
async def get_backtest_results(job_id: str):
    """
    Get the full results of a completed backtest.

    Returns detailed metrics and trade history.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status == JobStatus.PENDING:
        raise HTTPException(status_code=400, detail="Job has not started yet")

    if job.status == JobStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Job is still running")

    # Build response
    metrics = None
    trades = None

    if job.result:
        result_metrics = job.result.get("metrics", {})
        metrics = PerformanceMetrics(
            total_return=result_metrics.get("total_return", 0.0),
            sharpe_ratio=result_metrics.get("sharpe_ratio"),
            max_drawdown=result_metrics.get("max_drawdown", 0.0),
            win_rate=result_metrics.get("win_rate"),
            total_trades=len(job.result.get("trades", [])),
            final_equity=job.result.get("final_equity", job.initial_capital),
        )

        trades = [
            TradeRecord(
                timestamp=(
                    datetime.fromisoformat(t["timestamp"])
                    if isinstance(t["timestamp"], str)
                    else t["timestamp"]
                ),
                symbol=t["symbol"],
                direction=t["direction"],
                quantity=t["quantity"],
                price=t["price"],
                commission=t.get("commission", 0.0),
            )
            for t in job.result.get("trades", [])
        ]

    return BacktestResult(
        job_id=job.job_id,
        status=job.status,
        symbol=job.symbol,
        strategy=job.strategy,
        parameters=job.parameters,
        metrics=metrics,
        trades=trades,
        error=job.error,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@router.get("/strategies", response_model=List[StrategyInfo], tags=["Strategies"])
async def list_strategies():
    """
    List all available trading strategies.
    """
    return [
        StrategyInfo(
            name="ma_crossover",
            description="Moving Average Crossover Strategy. Generates BUY signals when short MA crosses above long MA, and EXIT signals when short MA crosses below.",
            parameters={
                "short_window": "Number of periods for the short moving average (default: 10)",
                "long_window": "Number of periods for the long moving average (default: 50)",
            },
        )
    ]


@router.get("/jobs", response_model=List[JobStatusResponse], tags=["Jobs"])
async def list_jobs():
    """
    List all backtest jobs (most recent first).
    """
    jobs = job_manager.get_all_jobs()
    return [
        JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            progress=f"{job.symbol} - {job.strategy}",
        )
        for job in jobs
    ]


@router.get("/db/results/{job_id}", tags=["Database"])
async def get_db_results(job_id: str):
    """
    Retrieve results directly from PostgreSQL.
    Demonstrates that data is persisted in the database.
    """
    db = SessionLocal()
    try:
        db_run = (
            db.query(models.BacktestRun)
            .filter(models.BacktestRun.job_id == job_id)
            .first()
        )
        if not db_run:
            raise HTTPException(status_code=404, detail="Job not found in database")

        if db_run.status != "completed":
            return {
                "job_id": job_id,
                "status": db_run.status,
                "message": "Result not ready yet",
            }

        return {
            "job_id": db_run.job_id,
            "symbol": db_run.symbol,
            "status": db_run.status,
            "metrics": (
                {
                    "total_return": db_run.performance.total_return,
                    "sharpe_ratio": db_run.performance.sharpe_ratio,
                    "max_drawdown": db_run.performance.max_drawdown,
                    "final_equity": db_run.performance.final_equity,
                }
                if db_run.performance
                else None
            ),
            "trade_count": len(db_run.trades),
            "created_at": db_run.created_at,
            "completed_at": db_run.completed_at,
        }
    finally:
        db.close()
