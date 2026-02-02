"""
Background job management for async backtest execution.
Provides in-memory job store with status tracking.
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Status of a backtest job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BacktestJob:
    """
    Represents a backtest job with its configuration and results.
    """

    job_id: str
    symbol: str
    start_date: str
    end_date: str
    strategy: str
    parameters: Dict[str, Any]
    initial_capital: float
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for API response."""
        return {
            "job_id": self.job_id,
            "symbol": self.symbol,
            "strategy": self.strategy,
            "parameters": self.parameters,
            "status": self.status.value,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
        }


class JobManager:
    """
    Manages backtest jobs with async execution.
    Uses ThreadPoolExecutor for background processing.
    """

    def __init__(self, max_workers: int = 4):
        self.jobs: Dict[str, BacktestJob] = {}
        self.futures: Dict[str, Future] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        logger.info(f"JobManager initialized with {max_workers} workers")

    def create_job(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        strategy: str,
        parameters: Dict[str, Any],
        initial_capital: float = 100000.0,
    ) -> BacktestJob:
        """
        Create a new backtest job.

        Returns:
            BacktestJob: The created job with a unique ID.
        """
        job_id = str(uuid.uuid4())
        job = BacktestJob(
            job_id=job_id,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            strategy=strategy,
            parameters=parameters,
            initial_capital=initial_capital,
        )
        self.jobs[job_id] = job
        logger.info(f"Created job {job_id}: {symbol} with {strategy}")
        return job

    def get_job(self, job_id: str) -> Optional[BacktestJob]:
        """Get a job by ID."""
        return self.jobs.get(job_id)

    def get_all_jobs(self) -> list[BacktestJob]:
        """Get all jobs sorted by creation time (newest first)."""
        return sorted(self.jobs.values(), key=lambda j: j.created_at, reverse=True)

    def submit_job(self, job_id: str, executor_func) -> bool:
        """
        Submit a job for background execution.

        Args:
            job_id: The job ID to execute.
            executor_func: Callable that takes (job) and returns results dict.

        Returns:
            bool: True if job was submitted successfully.
        """
        job = self.jobs.get(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return False

        if job.status != JobStatus.PENDING:
            logger.warning(f"Job {job_id} already started (status: {job.status})")
            return False

        job.status = JobStatus.RUNNING

        def wrapped_executor():
            try:
                result = executor_func(job)
                job.result = result
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now()
                logger.info(f"Job {job_id} completed successfully")
            except Exception as e:
                job.error = str(e)
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now()
                logger.error(f"Job {job_id} failed: {e}")

        future = self.executor.submit(wrapped_executor)
        self.futures[job_id] = future
        return True

    def shutdown(self, wait: bool = True):
        """Shutdown the executor."""
        self.executor.shutdown(wait=wait)
        logger.info("JobManager shutdown complete")


# Global job manager instance
job_manager = JobManager()
