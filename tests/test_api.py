"""
Comprehensive API tests using FastAPI TestClient.
Tests all endpoints, request validation, and job lifecycle.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.jobs import job_manager, JobStatus


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_job_manager():
    """Reset job manager state between tests."""
    job_manager.jobs.clear()
    job_manager.futures.clear()
    yield


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check_returns_healthy(self, client):
        """Health endpoint should return healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_root_endpoint(self, client):
        """Root endpoint should return API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Quant Backtester API"
        assert "version" in data
        assert data["docs"] == "/docs"


class TestStrategiesEndpoint:
    """Tests for the strategies listing endpoint."""

    def test_list_strategies(self, client):
        """Should return available strategies."""
        response = client.get("/strategies")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

        # Check MA Crossover strategy is listed
        ma_strategy = next((s for s in data if s["name"] == "ma_crossover"), None)
        assert ma_strategy is not None
        assert "description" in ma_strategy
        assert "parameters" in ma_strategy
        assert "short_window" in ma_strategy["parameters"]
        assert "long_window" in ma_strategy["parameters"]


class TestBacktestEndpoints:
    """Tests for backtest execution endpoints."""

    def test_run_backtest_valid_request(self, client):
        """Should accept valid backtest request and return job ID."""
        request_data = {
            "symbol": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-06-01",
            "strategy": "ma_crossover",
            "parameters": {"short_window": 10, "long_window": 50},
            "initial_capital": 100000.0,
        }

        response = client.post("/backtest/run", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert "job_id" in data
        assert data["status"] in ["pending", "running"]
        assert "progress" in data

    def test_run_backtest_invalid_strategy(self, client):
        """Should reject request with invalid strategy."""
        request_data = {
            "symbol": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-06-01",
            "strategy": "invalid_strategy",
            "parameters": {},
        }

        response = client.post("/backtest/run", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_run_backtest_missing_required_fields(self, client):
        """Should reject request with missing required fields."""
        request_data = {
            "symbol": "AAPL"
            # Missing start_date, end_date, strategy
        }

        response = client.post("/backtest/run", json=request_data)
        assert response.status_code == 422

    def test_get_job_status_not_found(self, client):
        """Should return 404 for non-existent job."""
        response = client.get("/backtest/non-existent-id")
        assert response.status_code == 404

    def test_get_results_not_found(self, client):
        """Should return 404 for non-existent job results."""
        response = client.get("/results/non-existent-id")
        assert response.status_code == 404


class TestJobsEndpoint:
    """Tests for job listing endpoint."""

    def test_list_jobs_empty(self, client):
        """Should return empty list when no jobs exist."""
        response = client.get("/jobs")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_jobs_after_creation(self, client):
        """Should list jobs after creation."""
        # Create a job
        request_data = {
            "symbol": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-06-01",
            "strategy": "ma_crossover",
            "parameters": {},
        }
        client.post("/backtest/run", json=request_data)

        # List jobs
        response = client.get("/jobs")
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 1
        assert "job_id" in jobs[0]
        assert "status" in jobs[0]


class TestJobManagerUnit:
    """Unit tests for the JobManager class."""

    def test_create_job(self):
        """Should create job with unique ID."""
        job = job_manager.create_job(
            symbol="AAPL",
            start_date="2023-01-01",
            end_date="2023-06-01",
            strategy="ma_crossover",
            parameters={"short_window": 10},
        )

        assert job.job_id is not None
        assert job.symbol == "AAPL"
        assert job.strategy == "ma_crossover"
        assert job.status == JobStatus.PENDING

    def test_get_job(self):
        """Should retrieve job by ID."""
        created_job = job_manager.create_job(
            symbol="MSFT",
            start_date="2023-01-01",
            end_date="2023-06-01",
            strategy="ma_crossover",
            parameters={},
        )

        retrieved_job = job_manager.get_job(created_job.job_id)
        assert retrieved_job is not None
        assert retrieved_job.symbol == "MSFT"

    def test_get_nonexistent_job(self):
        """Should return None for non-existent job."""
        job = job_manager.get_job("nonexistent-id")
        assert job is None

    def test_submit_job_executes(self):
        """Should execute job in background."""
        job = job_manager.create_job(
            symbol="TEST",
            start_date="2023-01-01",
            end_date="2023-06-01",
            strategy="ma_crossover",
            parameters={},
        )

        def mock_executor(j):
            return {"metrics": {"total_return": 10.0}}

        success = job_manager.submit_job(job.job_id, mock_executor)
        assert success is True

        # Wait for completion
        import time

        time.sleep(0.5)

        updated_job = job_manager.get_job(job.job_id)
        assert updated_job.status == JobStatus.COMPLETED
        assert updated_job.result is not None
