"""
Research API routes for parameter sweep / optimization.
Exposes POST /research/run, GET /research/stream/{job_id}, GET /research/{job_id}.
"""

import asyncio
import json
import logging
import queue
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.api.schemas import JobStatus
from src.db.database import SessionLocal
from src.db import models

logger = logging.getLogger(__name__)

research_router = APIRouter()
_executor = ThreadPoolExecutor(max_workers=2)
_research_jobs: Dict[str, "ResearchJob"] = {}


# ============================================================
# Request schema
# ============================================================


class ResearchRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    strategy: str = "ma_crossover"
    short_windows: List[int] = [5, 10, 20, 30]
    long_windows: List[int] = [40, 50, 60, 80, 100, 120]
    rsi_periods: List[int] = [10, 14, 21]
    oversold_levels: List[float] = [25.0, 30.0, 35.0]
    overbought_levels: List[float] = [65.0, 70.0, 75.0]
    initial_capital: float = 100000.0
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    risk_per_trade: float = 0.02


# ============================================================
# Job dataclass
# ============================================================


@dataclass
class ResearchJob:
    job_id: str
    symbol: str
    start_date: str
    end_date: str
    short_windows: List[int]
    long_windows: List[int]
    initial_capital: float
    commission_rate: float
    slippage_rate: float
    risk_per_trade: float
    strategy: str = "ma_crossover"
    rsi_periods: List[int] = field(default_factory=list)
    oversold_levels: List[float] = field(default_factory=list)
    overbought_levels: List[float] = field(default_factory=list)
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    results: List[Dict[str, Any]] = field(default_factory=list)
    best_equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    best_fills: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    event_queue: queue.Queue = field(default_factory=queue.Queue)
    progress: int = 0
    total: int = 0


# ============================================================
# DB helpers
# ============================================================


def _save_research_to_db(
    job: ResearchJob,
    all_results: List[Dict[str, Any]],
    best_equity_curve: List[Dict[str, Any]],
    best_fills: List[Dict[str, Any]],
    error: Optional[str] = None,
):
    """Persist completed (or failed) research results to the database."""
    db = SessionLocal()
    try:
        db_run = (
            db.query(models.ResearchRun)
            .filter(models.ResearchRun.job_id == job.job_id)
            .first()
        )
        if not db_run:
            return

        db_run.completed_at = datetime.utcnow()

        if error:
            db_run.status = "failed"
            db_run.error = error
        else:
            db_run.status = "completed"
            db_run.all_results = all_results
            db_run.best_equity_curve = best_equity_curve
            db_run.best_fills = best_fills
            if all_results:
                db_run.best_sharpe_ratio = max(r["sharpe_ratio"] for r in all_results)

        db.commit()
        logger.info(f"Research job {job.job_id} persisted to database")
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to save research results for {job.job_id}: {exc}")
    finally:
        db.close()


# ============================================================
# Execution logic (runs in thread pool)
# ============================================================


def _run_single_backtest(data_path, job, strategy_instance, DataHandler, Portfolio, BacktestEngine, FillEvent,
                         create_equity_curve, calculate_sharpe_ratio, calculate_drawdown, calculate_total_return):
    """Helper: run one backtest and return (total_return, sharpe_ratio, max_drawdown, fills)."""
    data_handler = DataHandler(data_path, job.symbol)
    portfolio = Portfolio(
        initial_capital=job.initial_capital,
        commission_rate=job.commission_rate,
        risk_per_trade=job.risk_per_trade,
    )
    engine = BacktestEngine(
        data_handler=data_handler,
        strategy=strategy_instance,
        portfolio=portfolio,
        slippage_rate=job.slippage_rate,
    )
    engine.run()

    equity_curve = create_equity_curve(portfolio.history)
    total_return = 0.0
    sharpe_ratio = 0.0
    max_drawdown = 0.0

    if not equity_curve.empty:
        total_return = calculate_total_return(equity_curve) * 100
        raw_sharpe = calculate_sharpe_ratio(equity_curve)
        sharpe_ratio = float(raw_sharpe) if raw_sharpe is not None else 0.0
        dd = calculate_drawdown(equity_curve)
        max_drawdown = float(dd.min()) * 100 if len(dd) > 0 else 0.0

    fills = [e for e in engine.processed_events if isinstance(e, FillEvent)]
    return total_return, sharpe_ratio, max_drawdown, fills, portfolio, engine


