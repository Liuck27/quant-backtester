"""
FastAPI routes for the backtesting API.
Provides endpoints for running backtests, checking status, and retrieving results.
"""

import asyncio
import json
import logging
import queue
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Header
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from src.api.schemas import (
    BacktestRequest,
    BacktestResult,
    JobStatusResponse,
    JobSummary,
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
    logger.info(f"Starting backtest execution for job {job.job_id}")

    def progress_callback(event_data: dict):
        job.event_queue.put(event_data)
        if event_data.get("type") == "equity":
            job.partial_equity_curve.append(event_data)
        elif event_data.get("type") == "fill":
            job.partial_fills.append(event_data)

    try:
        return _run_backtest(job, progress_callback)
    except Exception as e:
        job.event_queue.put({"type": "error", "message": str(e)})
        raise


def _run_backtest(job: BacktestJob, progress_callback) -> dict:
    from src.data_fetcher import DataFetcher
    from src.data_handler import DataHandler
    from src.strategy import MovingAverageCrossStrategy
    from src.ml_strategy import MLSignalStrategy
    from src.portfolio import Portfolio
    from src.engine import BacktestEngine
    from src.performance import (
        create_equity_curve,
        calculate_drawdown,
        calculate_sharpe_ratio,
        calculate_total_return,
        calculate_win_rate,
    )
    from src.events import FillEvent

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
    elif job.strategy == StrategyType.ML_SIGNAL.value:
        strategy = MLSignalStrategy(
            model_type=job.parameters.get("model_type", "random_forest"),
            lookback_window=job.parameters.get("lookback_window", 252),
            retrain_every=job.parameters.get("retrain_every", 20),
            long_threshold=job.parameters.get("long_threshold", 0.6),
            exit_threshold=job.parameters.get("exit_threshold", 0.4),
        )
    else:
        raise ValueError(f"Unknown strategy: {job.strategy}")

    portfolio = Portfolio(
        initial_capital=job.initial_capital,
        commission_rate=job.commission_rate,
        risk_per_trade=job.risk_per_trade,
    )

    # 4. Run backtest
    engine = BacktestEngine(
        data_handler=data_handler,
        strategy=strategy,
        portfolio=portfolio,
        progress_callback=progress_callback,
        slippage_rate=job.slippage_rate,
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

    metrics["win_rate"] = calculate_win_rate(trades)

    final_equity = portfolio.history[-1]["equity"] if portfolio.history else job.initial_capital

    equity_curve_data = [
        {
            "time": h["datetime"].isoformat() if hasattr(h["datetime"], "isoformat") else str(h["datetime"]),
            "equity": h["equity"],
            "cash": h["cash"],
            "price": h.get("price"),
        }
        for h in portfolio.history
    ]
    fills_data = [{"time": t["timestamp"], "direction": t["direction"]} for t in trades]

    save_results_to_db(job, metrics, trades, final_equity, equity_curve_data, fills_data)

    progress_callback({"type": "done", "metrics": metrics, "final_equity": final_equity})

    return {
        "metrics": metrics,
        "trades": trades,
        "final_equity": final_equity,
        "equity_curve": equity_curve_data,
        "fills": fills_data,
    }


def save_results_to_db(
    job: BacktestJob, metrics: dict, trades_data: list, final_equity: float,
    equity_curve_data: list = None, fills_data: list = None,
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
                equity_curve=equity_curve_data,
                fills=fills_data,
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
async def run_backtest(
    request: BacktestRequest,
    background_tasks: BackgroundTasks,
    x_session_id: Optional[str] = Header(default=None),
):
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
        commission_rate=request.commission_rate,
        slippage_rate=request.slippage_rate,
        risk_per_trade=request.risk_per_trade,
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
            session_id=x_session_id,
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

    equity_curve = job.result.get("equity_curve") if job.result else None
    fills = job.result.get("fills") if job.result else None

    return BacktestResult(
        job_id=job.job_id,
        status=job.status,
        symbol=job.symbol,
        strategy=job.strategy,
        parameters=job.parameters,
        initial_capital=job.initial_capital,
        metrics=metrics,
        trades=trades,
        equity_curve=equity_curve,
        fills=fills,
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
        ),
        StrategyInfo(
            name="ml_signal",
            description="Machine Learning Signal Strategy. Trains a classifier on historical price features to predict next-bar direction. Generates LONG signals when predicted up-probability exceeds the long threshold, and EXIT signals when it falls below the exit threshold.",
            parameters={
                "model_type": "Classifier to use: 'random_forest' (default), 'gradient_boosting', or 'logistic'",
                "lookback_window": "Number of past bars used for training (default: 252, ~1 trading year)",
                "retrain_every": "Retrain the model every N bars (default: 20)",
                "long_threshold": "Predicted up-probability above which a LONG signal fires (default: 0.6)",
                "exit_threshold": "Predicted up-probability below which an EXIT signal fires (default: 0.4)",
            },
        ),
    ]


@router.get("/jobs", tags=["Jobs"])
async def list_jobs(x_session_id: Optional[str] = Header(default=None)):
    """
    List all backtest and research jobs from the database (most recent first).
    Each entry includes a job_type field: "backtest" or "research".
    When X-Session-ID header is present, only jobs for that session are returned.
    """
    db = SessionLocal()
    try:
        backtest_query = db.query(models.BacktestRun)
        if x_session_id:
            backtest_query = backtest_query.filter(models.BacktestRun.session_id == x_session_id)
        backtest_rows = backtest_query.order_by(models.BacktestRun.created_at.desc()).all()

        research_query = db.query(models.ResearchRun)
        if x_session_id:
            research_query = research_query.filter(models.ResearchRun.session_id == x_session_id)
        research_rows = research_query.order_by(models.ResearchRun.created_at.desc()).all()

        jobs = []

        for r in backtest_rows:
            jobs.append({
                "job_id": r.job_id,
                "status": r.status,
                "symbol": r.symbol,
                "strategy": r.strategy,
                "created_at": r.created_at,
                "completed_at": r.completed_at,
                "total_return": r.performance.total_return if r.performance else None,
                "job_type": "backtest",
            })

        for r in research_rows:
            combo_count = sum(
                1
                for sw in (r.short_windows or [])
                for lw in (r.long_windows or [])
                if sw < lw
            )
            jobs.append({
                "job_id": r.job_id,
                "status": r.status,
                "symbol": r.symbol,
                "strategy": f"Param Sweep ({combo_count} combos)",
                "created_at": r.created_at,
                "completed_at": r.completed_at,
                "total_return": r.best_sharpe_ratio,
                "job_type": "research",
            })
    finally:
        db.close()

    jobs.sort(key=lambda j: j["created_at"] or datetime.min, reverse=True)
    return jobs


@router.get("/stream/{job_id}", tags=["Backtest"])
async def stream_backtest(job_id: str):
    """
    Stream live backtest progress via Server-Sent Events (SSE).

    Connect with EventSource('/stream/{job_id}') in the browser.
    Emits events of type: 'equity' (per bar), 'fill' (per trade), 'done', 'error'.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    async def event_generator():
        # On (re)connect, replay accumulated history so the client always sees
        # the full curve from bar 1, not just events from the moment of connection.
        if job.partial_equity_curve or job.partial_fills:
            snapshot = {
                "type": "snapshot",
                "equity_curve": job.partial_equity_curve,
                "fills": job.partial_fills,
            }
            yield f"data: {json.dumps(snapshot)}\n\n"

        while True:
            try:
                event = job.event_queue.get_nowait()
            except queue.Empty:
                if job.status.value == "completed":
                    break
                await asyncio.sleep(0.05)
                continue

            yield f"data: {json.dumps(event)}\n\n"

            if event.get("type") in ("done", "error"):
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


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