def _build_equity_and_fills(portfolio, engine, FillEvent):
    """Serialize equity curve and fills from a completed engine run."""
    best_equity_curve = [
        {
            "time": (
                h["datetime"].isoformat()
                if hasattr(h["datetime"], "isoformat")
                else str(h["datetime"])
            ),
            "equity": h["equity"],
            "cash": h["cash"],
            "price": h.get("price"),
        }
        for h in portfolio.history
    ]
    best_fills = [
        {
            "time": (
                e.time.isoformat()
                if hasattr(e.time, "isoformat")
                else str(e.time)
            ),
            "direction": e.direction,
        }
        for e in engine.processed_events
        if isinstance(e, FillEvent)
    ]
    return best_equity_curve, best_fills


def _execute_research(job: ResearchJob):
    from src.data_fetcher import DataFetcher
    from src.data_handler import DataHandler
    from src.strategy import MovingAverageCrossStrategy, RSIStrategy
    from src.portfolio import Portfolio
    from src.engine import BacktestEngine
    from src.performance import (
        create_equity_curve,
        calculate_sharpe_ratio,
        calculate_drawdown,
        calculate_total_return,
    )
    from src.events import FillEvent

    helpers = (DataHandler, Portfolio, BacktestEngine, FillEvent,
               create_equity_curve, calculate_sharpe_ratio, calculate_drawdown, calculate_total_return)

    try:
        # 1. Fetch price data once — reused for every combination
        fetcher = DataFetcher()
        data_path = fetcher.get_data(job.symbol, job.start_date, job.end_date)

        all_results: List[Dict[str, Any]] = []

        if job.strategy == "rsi":
            # ---- RSI parameter sweep ----
            combinations = [
                (p, ov, ob)
                for p in job.rsi_periods
                for ov in job.oversold_levels
                for ob in job.overbought_levels
            ]
            job.total = len(combinations)
            job.event_queue.put({"type": "start", "total": job.total})

            for i, (p, ov, ob) in enumerate(combinations):
                strategy_instance = RSIStrategy(rsi_period=p, oversold=ov, overbought=ob)
                total_return, sharpe_ratio, max_drawdown, fills, _, _ = _run_single_backtest(
                    data_path, job, strategy_instance, *helpers
                )

                result: Dict[str, Any] = {
                    "rsi_period": p,
                    "oversold": ov,
                    "overbought": ob,
                    "total_return": round(total_return, 2),
                    "sharpe_ratio": round(sharpe_ratio, 3),
                    "max_drawdown": round(max_drawdown, 2),
                    "trade_count": len(fills),
                }
                all_results.append(result)
                job.results.append(result)
                job.progress = i + 1

                job.event_queue.put(
                    {
                        "type": "progress",
                        "done": i + 1,
                        "total": job.total,
                        "result": result,
                    }
                )

            # Re-run best RSI params to capture full equity curve
            best_equity_curve: List[Dict[str, Any]] = []
            best_fills: List[Dict[str, Any]] = []

            if all_results:
                best = max(all_results, key=lambda r: r["sharpe_ratio"])
                strategy_instance = RSIStrategy(
                    rsi_period=best["rsi_period"],
                    oversold=best["oversold"],
                    overbought=best["overbought"],
                )
                _, _, _, _, portfolio, engine = _run_single_backtest(
                    data_path, job, strategy_instance, *helpers
                )
                best_equity_curve, best_fills = _build_equity_and_fills(portfolio, engine, FillEvent)

        else:
            # ---- MA Crossover parameter sweep (default) ----
            combinations = [
                (sw, lw)
                for sw in job.short_windows
                for lw in job.long_windows
                if sw < lw
            ]
            job.total = len(combinations)
            job.event_queue.put({"type": "start", "total": job.total})

            for i, (sw, lw) in enumerate(combinations):
                strategy_instance = MovingAverageCrossStrategy(short_window=sw, long_window=lw)
                total_return, sharpe_ratio, max_drawdown, fills, _, _ = _run_single_backtest(
                    data_path, job, strategy_instance, *helpers
                )

                result: Dict[str, Any] = {
                    "short_window": sw,
                    "long_window": lw,
                    "total_return": round(total_return, 2),
                    "sharpe_ratio": round(sharpe_ratio, 3),
                    "max_drawdown": round(max_drawdown, 2),
                    "trade_count": len(fills),
                }
                all_results.append(result)
                job.results.append(result)
                job.progress = i + 1

                job.event_queue.put(
                    {
                        "type": "progress",
                        "done": i + 1,
                        "total": job.total,
                        "result": result,
                    }
                )

            # Re-run best MA params to capture full equity curve
            best_equity_curve = []
            best_fills = []

            if all_results:
                best = max(all_results, key=lambda r: r["sharpe_ratio"])
                strategy_instance = MovingAverageCrossStrategy(
                    short_window=best["short_window"],
                    long_window=best["long_window"],
                )
                _, _, _, _, portfolio, engine = _run_single_backtest(
                    data_path, job, strategy_instance, *helpers
                )
                best_equity_curve, best_fills = _build_equity_and_fills(portfolio, engine, FillEvent)

        job.best_equity_curve = best_equity_curve
        job.best_fills = best_fills
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now()

        _save_research_to_db(job, all_results, best_equity_curve, best_fills)

        job.event_queue.put(
            {
                "type": "done",
                "results": all_results,
                "best_equity_curve": best_equity_curve,
                "best_fills": best_fills,
            }
        )

    except Exception as e:
        job.error = str(e)
        job.status = JobStatus.FAILED
        job.completed_at = datetime.now()
        _save_research_to_db(job, [], [], [], error=str(e))
        job.event_queue.put({"type": "error", "message": str(e)})
        logger.error(f"Research job {job.job_id} failed: {e}", exc_info=True)


# ============================================================
# API endpoints
# ============================================================


@research_router.post("/research/run", tags=["Research"])
async def run_research(
    request: ResearchRequest,
    x_session_id: Optional[str] = Header(default=None),
):
    """
    Start a parameter sweep over strategy parameter combinations.
    Supports MA crossover (short_window × long_window) and RSI mean-reversion
    (rsi_period × oversold × overbought) strategies.
    Returns a job_id — connect to /research/stream/{job_id} for live progress.
    """
    try:
        s = date.fromisoformat(request.start_date)
        e = date.fromisoformat(request.end_date)
        if s >= e:
            raise ValueError("start_date must be before end_date")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if request.strategy == "rsi":
        if not request.rsi_periods or not request.oversold_levels or not request.overbought_levels:
            raise HTTPException(
                status_code=400,
                detail="rsi_periods, oversold_levels, and overbought_levels must not be empty",
            )
    else:
        if not request.short_windows or not request.long_windows:
            raise HTTPException(status_code=400, detail="short_windows and long_windows must not be empty")

    job_id = str(uuid.uuid4())
    job = ResearchJob(
        job_id=job_id,
        symbol=request.symbol.upper().strip(),
        start_date=request.start_date,
        end_date=request.end_date,
        short_windows=sorted(set(request.short_windows)),
        long_windows=sorted(set(request.long_windows)),
        strategy=request.strategy,
        rsi_periods=sorted(set(request.rsi_periods)),
        oversold_levels=sorted(set(request.oversold_levels)),
        overbought_levels=sorted(set(request.overbought_levels)),
        initial_capital=request.initial_capital,
        commission_rate=request.commission_rate,
        slippage_rate=request.slippage_rate,
        risk_per_trade=request.risk_per_trade,
        status=JobStatus.RUNNING,
    )
    _research_jobs[job_id] = job

    # Persist initial record to DB immediately
    db = SessionLocal()
    try:
        db_run = models.ResearchRun(
            job_id=job.job_id,
            symbol=job.symbol,
            status="running",
            created_at=datetime.utcnow(),
            short_windows=job.short_windows,
            long_windows=job.long_windows,
            strategy=job.strategy,
            rsi_periods=job.rsi_periods,
            oversold_levels=job.oversold_levels,
            overbought_levels=job.overbought_levels,
            initial_capital=job.initial_capital,
            commission_rate=job.commission_rate,
            slippage_rate=job.slippage_rate,
            risk_per_trade=job.risk_per_trade,
            session_id=x_session_id,
        )
        db.add(db_run)
        db.commit()
    except Exception as exc:
        logger.error(f"Failed to create DB record for research job {job_id}: {exc}")
    finally:
        db.close()

    _executor.submit(_execute_research, job)

    return {"job_id": job_id, "status": "running"}


@research_router.get("/research/stream/{job_id}", tags=["Research"])
async def stream_research(job_id: str):
    """
    Stream research progress via SSE.
    Emits: start, progress (per combination), done, error.
    Reconnect-safe: replays accumulated results as a snapshot on reconnect.
    """
    job = _research_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Research job {job_id} not found")

    async def event_generator():
        # Replay already-computed results for reconnects
        if job.results:
            yield f"data: {json.dumps({'type': 'snapshot', 'done': job.progress, 'total': job.total, 'results': job.results})}\n\n"

        while True:
            try:
                event = job.event_queue.get_nowait()
            except queue.Empty:
                if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    break
                await asyncio.sleep(0.1)
                continue

            yield f"data: {json.dumps(event)}\n\n"

            if event.get("type") in ("done", "error"):
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@research_router.get("/research/{job_id}", tags=["Research"])
async def get_research(job_id: str):
    """
    Get the current state of a research job.
    Falls back to the database when the job is no longer in memory (e.g. after restart).
    """
    # In-memory first (live / recently completed jobs)
    job = _research_jobs.get(job_id)
    if job:
        return {
            "job_id": job.job_id,
            "status": job.status,
            "symbol": job.symbol,
            "strategy": job.strategy,
            "short_windows": job.short_windows,
            "long_windows": job.long_windows,
            "progress": job.progress,
            "total": job.total,
            "results": job.results,
            "best_equity_curve": job.best_equity_curve,
            "best_fills": job.best_fills,
            "error": job.error,
            "created_at": job.created_at,
            "completed_at": job.completed_at,
        }

    # Fall back to DB for jobs from previous server sessions
    db = SessionLocal()
    try:
        db_run = (
            db.query(models.ResearchRun)
            .filter(models.ResearchRun.job_id == job_id)
            .first()
        )
        if not db_run:
            raise HTTPException(status_code=404, detail=f"Research job {job_id} not found")

        combo_count = len(db_run.all_results or [])
        return {
            "job_id": db_run.job_id,
            "status": db_run.status,
            "symbol": db_run.symbol,
            "strategy": db_run.strategy or "ma_crossover",
            "short_windows": db_run.short_windows,
            "long_windows": db_run.long_windows,
            "progress": combo_count,
            "total": combo_count,
            "results": db_run.all_results or [],
            "best_equity_curve": db_run.best_equity_curve or [],
            "best_fills": db_run.best_fills or [],
            "error": db_run.error,
            "created_at": db_run.created_at,
            "completed_at": db_run.completed_at,
        }
    finally:
        db.close()
